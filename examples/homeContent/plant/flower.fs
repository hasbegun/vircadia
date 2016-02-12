#line 2
////////////////////////////////////////////////////////////////////////////////////
//
// REPLACE BELOW
//
// Replace the contents of this section with a shadertoy that includes a mainImage
// function 
//  
////////////////////////////////////////////////////////////////////////////////////

#define TWO_PI 6.28318530718

vec3 hsb2rgb( in vec3 c ){
    vec3 rgb = clamp(abs(mod(c.x*6.0+vec3(0.0,4.0,2.0),
                             6.0)-3.0)-1.0, 
                     0.0, 
                     1.0 );
    rgb = rgb*rgb*(3.0-2.0*rgb);
    return c.z * mix( vec3(1.0), rgb, c.y);
}


void mainImage( out vec4 fragColor, in vec2 fragCoord ) {
    vec2 st = fragCoord.xy/iWorldScale.xz;
    vec3 color = vec3(0.0, 0.0, 0.0);

    vec2 toCenter = vec2(0.5) - st;
    float angle = atan(toCenter.y, toCenter.x);
    float radius = length(toCenter) * 2.0;

    // Second check is so we discard the top half of the sphere
    if (radius > 0.8 || _position.y > 0) {
        discard;
    }
    float brightness = (angle * 10./ (TWO_PI)) + 0.5;
    float hueOffset = sin(iGlobalTime * .07);
    color = hsb2rgb(vec3( abs(angle/20) + hueOffset, 0.8, pow(fract(brightness), 0.3)));
  
    // Map the angle (-PI to PI) to the Hue (from 0 to 1)
    // and the Saturation to the radius
    // angle = pow(angle, 0.2);


    fragColor = vec4(color, 1.0);
}

////////////////////////////////////////////////////////////////////////////////////
//
// REPLACE ABOVE
//  
////////////////////////////////////////////////////////////////////////////////////


vec4 getProceduralColor() {
    vec4 result;
    vec2 position = _position.xz;
    position += 0.5;
    
    mainImage(result, position * iWorldScale.xz);
 
    return result;
}