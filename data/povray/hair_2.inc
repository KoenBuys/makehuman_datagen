#ifndef (%%name%%_Material)

#declare %%name%%_hairtex0 =
    texture {
        pigment {image_map {%%texture%% interpolate 2}}          
        finish {
            specular 0
            roughness 1
            phong 0 phong_size 0 
            ambient %%ambience%%
            diffuse 1 - %%spec%%
            conserve_energy
        }
    }
    

#declare %%name%%_hairtex1 =
    texture {
        pigment {rgb 1}         
        normal { bump_map {%%bumpmap%% interpolate 2} %%hard%%}
        finish {
            specular %%spec%%
            roughness 2*%%rough%%
            phong 0 phong_size 0 
            ambient %%ambience%%
            diffuse 1 - %%spec%%
            conserve_energy
        }
    }
    texture {
        pigment {image_map {%%texture%% interpolate 2 filter all 1}}          
        normal { bump_map {%%bumpmap%% interpolate 2} %%hard%%}
        finish {
            specular %%spec%%
            roughness %%rough%%
            phong 0 phong_size 0 
            ambient 0
            diffuse 0
            conserve_energy
        }
    }


#declare %%name%%_Material = material {
    texture {
        uv_mapping
        pigment_pattern {image_map {png "%%name%%_alpha.png" interpolate 2}}
        texture_map {
            [0 %%name%%_hairtex0]
            [1 %%name%%_hairtex1]    
        }
    }
}
#end   
