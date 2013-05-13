#!/usr/bin/python
# -*- coding: utf-8 -*-

""" 
**Project Name:**      MakeHuman

**Product Home Page:** http://www.makehuman.org/

**Code Home Page:**    http://code.google.com/p/makehuman/

**Authors:**           Thomas Larsson, Jonas Hauquier

**Copyright(c):**      MakeHuman Team 2001-2013

**Licensing:**         AGPL3 (see also http://www.makehuman.org/node/318)

**Coding Standards:**  See http://www.makehuman.org/node/165

Abstract
--------
Exports proxy mesh to obj

"""

import os
import math
import exportutils
import mh2proxy

#
#    exportObj(human, filepath, config):    
#

def exportObj(human, filepath, config=None):
    if config is None:
        config = exportutils.config.Config()
    obj = human.meshData
    config.setHuman(human)
    config.setupTexFolder(filepath)
    filename = os.path.basename(filepath)
    name = config.goodName(os.path.splitext(filename)[0])

    stuffs = exportutils.collect.setupObjects(
        name, 
        human,
        config=config,
        helpers=config.helpers, 
        eyebrows=config.eyebrows, 
        lashes=config.lashes,
        subdivide=config.subdivide)
    
    fp = open(filepath, 'w')
    mtlfile = "%s.mtl" % os.path.splitext(filepath)[0]
    mtlfile = mtlfile.encode(config.encoding, 'replace')
    fp.write(
        "# MakeHuman exported OBJ\n" +
        "# www.makehuman.org\n\n" +
        "mtllib %s\n" % os.path.basename(mtlfile))

    # Vertices
    
    for stuff in stuffs:
        obj = stuff.meshInfo.object
        for co in obj.coord:
            fp.write("v %.4g %.4g %.4g\n" % tuple(co))

    # Vertex normals
    
    if config.useNormals:
        for stuff in stuffs:
            obj = stuff.meshInfo.object
            obj.calcFaceNormals()
            #obj.calcVertexNormals()
            for no in obj.fnorm:
                no = no/math.sqrt(no.dot(no))
                fp.write("vn %.4g %.4g %.4g\n" % tuple(no))


    # UV vertices
    
    for stuff in stuffs:
        obj = stuff.meshInfo.object
        if obj.has_uv:
            for uv in obj.texco:
                fp.write("vt %.4g %.4g\n" % tuple(uv))

    # Faces
    
    nVerts = 1
    nTexVerts = 1
    for stuff in stuffs:
        fp.write("usemtl %s\n" % stuff.name)
        fp.write("g %s\n" % stuff.name)    
        obj = stuff.meshInfo.object
        for fn,fv in enumerate(obj.fvert):
            fp.write('f ')
            fuv = obj.fuvs[fn]                
            if fv[0] == fv[3]:
                nv = 3
            else:
                nv = 4
            if config.useNormals:
                if obj.has_uv:            
                    for n in range(nv):
                        vn = fv[n]+nVerts
                        fp.write("%d/%d/%d " % (vn, fuv[n]+nTexVerts, fn))
                else:
                    for n in range(nv):
                        vn = fv[n]+nVerts
                        fp.write("%d//%d " % (vn, fn))
            else:
                if obj.has_uv:
                    for n in range(nv):
                        vn = fv[n]+nVerts
                        fp.write("%d/%d " % (vn, fuv[n]+nTexVerts))
                else:
                    for n in range(nv):
                        vn = fv[n]+nVerts
                        fp.write("%d " % (vn))
            fp.write('\n')
        
        nVerts += len(obj.coord)
        nTexVerts += len(obj.texco)
        
    fp.close()
    
    fp = open(mtlfile, 'w')
    fp.write(
        '# MakeHuman exported MTL\n' +
        '# www.makehuman.org\n\n')
    for stuff in stuffs:
        writeMaterial(fp, stuff, human, config)
    fp.close()
    return

#
#   writeMaterial(fp, stuff, human, config):
#

def writeMaterial(fp, stuff, human, config):
    fp.write("\nnewmtl %s\n" % stuff.name)
    diffuse = (1, 1, 1)
    spec = (1, 1, 1)
    diffScale = 0.8
    specScale = 0.02
    alpha = 1
    if stuff.material:
        for (key, value) in stuff.material.settings:
            if key == "diffuse_color":
                diffuse = value
            elif key == "specular_color":
                spec = value
            elif key == "diffuse_intensity":
                diffScale = value
            elif key == "specular_intensity":
                specScale = value
            elif key == "alpha":
                alpha = value
                
    fp.write(
        "Kd %.4g %.4g %.4g\n" % (diffScale*diffuse[0], diffScale*diffuse[1], diffScale*diffuse[2]) +
        "Ks %.4g %.4g %.4g\n" % (specScale*spec[0], specScale*spec[1], specScale*spec[2]) +
        "d %.4g\n" % alpha
    )
    
    if stuff.proxy:
        writeTexture(fp, "map_Kd", stuff.texture, human, config)
        #writeTexture(fp, "map_Tr", stuff.proxy.translucency, human, config)
        writeTexture(fp, "map_Disp", stuff.proxy.normal, human, config)
        writeTexture(fp, "map_Disp", stuff.proxy.displacement, human, config)
    else:        
        writeTexture(fp, "map_Kd", ("data/textures", "texture.png"), human, config)


def writeTexture(fp, key, texture, human, config):
    if not texture:
        return
    (folder, texfile) = texture
    texpath = config.getTexturePath(texfile, folder, True, human)        
    (fname, ext) = os.path.splitext(texfile)  
    name = "%s_%s" % (fname, ext[1:])
    print(texpath)
    fp.write("%s %s\n" % (key, texpath))
    

"""    
Ka 1.0 1.0 1.0
Kd 1.0 1.0 1.0
Ks 0.33 0.33 0.52
illum 5
Ns 50.0
map_Kd texture.png
"""
