import Hifi 1.0
import QtQuick 2.3
import QtQuick.Controls 1.3
import QtQuick.Controls.Styles 1.3
import QtGraphicalEffects 1.0
import "controls"
import "styles"

DialogContainer {
    id: root
    HifiConstants { id: hifi }

    objectName: "UpdateDialog"

    implicitWidth: updateDialog.implicitWidth
    implicitHeight: updateDialog.implicitHeight

    x: parent ? parent.width / 2 - width / 2 : 0
    y: parent ? parent.height / 2 - height / 2 : 0
    property int maximumX: parent ? parent.width - width : 0
    property int maximumY: parent ? parent.height - height : 0

    UpdateDialog {
        id: updateDialog
        
        implicitWidth: backgroundRectangle.width
        implicitHeight: backgroundRectangle.height
        
        readonly property int contentWidth: 500
        readonly property int logoSize: 60
        readonly property int borderWidth: 30
        readonly property int closeMargin: 16
        readonly property int inputSpacing: 16
        readonly property int buttonWidth: 150
        readonly property int buttonHeight: 50
        readonly property int buttonRadius: 15
        readonly property int noticeHeight: 15 * inputSpacing

        signal triggerBuildDownload
        signal closeUpdateDialog
        
        Rectangle {
            id: backgroundRectangle
            color: "#ffffff"

            width: updateDialog.contentWidth + updateDialog.borderWidth * 2
            height: mainContent.height + updateDialog.borderWidth * 2

            MouseArea {
                width: parent.width
                height: parent.height
                anchors {
                    horizontalCenter: parent.horizontalCenter
                    verticalCenter: parent.verticalCenter
                }
                drag {
                    target: root
                    minimumX: 0
                    minimumY: 0
                    maximumX: root.parent ? root.maximumX : 0
                    maximumY: root.parent ? root.maximumY : 0
                }
            }
        }

        Image {
            id: logo
            source: "../images/hifi-logo.svg"
            width: updateDialog.logoSize
            height: updateDialog.logoSize
            anchors {
                top: mainContent.top
                right: mainContent.right
            }
        }

        Column {
            id: mainContent
            width: updateDialog.contentWidth
            spacing: updateDialog.inputSpacing
            anchors {
                horizontalCenter: parent.horizontalCenter
                verticalCenter: parent.verticalCenter
            }
            
            Rectangle {
                id: header
                width: parent.width - updateDialog.logoSize - updateDialog.inputSpacing
                height: updateAvailable.height + versionDetails.height

                Text {
                    id: updateAvailable
                    text: "Update Available"
                }

                Text {
                    id: versionDetails
                    text: updateDialog.updateAvailableDetails
                    font.pixelSize: 14
                    color: hifi.colors.text
                    anchors {
                        top: updateAvailable.bottom
                    }
                }
            }

            Rectangle {
                width: parent.width
                height: updateDialog.noticeHeight

                border {
                    width: 1
                    color: "#808080"
                }

                ScrollView {
                    id: scrollArea
                    width: parent.width - updateDialog.closeMargin
                    height: parent.height
                    horizontalScrollBarPolicy: Qt.ScrollBarAlwaysOff
                    verticalScrollBarPolicy: Qt.ScrollBarAsNeeded
                    anchors.right: parent.right

                    Text {
                        id: releaseNotes
                        wrapMode: Text.Wrap
                        width: parent.width - updateDialog.closeMargin
                        text: updateDialog.releaseNotes
                        font.pixelSize: 14
                        color: "#000000"
                    }
                }
            }

            Row {
                anchors.right: parent.right
                spacing: updateDialog.inputSpacing

                Rectangle {
                    id: cancelButton
                    width: updateDialog.buttonWidth
                    height: updateDialog.buttonHeight
                    radius: updateDialog.buttonRadius
                    color: "red"

                    Text {
                        text: "Cancel"
                        anchors {
                            verticalCenter: parent.verticalCenter
                            horizontalCenter: parent.horizontalCenter
                        }
                    }

                    MouseArea {
                        id: cancelButtonAction
                        anchors.fill: parent
                        onClicked: updateDialog.closeDialog()
                        cursorShape: "PointingHandCursor"
                    }
                }

                Rectangle {
                    id: downloadButton
                    width: updateDialog.buttonWidth
                    height: updateDialog.buttonHeight
                    radius: updateDialog.buttonRadius
                    color: "green"

                    Text {
                        text: "Upgrade"
                        anchors {
                            verticalCenter: parent.verticalCenter
                            horizontalCenter: parent.horizontalCenter
                        }
                    }

                    MouseArea {
                        id: downloadButtonAction
                        anchors.fill: parent
                        onClicked: updateDialog.triggerUpgrade()
                        cursorShape: "PointingHandCursor"
                    }
                }
            }
        }
    }
}
