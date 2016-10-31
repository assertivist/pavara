#version 130

uniform vec4 skyColor;
uniform vec4 horizonColor;
uniform vec4 groundColor;
uniform float gradientHeight;
in vec3 tex_vector;
out vec4 frag_color;

void main() {
    float phi = normalize(tex_vector).y;
    
    if (phi <= 0.0) {
        frag_color = groundColor;
    }

    if(phi > gradientHeight) {
            frag_color = skyColor;
    }

    if (0.0 < phi && phi < gradientHeight ) {
        float gradientValue = phi / gradientHeight;
        frag_color = skyColor * gradientValue + horizonColor * (1.0 - gradientValue);
    }
}
