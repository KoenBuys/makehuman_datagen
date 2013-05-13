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

Mesh
"""

import numpy
import os
import mh2proxy
from . import mhx_drivers

#-------------------------------------------------------------------------------        
#   
#-------------------------------------------------------------------------------        

def writeMesh(fp, amt, config):

    fp.write("""
# ----------------------------- MESH --------------------- # 
""")    

    fp.write("Mesh %sMesh %sMesh\n  Verts\n" % (amt.name, amt.name))
    ox = amt.origin[0]
    oy = amt.origin[1]
    oz = amt.origin[2]
    scale = config.scale
    for co in amt.mesh.coord:
        fp.write("  v %.4f %.4f %.4f ;\n" % (scale*(co[0]-ox), scale*(-co[2]+oz), scale*(co[1]-oy)))
  
    fp.write("""
  end Verts

  Faces
""")  
    for fverts in amt.mesh.fvert:
        if fverts[0] == fverts[3]:
            fp.write("    f %d %d %d ;\n" % tuple(fverts[0:3]))
        else:
            fp.write("    f %d %d %d %d ;\n" % tuple(fverts))

    writeFaceNumbers(fp, amt, config)

    fp.write("""
  end Faces
  
  MeshTextureFaceLayer UVTex
    Data 
""")

    if amt.human.uvset:
        for ft in amt.human.uvset.texFaces:
            fp.write("    vt")
            for vt in ft:
                uv = amt.human.uvset.texVerts[vt]
                fp.write(" %.4g %.4g" %(uv[0], uv[1]))
            fp.write(" ;\n")
    else:
        for fuv in amt.mesh.fuvs:
            uv0 = amt.mesh.texco[fuv[0]]
            uv1 = amt.mesh.texco[fuv[1]]
            uv2 = amt.mesh.texco[fuv[2]]
            uv3 = amt.mesh.texco[fuv[3]]
            if fuv[0] == fuv[3]:
                fp.write("    vt %.4g %.4g %.4g %.4g %.4g %.4g ;\n" % (uv0[0], uv0[1], uv1[0], uv1[1], uv2[0], uv2[1]))
            else:
                fp.write("    vt %.4g %.4g %.4g %.4g %.4g %.4g %.4g %.4g ;\n" % (uv0[0], uv0[1], uv1[0], uv1[1], uv2[0], uv2[1], uv3[0], uv3[1]))

    fp.write("""
    end Data
    active True ;
    active_clone True ;
    active_render True ;
  end MeshTextureFaceLayer  
""")

    writeBaseMaterials(fp, amt)
    writeVertexGroups(fp, amt, config, None)

    fp.write("""
end Mesh
""")

    fp.write(
        "Object %sMesh MESH %sMesh\n"  % (amt.name, amt.name) +
        "  Property MhxOffsetX %.4f ;\n" % amt.origin[0] +
        "  Property MhxOffsetY %.4f ;\n" % amt.origin[1] +
        "  Property MhxOffsetZ %.4f ;\n" % amt.origin[2])
    fp.write("""
  layers Array 1 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0  ;
#if toggle&T_Armature
""")

    writeArmatureModifier(fp, amt, config, None)

    fp.write("  parent Refer Object %s ;\n" % amt.name)
    fp.write("""
  parent_type 'OBJECT' ;
#endif
  color Array 1.0 1.0 1.0 1.0  ;
  select True ;
  lock_location Array 1 1 1 ; 
  lock_rotation Array 1 1 1 ;
  lock_scale Array 1 1 1  ; 
  Property MhxScale theScale ;
  Property MhxMesh True ;
  Modifier SubSurf SUBSURF
    levels 0 ;
    render_levels 1 ;
  end Modifier
end Object
""")

    writeHideAnimationData(fp, amt, "", amt.name)
    return


#-------------------------------------------------------------------------------        
#   Armature modifier. 
#-------------------------------------------------------------------------------        

def writeArmatureModifier(fp, amt, config, proxy):
    if (config.cage and
        not (proxy and proxy.cage)):
    
        fp.write("""
  #if toggle&T_Cage
    Modifier MeshDeform MESH_DEFORM
      invert_vertex_group False ;
