
// Create the skin material.
// This texture implements a SubSurface Scattering method
// using premade lightmaps.  
#ifndef (%%name%%_Material)                            

#declare %%name%%_Texture = 
    texture { // Apply high blur to red channel.
        pigment { image_map {png "%%name%%_sss_redlmap.png" interpolate 2} }
        normal  {%%rednormal%%}
        finish { 
            specular 0
            roughness 0.01
            phong 0 phong_size 0
            ambient 0
            diffuse 6
            reflection {0}
            conserve_energy
        }
    }
    texture { // Apply medium blur to green channel.
        pigment { image_map {png "%%name%%_sss_greenlmap.png" interpolate 2 transmit all 1/2} }
        normal  {%%greennormal%%}
        finish { 
            specular 6*%%edss%%
            roughness 2*%%rough%%
            phong 0 phong_size 0
            ambient 0
            diffuse 6
            reflection {0}
            conserve_energy
        }
    }
    texture { // Apply no blur to blue channel.
        pigment { image_map {png "%%name%%_sss_bluelmap.png" interpolate 2 transmit all 2/3} }
        normal  {%%bluenormal%%}
        finish { 
            specular 0
            roughness 0.01
            phong 0 phong_size 0
            ambient 0
            diffuse 6
            reflection {0}
            conserve_energy
        }
    }
    texture { // Ambience.
        pigment {rgbt <1, 1, 1, 0.5>}
        finish {
            specular 0
            roughness 0.01
            phong 0 phong_size 0
            ambient rgb 2*%%ambience%%
            diffuse 0
            reflection {0}
            conserve_energy
        }
    }
    texture {
        pigment { image_map {png "%%name%%_texture.png" filter all 1} }
        normal  {%%normal%%}
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

                                                                            