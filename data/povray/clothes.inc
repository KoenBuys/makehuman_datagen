#ifndef (%%name%%_Material)
#declare %%name%%_Texture =
    texture {
        pigment {%%texture%%}
        normal {%%bumpmap%%}
        finish {
            specular 0
            roughness 1
            phong 0 phong_size 0 
            ambient rgb %%ambience%%
            diffuse 1
            conserve_energy
        }
    }

#declare %%name%%_Material = material {
    texture {
        uv_mapping
        pigment_pattern {image_map {png "%%name%%_alpha.png" interpolate 2}}
        texture_map {
            [0 pigment {color transmit 1.0}]
            [1 %%name%%_Texture]
        }
    }
}

#end