""")
        fp.write("  object Refer Object %sCageMesh ;" % amt.name)
        fp.write("""
      precision 6 ;
      use_dynamic_bind True ;
    end Modifier
    Modifier Armature ARMATURE
      invert_vertex_group False ;
""")
        fp.write("  object Refer Object %s ;" % amt.name)
        fp.write("""
      use_bone_envelopes False ;
      use_multi_modifier True ;
      use_vertex_groups True ;
      vertex_group 'Cage' ;
    end Modifier
  #else
    Modifier Armature ARMATURE
""")
        fp.write("  object Refer Object %s ;" % amt.name)
        fp.write("""
      use_bone_envelopes False ;
      use_vertex_groups True ;
    end Modifier
  #endif
""")

    else:
    
        fp.write("""
    Modifier Armature ARMATURE
""")
        fp.write("  object Refer Object %s ;" % amt.name)
        fp.write("""
      use_bone_envelopes False ;
      use_vertex_groups True ;
    end Modifier
""")
    
#-------------------------------------------------------------------------------        
#   Face numbers
#-------------------------------------------------------------------------------        

MaterialNumbers = {
    ""       : 0,     # skin
    "skin"   : 0,     # skin
    "nail"   : 1,     # nail
    "teeth"  : 1,     # teeth
    "eye"    : 1,     # eye
    "cornea" : 1,     # cornea
    "brow"   : 1,     # brows
    "joint"  : 2,     # joint
    "red"    : 3,     # red
    "green"  : 4,     # green
    "blue"   : 5      # blue
}
    
def writeFaceNumbers(fp, amt, config):
    if amt.human.uvset:
        for ftn in amt.human.uvset.faceNumbers:
            fp.write(ftn)
    else:            
        obj = amt.mesh
        fmats = numpy.zeros(len(obj.coord), int)
        for fn,mtl in obj.materials.items():
            fmats[fn] = MaterialNumbers[mtl]
            
        # TODO use facemask set on module3d instead (cant we reuse filterMesh from collect module?)
        deleteVerts = None
        deleteGroups = []

        for fg in obj.faceGroups: 
            fmask = obj.getFaceMaskForGroups([fg.name])
            if mh2proxy.deleteGroup(fg.name, deleteGroups):
                fmats[fmask] = 6
            elif "joint" in fg.name:
                fmats[fmask] = 4
            elif fg.name == "helper-tights":                    
                fmats[fmask] = 5
            elif fg.name == "helper-skirt":                    
                fmats[fmask] = 7
            elif ("tongue" in fg.name):
                fmats[fmask] = 1
            elif ("eyebrown" in fg.name) or ("lash" in fg.name):
                fmats[fmask] = 3
                    
        if deleteVerts != None:
            for fn,fverts in enumerate(obj.fvert):
                if deleteVerts[fverts[0]]:
                    fmats[fn] = 6                        
                
        mn = -1
        fn = 0
        f0 = 0
        for fverts in obj.fvert:
            if fmats[fn] != mn:
                if fn != f0:
                    fp.write("  ftn %d %d 1 ;\n" % (fn-f0, mn))
                mn = fmats[fn]
                f0 = fn
            fn += 1
        if fn != f0:
            fp.write("  ftn %d %d 1 ;\n" % (fn-f0, mn))

#-------------------------------------------------------------------------------        
#   Material access
#-------------------------------------------------------------------------------        

def writeBaseMaterials(fp, amt):      
    if amt.human.uvset:
        for mat in amt.human.uvset.materials:
            fp.write("  Material %s_%s ;\n" % (amt.name, mat.name))
    else:
        fp.write(
"  Material %sSkin ;\n" % amt.name +
"  Material %sShiny ;\n" % amt.name +
"  Material %sInvisio ;\n" % amt.name +
"  Material %sRed ;\n" % amt.name +
"  Material %sGreen ;\n" % amt.name +
"  Material %sBlue ;\n" % amt.name
)
    

def writeHideAnimationData(fp, amt, prefix, name):
    fp.write("AnimationData %s%sMesh True\n" % (prefix, name))
    mhx_drivers.writePropDriver(fp, amt, ["Mhh%s" % name], "x1", "hide", -1)
    mhx_drivers.writePropDriver(fp, amt, ["Mhh%s" % name], "x1", "hide_render", -1)
    fp.write("end AnimationData\n")
    return    
       
#-------------------------------------------------------------------------------        
#   Vertex groups   
#-------------------------------------------------------------------------------        

def writeVertexGroups(fp, amt, config, proxy):                
    if proxy and proxy.weights:
        writeRigWeights(fp, proxy.weights)
        return

    if amt.vertexWeights:
        if proxy:
            weights = mh2proxy.getProxyWeights(amt.vertexWeights, proxy)
        else:
            weights = amt.vertexWeights                    
        writeRigWeights(fp, weights)
    else:
        for file in amt.vertexGroupFiles:
            copyVertexGroups(file, fp, proxy)
            
    #for path in config.customvertexgroups:
    #    print("    %s" % path)
    #    copyVertexGroups(path, fp, proxy)    

    if config.cage and not (proxy and proxy.cage):
        fp.write("#if toggle&T_Cage\n")
        copyVertexGroups("cage", fp, proxy)    
        fp.write("#endif\n")

    copyVertexGroups("leftright", fp, proxy)    
    copyVertexGroups("tight-leftright", fp, proxy)    
    copyVertexGroups("skirt-leftright", fp, proxy)    
    return


def getVertexGroups(name, vgroups):
    file = os.path.join("shared/mhx/vertexgroups", name + ".vgrp")
    fp = open(file, "rU")
    vgroupList = []
    for line in fp:
        words = line.split()
        if len(words) < 2:
            continue
        elif words[1] == "weights":
            name = words[2]
            try:
                vgroup = vgroups[name]
            except KeyError:
                vgroup = []
                vgroups[name] = vgroup 
            vgroupList.append((name, vgroup))
        else:
            vgroup.append((int(words[0]), float(words[1])))
    fp.close()            
    return vgroupList            


def copyVertexGroups(name, fp, proxy):
    vgroupList = getVertexGroups(name, {})
    if not proxy:
        for (name, weights) in vgroupList:
            fp.write("  VertexGroup %s\n" % name)
            for (v,wt) in weights:
                fp.write("    wv %d %.4g ;\n" % (v,wt))
            fp.write("  end VertexGroup\n\n")
    else:
        for (name, weights) in vgroupList:
            pgroup = []
            for (v,wt) in weights:
                try:
                    vlist = proxy.vertWeights[v]
                except:
                    vlist = []
                for (pv, w) in vlist:
                    pw = w*wt
                    if pw > 1e-4:
                        pgroup.append((pv, pw))
            if pgroup:
                fp.write("  VertexGroup %s\n" % name)
                printProxyVGroup(fp, pgroup)
                fp.write("  end VertexGroup\n\n")
    

def printProxyVGroup(fp, vgroups):
    vgroups.sort()
    pv = -1
    while vgroups:
        (pv0, wt0) = vgroups.pop()
        if pv0 == pv:
            wt += wt0
        else:
            if pv >= 0 and wt > 1e-4:
                fp.write("    wv %d %.4f ;\n" % (pv, wt))
            (pv, wt) = (pv0, wt0)
    if pv >= 0 and wt > 1e-4:
        fp.write("    wv %d %.4f ;\n" % (pv, wt))
    return

    
def writeRigWeights(fp, weights):
    for grp in weights.keys():
        fp.write("\n  VertexGroup %s\n" % grp)
        for (v,w) in weights[grp]:
            fp.write("    wv %d %.4f ;\n" % (v,w))
        fp.write("  end VertexGroup\n")
    return
    
    
