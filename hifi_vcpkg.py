import hifi_utils
import hifi_android
import hashlib
import os
import platform
import re
import shutil
import tempfile
import json
import xml.etree.ElementTree as ET
import functools
from os import path

print = functools.partial(print, flush=True)

# Encapsulates the vcpkg system
class VcpkgRepo:
    CMAKE_TEMPLATE = """
# this file auto-generated by hifi_vcpkg.py
get_filename_component(CMAKE_TOOLCHAIN_FILE "{}" ABSOLUTE CACHE)
get_filename_component(CMAKE_TOOLCHAIN_FILE_UNCACHED "{}" ABSOLUTE)
set(VCPKG_INSTALL_ROOT "{}")
set(VCPKG_TOOLS_DIR "{}")
set(VCPKG_TARGET_TRIPLET "{}")
"""

    CMAKE_TEMPLATE_NON_ANDROID = """
# If the cached cmake toolchain path is different from the computed one, exit
if(NOT (CMAKE_TOOLCHAIN_FILE_UNCACHED STREQUAL CMAKE_TOOLCHAIN_FILE))
    message(FATAL_ERROR "CMAKE_TOOLCHAIN_FILE has changed, please wipe the build directory and rerun cmake")
endif()
"""

    def __init__(self, args):
        self.args = args
        # our custom ports, relative to the script location
        self.sourcePortsPath = args.ports_path
        self.vcpkgBuildType = args.vcpkg_build_type
        if (self.vcpkgBuildType):
            self.id = hifi_utils.hashFolder(self.sourcePortsPath)[:8] + "-" + self.vcpkgBuildType
        else:
            self.id = hifi_utils.hashFolder(self.sourcePortsPath)[:8]
        self.configFilePath = os.path.join(args.build_root, 'vcpkg.cmake')

        # The noClean flag indicates we're doing weird dependency maintenance stuff
        # i.e. we've got an explicit checkout of vcpkg and we don't want the script to
        # do stuff it might otherwise do.  It typically indicates that we're using our
        # own git checkout of vcpkg and manually managing it
        self.noClean = False

        # OS dependent information
        system = platform.system()
        machine = platform.machine()

        if 'HIFI_VCPKG_PATH' in os.environ:
            self.path = os.environ['HIFI_VCPKG_PATH']
            self.noClean = True
        elif self.args.vcpkg_root is not None:
            self.path = args.vcpkg_root
            self.noClean = True
        else:
            defaultBasePath = os.path.expanduser('~/vircadia-files/vcpkg')
            if 'CI_WORKSPACE' in os.environ:
                self.basePath = os.path.join(os.getenv('CI_WORKSPACE'), 'vircadia-files/vcpkg')
            else:
                self.basePath = os.getenv('HIFI_VCPKG_BASE', defaultBasePath)
            if self.args.android:
                self.basePath = os.path.join(self.basePath, 'android')
            if (not os.path.isdir(self.basePath)):
                os.makedirs(self.basePath)
            self.path = os.path.join(self.basePath, self.id)

        print("Using vcpkg path {}".format(self.path))
        lockDir, lockName = os.path.split(self.path)
        lockName += '.lock'
        if not os.path.isdir(lockDir):
            os.makedirs(lockDir)

        self.lockFile = os.path.join(lockDir, lockName)
        self.tagFile = os.path.join(self.path, '.id')
        self.prebuildTagFile = os.path.join(self.path, '.prebuild')
        # A format version attached to the tag file... increment when you want to force the build systems to rebuild
        # without the contents of the ports changing
        self.version = 1
        self.tagContents = "{}_{}".format(self.id, self.version)
        self.bootstrapEnv = os.environ.copy()
        self.buildEnv = os.environ.copy()
        self.prebuiltArchive = None
        usePrebuilt = False
        # usePrebuild Disabled, to re-enabled using the prebuilt archives for GitHub action builds uncomment the following line:
        # usePrebuilt = ('CI_BUILD' in os.environ) and os.environ["CI_BUILD"] == "Github" and (not self.noClean)

        if 'Windows' == system:
            self.exe = os.path.join(self.path, 'vcpkg.exe')
            self.bootstrapCmds = [ os.path.join(self.path, 'bootstrap-vcpkg.bat'), '-disableMetrics' ]
            self.vcpkgUrl = self.readVar('EXTERNAL_VCPKG_WIN_CLIENT_URLS').split(';')
            self.hostTriplet = 'x64-windows'
            if usePrebuilt:
                self.prebuiltArchive = self.readVar('EXTERNAL_VCPKG_WIN_URLS').split(';')
        elif 'Darwin' == system:
            self.exe = os.path.join(self.path, 'vcpkg')
            self.bootstrapCmds = [ os.path.join(self.path, 'bootstrap-vcpkg.sh'), '--allowAppleClang', '-disableMetrics' ]
            self.vcpkgUrl = self.readVar('EXTERNAL_VCPKG_MAC_CLIENT_URLS').split(';')
            self.hostTriplet = 'x64-osx'
            # Potential fix for a vcpkg build issue on OSX (see https://github.com/microsoft/vcpkg/issues/9029)
            self.bootstrapEnv['CXXFLAGS'] = '-D_CTERMID_H_'
            if usePrebuilt:
                self.prebuiltArchive = self.readVar('EXTERNAL_VCPKG_MAC_URLS').split(';')
        elif 'Linux' == system and 'aarch64' == machine:
            self.exe = os.path.join(self.path, 'vcpkg')
            self.bootstrapCmds = [ os.path.join(self.path, 'bootstrap-vcpkg.sh'), '-disableMetrics' ]
            self.vcpkgUrl = self.readVar('EXTERNAL_VCPKG_LINUX_AARCH64_URLS').split(';')
            self.hostTriplet = 'arm64-linux'
        else:
            self.exe = os.path.join(self.path, 'vcpkg')
            self.bootstrapCmds = [ os.path.join(self.path, 'bootstrap-vcpkg.sh'), '-disableMetrics' ]
            self.vcpkgUrl = self.readVar('EXTERNAL_VCPKG_LINUX_CLIENT_URLS').split(';')
            self.hostTriplet = 'x64-linux'

        if self.args.android:
            self.triplet = 'arm64-android'
            self.androidPackagePath = os.getenv('HIFI_ANDROID_PRECOMPILED', os.path.join(self.path, 'android'))
        else:
            self.triplet = self.hostTriplet

    def readVar(self, var):
        with open(os.path.join(self.args.build_root, '_env', var + ".txt")) as fp:
            return fp.read()

    def writeVar(self, var, value):
        with open(os.path.join(self.args.build_root, '_env', var + ".txt"), 'w') as fp:
            fp.write(value)

    def upToDate(self):
        # Prevent doing a clean if we've explcitly set a directory for vcpkg
        if self.noClean:
            return True

        if self.args.force_build:
            print("Force build, out of date")
            return False
        if not os.path.isfile(self.exe):
            print("Exe file {} not found, out of date".format(self.exe))
            return False
        if not os.path.isfile(self.tagFile):
            print("Tag file {} not found, out of date".format(self.tagFile))
            return False
        with open(self.tagFile, 'r') as f:
            storedTag = f.read()
        if storedTag != self.tagContents:
            print("Tag file {} contents don't match computed tag {}, out of date".format(self.tagFile, self.tagContents))
            return False
        return True

    def copyEnv(self):
        print("Passing on variables to vcpkg")
        srcEnv = os.path.join(self.args.build_root, "_env")
        destEnv = os.path.join(self.path, "_env")

        if path.exists(destEnv):
            shutil.rmtree(destEnv)

        shutil.copytree(srcEnv, destEnv)


    def clean(self):
        print("Cleaning vcpkg installation at {}".format(self.path))
        if os.path.isdir(self.path):
            print("Removing {}".format(self.path))
            shutil.rmtree(self.path, ignore_errors=True)

    # Make sure the VCPKG prerequisites are all there.
    def bootstrap(self):
        if self.upToDate():
            self.copyEnv()
            return

        if self.prebuiltArchive is not None:
            return

        self.clean()
        downloadVcpkg = False
        if self.args.force_bootstrap:
            print("Forcing bootstrap")
            downloadVcpkg = True

        if not downloadVcpkg and not os.path.isfile(self.exe):
            print("Missing executable, boot-strapping")
            downloadVcpkg = True

        # Make sure we have a vcpkg executable
        testFile = os.path.join(self.path, '.vcpkg-root')
        if not downloadVcpkg and not os.path.isfile(testFile):
            print("Missing {}, bootstrapping".format(testFile))
            downloadVcpkg = True

        if downloadVcpkg:
            if "HIFI_VCPKG_BOOTSTRAP" in os.environ:
                print("Cloning vcpkg from github to {}".format(self.path))
                hifi_utils.executeSubprocess(['git', 'clone', 'https://github.com/microsoft/vcpkg', self.path])
                print("Bootstrapping vcpkg")
                hifi_utils.executeSubprocess(self.bootstrapCmds, folder=self.path, env=self.bootstrapEnv)
            else:
                print("Fetching vcpkg from {} to {}".format(self.vcpkgUrl, self.path))
                hifi_utils.downloadAndExtract(self.vcpkgUrl, self.path)

        print("Replacing port files")
        portsPath = os.path.join(self.path, 'ports')
        if (os.path.islink(portsPath)):
            os.unlink(portsPath)
        if (os.path.isdir(portsPath)):
            shutil.rmtree(portsPath, ignore_errors=True)
        shutil.copytree(self.sourcePortsPath, portsPath)
        self.copyEnv()

    def run(self, commands):
        actualCommands = [self.exe, '--vcpkg-root', self.path]
        actualCommands.extend(commands)
        print("Running command")
        print(actualCommands)
        hifi_utils.executeSubprocess(actualCommands, folder=self.path, env=self.buildEnv)

    def copyTripletForBuildType(self, triplet):
        print('Copying triplet ' + triplet + ' to have build type ' + self.vcpkgBuildType)
        tripletPath = os.path.join(self.path, 'triplets', triplet + '.cmake')
        tripletForBuildTypePath = os.path.join(self.path, 'triplets', self.getTripletWithBuildType(triplet) + '.cmake')
        shutil.copy(tripletPath, tripletForBuildTypePath)
        with open(tripletForBuildTypePath, "a") as tripletForBuildTypeFile:
            tripletForBuildTypeFile.write("set(VCPKG_BUILD_TYPE " + self.vcpkgBuildType + ")\n")

    def getTripletWithBuildType(self, triplet):
        if (not self.vcpkgBuildType):
            return triplet
        return triplet + '-' + self.vcpkgBuildType

    def setupDependencies(self, qt=None):
        if self.prebuiltArchive:
            if not os.path.isfile(self.prebuildTagFile):
                print('Extracting ' + self.prebuiltArchive + ' to ' + self.path)
                hifi_utils.downloadAndExtract(self.prebuiltArchive, self.path)
                self.writePrebuildTag()
            return

        if qt is not None:
            self.buildEnv['QT_CMAKE_PREFIX_PATH'] = qt

        # Special case for android, grab a bunch of binaries
        # FIXME remove special casing for android builds eventually
        if self.args.android:
            print("Installing Android binaries")
            self.setupAndroidDependencies()

        print("Installing host tools")
        if (self.vcpkgBuildType):
            self.copyTripletForBuildType(self.hostTriplet)
        self.run(['install', '--triplet', self.getTripletWithBuildType(self.hostTriplet), 'hifi-host-tools'])

        # If not android, install the hifi-client-deps libraries
        if not self.args.android:
            print("Installing build dependencies")
            if (self.vcpkgBuildType):
                self.copyTripletForBuildType(self.triplet)
            self.run(['install', '--triplet', self.getTripletWithBuildType(self.triplet), 'hifi-client-deps'])

    def cleanBuilds(self):
        if self.noClean:
            return
        # Remove temporary build artifacts
        builddir = os.path.join(self.path, 'buildtrees')
        if os.path.isdir(builddir):
            print("Wiping build trees")
            shutil.rmtree(builddir, ignore_errors=True)

    # Removes large files used to build the vcpkg, for CI purposes.
    def cleanupDevelopmentFiles(self):
        shutil.rmtree(os.path.join(self.path, "downloads"), ignore_errors=True)
        shutil.rmtree(os.path.join(self.path, "packages"), ignore_errors=True)


    def setupAndroidDependencies(self):
        # vcpkg prebuilt
        if not os.path.isdir(os.path.join(self.path, 'installed', 'arm64-android')):
            dest = os.path.join(self.path, 'installed')
            url = self.readVar('EXTERNAL_VCPKG_ANDROID_URLS').split(';')
            # FIXME I don't know why the hash check frequently fails here.  If you examine the file later it has the right hash
            #hash = self.readVar(('EXTERNAL_VCPKG_ANDROID_SHA512')
            #hifi_utils.downloadAndExtract(url, dest, hash)
            hifi_utils.downloadAndExtract(url, dest)

        print("Installing additional android archives")
        androidPackages = hifi_android.getPlatformPackages()
        for packageName in androidPackages:
            package = androidPackages[packageName]
            dest = os.path.join(self.androidPackagePath, packageName)
            if os.path.isdir(dest):
                continue
            url = hifi_android.getPackageUrl(package)
            zipFile = package['file'].endswith('.zip')
            print("Android archive {}".format(package['file']))
            hifi_utils.downloadAndExtract(url, dest, isZip=zipFile, hash=package['checksum'], hasher=hashlib.md5())

    def writeTag(self):
        if self.noClean:
            return
        print("Writing tag {} to {}".format(self.tagContents, self.tagFile))
        if not os.path.isdir(self.path):
            os.makedirs(self.path)
        with open(self.tagFile, 'w') as f:
            f.write(self.tagContents)

    def writePrebuildTag(self):
        print("Writing tag {} to {}".format(self.tagContents, self.tagFile))
        with open(self.prebuildTagFile, 'w') as f:
            f.write(self.tagContents)

    def fixupCmakeScript(self):
        cmakeScript = os.path.join(self.path, 'scripts/buildsystems/vcpkg.cmake')
        newCmakeScript = cmakeScript + '.new'
        isFileChanged = False
        removalPrefix = "set(VCPKG_TARGET_TRIPLET "
        # Open original file in read only mode and dummy file in write mode
        with open(cmakeScript, 'r') as read_obj, open(newCmakeScript, 'w') as write_obj:
            # Line by line copy data from original file to dummy file
            for line in read_obj:
                if not line.startswith(removalPrefix):
                    write_obj.write(line)
                else:
                    isFileChanged = True

        if isFileChanged:
            shutil.move(newCmakeScript, cmakeScript)
        else:
            os.remove(newCmakeScript)


    def writeConfig(self):
        print("Writing cmake config to {}".format(self.configFilePath))
        # Write out the configuration for use by CMake
        cmakeScript = os.path.join(self.path, 'scripts/buildsystems/vcpkg.cmake')
        installPath = os.path.join(self.path, 'installed', self.getTripletWithBuildType(self.triplet))
        toolsPath = os.path.join(self.path, 'installed', self.getTripletWithBuildType(self.hostTriplet), 'tools')

        cmakeTemplate = VcpkgRepo.CMAKE_TEMPLATE
        if self.args.android:
            precompiled = os.path.realpath(self.androidPackagePath)
            cmakeTemplate += 'set(HIFI_ANDROID_PRECOMPILED "{}")\n'.format(precompiled)
        else:
            cmakeTemplate += VcpkgRepo.CMAKE_TEMPLATE_NON_ANDROID
        cmakeConfig = cmakeTemplate.format(cmakeScript, cmakeScript, installPath, toolsPath, self.getTripletWithBuildType(self.hostTriplet)).replace('\\', '/')
        with open(self.configFilePath, 'w') as f:
            f.write(cmakeConfig)

    def cleanOldBuilds(self):
        # FIXME because we have the base directory, and because a build will
        # update the tag file on every run, we can scan the base dir for sub directories containing
        # a tag file that is older than N days, and if found, delete the directory, recovering space
        print("Not implemented")
