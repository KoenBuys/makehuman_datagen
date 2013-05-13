#!/usr/bin/python
# -*- coding: utf-8 -*-

""" 
**Project Name:**      MakeHuman

**Product Home Page:** http://www.makeinfo.human.org/

**Code Home Page:**    http://code.google.com/p/makehuman/

**Authors:**           Thomas Larsson

**Copyright(c):**      MakeHuman Team 2001-2013

**Licensing:**         AGPL3 (see also http://www.makeinfo.human.org/node/318)

**Coding Standards:**  See http://www.makeinfo.human.org/node/165

Abstract
--------

Proxies
"""

import os
import log
import gui3d

from . import mhx_mesh
from . import mhx_materials

#-------------------------------------------------------------------------------        
#   
#-------------------------------------------------------------------------------        

def writeProxyType(type, test, amt, config, fp, t0, t1):
    n = 0
    for proxy in amt.proxies.values():
        if proxy.type == type:
            n += 1
    if n == 0:
        return
        
    dt = (t1-t0)/n
    t = t0
    for proxy in amt.proxies.values():
        if proxy.type == type:
            gui3d.app.progress(t, text="Exporting %s" % proxy.name)
            fp.write("#if toggle&%s\n" % test)
            writeProxy(fp, amt, config, proxy)    
            fp.write("#endif\n")
            t += dt
        

#-------------------------------------------------------------------------------        
#   
#-------------------------------------------------------------------------------        

def writeProxy(fp, amt, config, proxy):
    fp.write("""
NoScale False ;
""")

    # Proxy materials
    
    mat = proxy.material
    if mat:
        if proxy.material_file:
            copyProxyMaterialFile(fp, proxy.material_file, mat, proxy, amt, config)
        else:
            writeProxyMaterial(fp, mat, proxy, amt, config)

    # Proxy mesh
    
    name = amt.name + proxy.name
    fp.write(
        "Mesh %sMesh %sMesh \n" % (name, name) +
        "  Verts\n")
    
    ox = amt.origin[0]
    oy = amt.origin[1]
    oz = amt.origin[2]
    scale = config.scale
    for refVert in proxy.refVerts:
        (x,y,z) = refVert.getCoord()
        fp.write("  v %.4f %.4f %.4f ;\n" % (scale*(x-ox), scale*(-z+oz), scale*(y-oy)))
  
    fp.write("""
  end Verts
  Faces
""")

    for (f,g) in proxy.faces:
        fp.write("    f")
        for v in f:
            fp.write(" %s" % v)
        fp.write(" ;\n")
    if proxy.faceNumbers:
        for ftn in proxy.faceNumbers:
            fp.write(ftn)
    else:
        fp.write("    ftall 0 1 ;\n")
  
    fp.write("  end Faces\n")
    
    # Proxy layers
    
    layers = list(proxy.uvtexLayerName.keys())
    layers.sort()
    for layer in layers:
        try:
            texfaces = proxy.texFacesLayers[layer]
            texverts = proxy.texVertsLayers[layer]
        except KeyError:
            continue
        fp.write(       
            '  MeshTextureFaceLayer %s\n' % proxy.uvtexLayerName[layer] +
            '    Data \n')
        for f in texfaces:
            fp.write("    vt")
            for v in f:
                uv = texverts[v]
                fp.write(" %.4g %.4g" % (uv[0], uv[1]))
            fp.write(" ;\n")
        fp.write(
            '    end Data\n' +
            '  end MeshTextureFaceLayer\n')

    # Proxy vertex groups
    
    mhx_mesh.writeVertexGroups(fp, amt, config, proxy)
  
    if proxy.useBaseMaterials:
        mhx_mesh.writeBaseMaterials(fp, amt)
    elif proxy.material:
        fp.write("  Material %s%s ;" % (amt.name, proxy.material.name))

  
    fp.write("""
end Mesh
""")

    # Proxy object
    
    name = amt.name + proxy.name
    fp.write(
        "Object %sMesh MESH %sMesh \n" % (name, name) +
        "  parent Refer Object %s ;\n" % amt.name +
        "  hide False ;\n" +
        "  hide_render False ;\n")
    if proxy.wire:
        fp.write("  draw_type 'WIRE' ;\n")    


    # Proxy layers 
    
    fp.write("layers Array ")
    for n in range(20):
        if n == proxy.layer:
            fp.write("1 ")
        else:
            fp.write("0 ")
    fp.write(";\n")

    fp.write("""
#if toggle&T_Armature
""")

    mhx_mesh.writeArmatureModifier(fp, amt, config, proxy) 
    writeProxyModifiers(fp, amt, proxy)

    fp.write("""
  parent_type 'OBJECT' ;
#endif
  color Array 1.0 1.0 1.0 1.0  ;
  show_name True ;
  select True ;
  lock_location Array 1 1 1 ; 
  lock_rotation Array 1 1 1 ;
  lock_scale Array 1 1 1  ; 
  Property MhxScale theScale ;
  Property MhxProxy True ;
end Object
""")

    mhx_mesh.writeHideAnimationData(fp, amt, amt.name, proxy.name)

