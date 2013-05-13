
// Assign default values.
// This texture uses the standard pigment map as a uv-mapped pigment and adds a
// little disruption to the surface normals.  
#ifndef (%%name%%_Material)

#declare %%name%%_Texture =
    texture {
        pigment {rgb 1}
        finish {
            specular 0
            roughness 1
            phong 0 phong_size 0
            ambient %%ambience%%
            diffuse 1
        }
    }
    texture {
        pigment {rgbf 1}
        normal {%%normal%%}
        finish {
            specular %%edss%%
            roughness 2*%%rough%%
            phong 0 phong_size 0
            ambient 0
            diffuse 0
        }
    }
    texture {
        pigment {image_map {png "%%name%%_texture.png" filter all 1}}
        normal {%%normal%%}
        finish { 
            specular %%spec%%
            roughness %%rough%%
            phong 0 phong_size 0
            ambient 0
            diffuse 0
            reflection {0}
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

                                                                            