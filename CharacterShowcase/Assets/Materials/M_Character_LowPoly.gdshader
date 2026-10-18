shader_type spatial;
render_mode blend_mix, depth_draw_opaque, cull_back, diffuse_burley, specular_schlick_ggx;

uniform vec4 color_skin : source_color = vec4(0.882, 0.718, 0.580, 1.0);
uniform vec4 color_shirt : source_color = vec4(0.180, 0.330, 0.820, 1.0);
uniform vec4 color_pants : source_color = vec4(0.120, 0.120, 0.280, 1.0);
uniform vec4 color_shoes : source_color = vec4(0.082, 0.060, 0.040, 1.0);

varying vec3 v_vertex;

void vertex() {
	v_vertex = VERTEX;
}

void fragment() {
	vec3 col = color_shirt.rgb;
	if (v_vertex.y < 0.075) {
		col = color_shoes.rgb;
	} else if (v_vertex.y < 0.95) {
		col = color_pants.rgb;
	} else if (abs(v_vertex.x) > 0.32 && v_vertex.y > 1.15) {
		col = color_skin.rgb;
	} else if (v_vertex.y > 1.365 && abs(v_vertex.x) < 0.12) {
		col = color_skin.rgb;
	} else {
		col = color_shirt.rgb;
	}
	ALBEDO = col;
	ROUGHNESS = 0.85;
	METALLIC = 0.0;
}