#-------------------------------------------------------------------------------        
#   
#-------------------------------------------------------------------------------        

def writeProxyModifiers(fp, amt, proxy):
    for mod in proxy.modifiers:
        if mod[0] == 'subsurf':
            fp.write(
                "    Modifier SubSurf SUBSURF\n" +
                "      levels %d ;\n" % mod[1] +
                "      render_levels %d ;\n" % mod[2] +
                "    end Modifier\n")
        elif mod[0] == 'shrinkwrap':
            offset = mod[1]
            fp.write(
                "    Modifier ShrinkWrap SHRINKWRAP\n" +
                "      target Refer Object %sMesh ;\n" % amt.name +
                "      offset %.4f ;\n" % offset +
                "      use_keep_above_surface True ;\n" +
                "    end Modifier\n")
        elif mod[0] == 'solidify':
            thickness = mod[1]
            offset = mod[2]
            fp.write(
                "    Modifier Solidify SOLIDIFY\n" +
                "      thickness %.4f ;\n" % thickness +
                "      offset %.4f ;\n" % offset +
                "    end Modifier\n")
    return



def copyProxyMaterialFile(fp, pair, mat, proxy, amt, config):
    prxList = sortedMasks(amt, config)
    nMasks = countMasks(proxy, prxList)
    tex = None
    
    (folder, file) = pair
    folder = os.path.realpath(os.path.expanduser(folder))
    infile = os.path.join(folder, file)
    tmpl = open(infile, "rU")
    for line in tmpl:
        words= line.split()
        if len(words) == 0:
            fp.write(line)
        elif words[0] == 'Texture':
            words[1] = amt.name + words[1]
            for word in words:
                fp.write("%s " % word)
            fp.write("\n")
            tex = os.path.join(folder,words[1])
        elif words[0] == 'Material':
            words[1] = amt.name + words[1]
            for word in words:
                fp.write("%s " % word)
            fp.write("\n")
            addProxyMaskMTexs(fp, mat, proxy, prxList, tex)
        elif words[0] == 'MTex':
            words[2] = amt.name + words[2]
            for word in words:
                fp.write("%s " % word)
            fp.write("\n")                
        elif words[0] == 'Filename':
            file = config.getTexturePath(words[1], folder, True, amt.human)
            fp.write("  Filename %s ;\n" % file)
        else:
            fp.write(line)
    tmpl.close()
    return
       

def writeProxyTexture(fp, texture, mat, extra, amt, config):        
    (folder,name) = texture
    tex = os.path.join(folder,name)
    #print(amt.name)
    log.debug("Tex %s", tex)
    texname = amt.name + os.path.basename(tex)
    fromDir = os.path.dirname(tex)
    texfile = config.getTexturePath(tex, fromDir, True, None)
    fp.write(
        "Image %s\n" % texname +
        "  Filename %s ;\n" % texfile +
#        "  alpha_mode 'PREMUL' ;\n" +
        "end Image\n\n" +
        "Texture %s IMAGE\n" % texname +
        "  Image %s ;\n" % texname)
    writeProxyMaterialSettings(fp, mat.textureSettings)             
    fp.write(extra)
    fp.write("end Texture\n\n")
    return (tex, texname)
    
    
