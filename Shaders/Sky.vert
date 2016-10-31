#version 130

uniform mat4 p3d_ModelViewProjectionMatrix;
uniform mat4 trans_model_to_world;
in vec4 p3d_Vertex;
out vec3 tex_vector;

void main() {
    gl_Position = p3d_ModelViewProjectionMatrix * p3d_Vertex;
    tex_vector = (trans_model_to_world * p3d_Vertex).xyz; 
}