def writeProxyMaterial(fp, mat, proxy, amt, config):
    alpha = mat.alpha
    tex = None
    bump = None
    normal = None
    displacement = None
    transparency = None
    if proxy.texture:
        uuid = proxy.getUuid()
        if uuid in amt.human.clothesObjs.keys() and amt.human.clothesObjs[uuid]:
            # Apply custom texture
            clothesObj = amt.human.clothesObjs[uuid]
            texture = clothesObj.mesh.texture
            texPath = (os.path.dirname(texture), os.path.basename(texture))
            (tex,texname) = writeProxyTexture(fp, texPath, mat, "", amt, config)
        else:
            (tex,texname) = writeProxyTexture(fp, proxy.texture, mat, "", amt, config)
    if proxy.bump:
        (bump,bumpname) = writeProxyTexture(fp, proxy.bump, mat, "", amt, config)
    if proxy.normal:
        (normal,normalname) = writeProxyTexture(fp, proxy.normal, mat, 
            ("    use_normal_map True ;\n"),
            amt, config)
    if proxy.displacement:
        (displacement,dispname) = writeProxyTexture(fp, proxy.displacement, mat, "", amt, config)
    if proxy.transparency:
        (transparency,transname) = writeProxyTexture(fp, proxy.transparency, mat, "", amt, config)
           
    prxList = sortedMasks(amt, config)
    nMasks = countMasks(proxy, prxList)
    slot = nMasks
    
    fp.write("Material %s%s \n" % (amt.name, mat.name))
    addProxyMaskMTexs(fp, mat, proxy, prxList, tex)
    writeProxyMaterialSettings(fp, mat.settings)   
    uvlayer = proxy.uvtexLayerName[proxy.textureLayer]

    if tex:
        fp.write(
            "  MTex %d %s UV COLOR\n" % (slot, texname) +
            "    texture Refer Texture %s ;\n" % texname +
            "    use_map_alpha True ;\n" +
            "    diffuse_color_factor 1.0 ;\n" +
            "    uv_layer '%s' ;\n" % uvlayer)
        writeProxyMaterialSettings(fp, mat.mtexSettings)             
        fp.write("  end MTex\n")
        slot += 1
        alpha = 0
        
    if bump:
        fp.write(
            "  MTex %d %s UV NORMAL\n" % (slot, bumpname) +
            "    texture Refer Texture %s ;\n" % bumpname +
            "    use_map_normal True ;\n" +
            "    use_map_color_diffuse False ;\n" +
            "    normal_factor %.3f ;\n" % proxy.bumpStrength + 
            "    use_rgb_to_intensity True ;\n" +
            "    uv_layer '%s' ;\n" % uvlayer +
            "  end MTex\n")
        slot += 1
        
    if normal:
        fp.write(
            "  MTex %d %s UV NORMAL\n" % (slot, normalname) +
            "    texture Refer Texture %s ;\n" % normalname +
            "    use_map_normal True ;\n" +
            "    use_map_color_diffuse False ;\n" +
            "    normal_factor %.3f ;\n" % proxy.normalStrength + 
            "    normal_map_space 'TANGENT' ;\n" +
            "    uv_layer '%s' ;\n" % uvlayer +
            "  end MTex\n")
        slot += 1
        
    if displacement:
        fp.write(
"  MTex %d %s UV DISPLACEMENT\n" % (slot, dispname) +
"    texture Refer Texture %s ;\n" % dispname +
"    use_map_displacement True ;\n" +
"    use_map_color_diffuse False ;\n" +
"    displacement_factor %.3f ;\n" % proxy.dispStrength + 
"    use_rgb_to_intensity True ;\n" +
"    uv_layer '%s' ;\n" % uvlayer +
"  end MTex\n")
        slot += 1

    if transparency:        
        fp.write(
"  MTex %d %s UV ALPHA\n" % (slot, transname) +
"    texture Refer Texture %s ;\n" % transname +
"    use_map_alpha True ;\n" +
"    use_map_color_diffuse False ;\n" +
"    invert True ;\n" +
"    use_stencil True ;\n" +
"    use_rgb_to_intensity True ;\n" +
"    uv_layer '%s' ;\n" % uvlayer +
"  end MTex\n")
        slot += 1        
        
    if nMasks > 0 or alpha < 0.99:
        fp.write(
"  use_transparency True ;\n" +
"  transparency_method 'Z_TRANSPARENCY' ;\n" +
"  alpha %3.f ;\n" % alpha +
"  specular_alpha %.3f ;\n" % alpha)
    if mat.mtexSettings == []:
        fp.write(
"  use_shadows True ;\n" +
"  use_transparent_shadows True ;\n")
    fp.write(
"  Property MhxDriven True ;\n" +
"end Material\n\n")


def writeProxyMaterialSettings(fp, settings):
    for (key, value) in settings:        
        if type(value) == list:
            fp.write("  %s Array %.4f %.4f %.4f ;\n" % (key, value[0], value[1], value[2]))
        elif type(value) == float:
            fp.write("  %s %.4f ;\n" % (key, value))
        elif type(value) == int:
            fp.write("  %s %d ;\n" % (key, value))
        else:
            fp.write("  %s '%s' ;\n" % (key, value))


def addProxyMaskMTexs(fp, mat, proxy, prxList, tex):
    if proxy.maskLayer < 0:
        return
    n = 0  
    m = len(prxList)
    for (zdepth, prx) in prxList:
        m -= 1
        if zdepth > proxy.z_depth:
            n = mhx_materials.addMaskMTex(fp, prx.mask, proxy, 'MULTIPLY', n)
    if not tex:            
        n = mhx_materials.addMaskMTex(fp, (None,'solid'), proxy, 'MIX', n)
    
    
def sortedMasks(amt, config):
    if not config.useMasks:
        return []
    prxList = []
    for prx in amt.proxies.values():
        if prx.type == 'Clothes' and prx.mask:
            prxList.append((prx.z_depth, prx))
    prxList.sort()
    return prxList

    
def countMasks(proxy, prxList):
    n = 0
    for (zdepth, prx) in prxList:
        if prx.type == 'Clothes' and zdepth > proxy.z_depth:
            n += 1
    return n            

  
