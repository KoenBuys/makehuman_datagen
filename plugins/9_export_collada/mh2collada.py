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

MakeHuman to Collada (MakeHuman eXchange format) exporter. Collada files can be loaded into
Blender by collada_import.py.

TODO
"""

import os.path
import time
import numpy
import log

import gui3d
import exportutils
import posemode

#
#    Size of end bones = 1 mm
# 
Delta = [0,0.01,0]


#
# exportCollada(human, filepath, config):
#

def exportCollada(human, filepath, config):    
    posemode.exitPoseMode()        
    posemode.enterPoseMode()
    gui3d.app.progress(0, text="Exporting %s" % filepath)

    time1 = time.clock()
    config.setHuman(human)
    config.setupTexFolder(filepath)        
    try:
        fp = open(filepath, 'w')
        log.message("Writing Collada file %s" % filepath)
    except:
        log.error("Unable to open file for writing %s" % filepath)

    filename = os.path.basename(filepath)
    name = config.goodName(os.path.splitext(filename)[0])
    exportDae(human, name, fp, config)

    fp.close()
    time2 = time.clock()
    log.message("Wrote Collada file in %g s: %s" % (time2-time1, filepath))
    gui3d.app.progress(1)
    posemode.exitPoseMode()        
    return


def exportDae(human, name, fp, config):
    rigfile = "data/rigs/%s.rig" % config.rigtype
    rawTargets = exportutils.collect.readTargets(human, config)
    stuffs = exportutils.collect.setupObjects(
        name, 
        human, 
        config=config,
        rigfile=rigfile, 
        rawTargets = rawTargets,
        helpers=config.helpers, 
        eyebrows=config.eyebrows, 
        lashes=config.lashes)
    mainStuff = stuffs[0]        

    date = time.strftime("%a, %d %b %Y %H:%M:%S +0000", time.localtime())
    if config.rotate90X:
        upaxis = 'Z_UP'
    else:
        upaxis = 'Y_UP'
        
    fp.write('<?xml version="1.0" encoding="utf-8"?>\n' +
        '<COLLADA version="1.4.0" xmlns="http://www.collada.org/2005/11/COLLADASchema">\n' +
        '  <asset>\n' +
        '    <contributor>\n' +
        '      <author>www.makehuman.org</author>\n' +
        '    </contributor>\n' +
        '    <created>%s</created>\n' % date +
        '    <modified>%s</modified>\n' % date +
        '    <unit meter="%.4f" name="meter"/>\n' % (0.1/config.scale) +
        '    <up_axis>%s</up_axis>\n' % upaxis+
        '  </asset>\n' +
        '  <library_images>\n')

    for stuff in stuffs:
        writeImages(fp, stuff, human, config)

    fp.write(
        '  </library_images>\n' +
        '  <library_effects>\n')

    gui3d.app.progress(0.1, text="Exporting effects")
    for stuff in stuffs:
        writeEffects(fp, stuff)

    fp.write(
        '  </library_effects>\n' +
        '  <library_materials>\n')

    gui3d.app.progress(0.2, text="Exporting materials")
    for stuff in stuffs:
        writeMaterials(fp, stuff)

    fp.write(
        '  </library_materials>\n'+
        '  <library_controllers>\n')

    gui3d.app.progress(0.3, text="Exporting controllers")
    for stuff in stuffs:
        writeController(fp, stuff, config)

    fp.write(
        '  </library_controllers>\n'+
        '  <library_geometries>\n')

    dt = 0.4/len(stuffs)
    t = 0.4
    for stuff in stuffs:
        gui3d.app.progress(t, text="Exporting %s" % stuff.name)
        t += dt
        writeGeometry(fp, stuff, config)

    fp.write(
        '  </library_geometries>\n\n' +
        '  <library_visual_scenes>\n' +
        '    <visual_scene id="Scene" name="Scene">\n' +
        '      <node id="Armature">\n')

    gui3d.app.progress(0.8, text="Exporting bones")
    for root in mainStuff.boneInfo.hier:
        writeBone(fp, root, [0,0,0], 'layer="L1"', '  ', mainStuff, config)

    fp.write(
        '      </node>\n')

    gui3d.app.progress(0.9, text="Exporting nodes")
    for stuff in stuffs:
        writeNode(fp, "        ", stuff, config)

    fp.write(
        '    </visual_scene>\n' +
        '  </library_visual_scenes>\n' +
        '  <scene>\n' +
        '    <instance_visual_scene url="#Scene"/>\n' +
        '  </scene>\n' +
        '</COLLADA>\n')
    return

#
#    writeImages(fp, stuff, human, config):
#

def writeImages(fp, stuff, human, config):
    if stuff.texture:
        textures = [stuff.texture]
    else:
        textures = []

    for (folder, texname) in textures: 
        path = config.getTexturePath(texname, folder, True, human)        
        texfile = os.path.basename(path)
        (fname, ext) = os.path.splitext(texname)  
        name = "%s_%s" % (fname, ext[1:])
        if config.useTexFolder:
            texpath = "textures/"+texfile
        else:
            texpath = path
        fp.write(
            '    <image id="%s" name="%s">\n' % (name, name) +
            '      <init_from>%s</init_from>\n' % texpath +
            '    </image>\n'
        )
    return

#
#    writeEffects(fp, stuff):
#

def writeColor(fp, tech, tex, color, s):
    (r,g,b) = color
    fp.write('            <%s><color>%.4f %.4f %.4f 1</color> \n' % (tech, r*s, g*s, b*s) )
    if tex:
        fp.write('              <texture texture="%s-sampler" texcoord="UVTex"/>\n' % tex)
    fp.write('            </%s>\n' % tech)
    return 
    
def writeIntensity(fp, tech, tex, value):
    fp.write('            <%s><float>%s</float>\n' % (tech, value))
    if tex:
        fp.write('              <texture texture="%s-sampler" texcoord="UVTex"/>\n' % tex)
    fp.write('            </%s>\n' % tech)
    return
    
def writeTexture(fp, tech, tex):            
    fp.write(
        '            <%s>\n' % tech +
        '              <texture texture="%s-sampler" texcoord="UVTex"/>\n' % tex +
        '            </%s>\n' % tech)
    return    
    
BlenderDaeColor = {
    'diffuse_color' : 'diffuse',
    'specular_color' : 'specular',
    'emit_color' : 'emission',
    'ambient_color' : 'ambient',
}

BlenderDaeIntensity = {
    'specular_hardness' : 'shininess',
}

DefaultMaterialSettings = {    
    'diffuse': (0.8,0.8,0.8),
    'specular': (0.1,0.1,0.1),
    'transparency' : 1,
    'shininess' : 10,
}

def writeEffects(fp, stuff):
    (texname, texfile, matname) = exportutils.collect.getTextureNames(stuff)
    if not stuff.type:
        tex = "texture_png"
        writeEffectStart(fp, "SkinShader")
        writeSurfaceSampler(fp, tex)
        #writeSurfaceSampler(fp, "texture_ref_png")
        writePhongStart(fp)
        writeTexture(fp, 'diffuse', tex)
        writeTexture(fp, 'transparent', tex)
        writeColor(fp, 'specular', None, (1,1,1), 0.1)        
        writeIntensity(fp, 'shininess', None, 10)
        writeIntensity(fp, 'transparency', None, 0)
        writePhongEnd(fp)            
    elif matname:
        matname = matname.replace(" ", "_")
        mat = stuff.material
        writeEffectStart(fp, matname)
        writeSurfaceSampler(fp, texfile)
        writePhongStart(fp)
        doneDiffuse = False
        doneSpec = False
        diffInt = 1
        specInt = 0.1
        for (key, value) in mat.settings:
            if key == "diffuse_intensity":
                diffInt = value
            elif key == "specular_intensity":
                specInt = value
        for (key, value) in mat.settings:
            if key == "diffuse_color":
                writeColor(fp, 'diffuse', texfile, value, diffInt)
                if mat.use_transparency:
                    writeTexture(fp, 'transparent', texfile)
                    writeIntensity(fp, 'transparency', None, mat.alpha)
                doneDiffuse = True
            elif key == "specular_color":
                writeColor(fp, 'specular', None, value, specInt)
                doneSpec = True
            else:                
                try:
                    tech = BlenderDaeColor[key]
                except:
                    tech = None
                if tech:
                    writeColor(fp, tech, None, value, 1)
                try:
                    tech = BlenderDaeIntensity[tech]
                except:
                    tech = None
                if tech:
                    writeIntensity(fp, tech, None, value, 1)
        if not doneDiffuse:   
            writeColor(fp, "diffuse", texfile, (1,1,1), 0.8)
            if mat.use_transparency:
                writeTexture(fp, 'transparent', texfile)
                writeIntensity(fp, 'transparency', None, mat.alpha)
        if not doneSpec:
            writeColor(fp, 'specular', None, (1,1,1), 0.1)        
            writeIntensity(fp, 'shininess', None, 10)                
        writePhongEnd(fp)
    return

def writeEffectStart(fp, name):        
    fp.write(
       '    <effect id="%s-effect">\n' % name +
       '      <profile_COMMON>\n')

def writePhongStart(fp): 
    fp.write(
        '        <technique sid="common">\n' +
        '          <phong>\n')

def writePhongEnd(fp):        
    fp.write(
        '          </phong>\n' +
        '          <extra/>\n' +
        '        </technique>\n' +
        '        <extra>\n' +
        '          <technique profile="GOOGLEEARTH">\n' +
        '            <show_double_sided>1</show_double_sided>\n' +
        '          </technique>\n' +
        '        </extra>\n' +
        '      </profile_COMMON>\n' +
        '      <extra><technique profile="MAX3D"><double_sided>1</double_sided></technique></extra>\n' +
        '    </effect>\n')

def writeSurfaceSampler(fp, tex):
    fp.write(
        '        <newparam sid="%s-surface">\n' % tex +
        '          <surface type="2D">\n' +
        '            <init_from>%s</init_from>\n' % tex +
        '          </surface>\n' +
        '        </newparam>\n' +
        '        <newparam sid="%s-sampler">\n' % tex +
        '          <sampler2D>\n' +
        '            <source>%s-surface</source>\n' % tex +
        '          </sampler2D>\n' +
        '        </newparam>\n')

#
#    writeMaterials(fp, stuff):
#

def writeMaterials(fp, stuff):
    (texname, texfile, matname) = exportutils.collect.getTextureNames(stuff)
    if matname:
        matname = matname.replace(" ", "_")
        fp.write(
            '    <material id="%s" name="%s">\n' % (matname, matname) +
            '      <instance_effect url="#%s-effect"/>\n' % matname +
            '    </material>\n')
    return

#
#    writeController(fp, stuff, config):
#

def writeController(fp, stuff, config):
    obj = stuff.meshInfo.object
    exportutils.collect.setStuffSkinWeights(stuff)
    nVerts = len(obj.coord)
    nUvVerts = len(obj.texco)
    nFaces = len(obj.fvert)
    nWeights = len(stuff.skinWeights)
    nBones = len(stuff.boneInfo.bones)
    nShapes = len(stuff.meshInfo.shapes)

    fp.write('\n' +
        '    <controller id="%s-skin">\n' % stuff.name +
        '      <skin source="#%sMesh">\n' % stuff.name +
        '        <bind_shape_matrix>\n' +
        '          1.0 0.0 0.0 0.0 \n' +
        '          0.0 1.0 0.0 0.0 \n' +
        '          0.0 0.0 1.0 0.0 \n' +
        '          0.0 0.0 0.0 1.0 \n' +
        '        </bind_shape_matrix>\n' +
        '        <source id="%s-skin-joints">\n' % stuff.name +
        '          <IDREF_array count="%d" id="%s-skin-joints-array">\n' % (nBones,stuff.name) +
        '           ')

    for b in stuff.boneInfo.bones:
        fp.write(' %s' % b)
    
    fp.write('\n' +
        '          </IDREF_array>\n' +
        '          <technique_common>\n' +
        '            <accessor count="%d" source="#%s-skin-joints-array" stride="1">\n' % (nBones,stuff.name) +
        '              <param type="IDREF" name="JOINT"></param>\n' +
        '            </accessor>\n' +
        '          </technique_common>\n' +
        '        </source>\n' +
        '        <source id="%s-skin-weights">\n' % stuff.name +
        '          <float_array count="%d" id="%s-skin-weights-array">\n' % (nWeights,stuff.name) +
        '           ')

    for (n,b) in enumerate(stuff.skinWeights):
        (v,w) = stuff.skinWeights[n]
        fp.write(' %s' % w)

    fp.write('\n' +
        '          </float_array>\n' +    
        '          <technique_common>\n' +
        '            <accessor count="%d" source="#%s-skin-weights-array" stride="1">\n' % (nWeights,stuff.name) +
        '              <param type="float" name="WEIGHT"></param>\n' +
        '            </accessor>\n' +
        '          </technique_common>\n' +
        '        </source>\n' +
        '        <source id="%s-skin-poses">\n' % stuff.name +
        '          <float_array count="%d" id="%s-skin-poses-array">' % (16*nBones,stuff.name))

    mat = [[1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]]
    for b in stuff.boneInfo.bones:
        vec = stuff.boneInfo.heads[b]
        (x,y,z) = rotateLoc(vec, config)
        mat[0][3] = -x
        mat[1][3] = -y
        mat[2][3] = -z
        fp.write('\n            ')
        for i in range(4):
            for j in range(4):
                fp.write('%.4f ' % mat[i][j])

    fp.write('\n' +
        '          </float_array>\n' +    
        '          <technique_common>\n' +
        '            <accessor count="%d" source="#%s-skin-poses-array" stride="16">\n' % (nBones,stuff.name) +
        '              <param type="float4x4"></param>\n' +
        '            </accessor>\n' +
        '          </technique_common>\n' +
        '        </source>\n' +
        '        <joints>\n' +
        '          <input semantic="JOINT" source="#%s-skin-joints"/>\n' % stuff.name +
        '          <input semantic="INV_BIND_MATRIX" source="#%s-skin-poses"/>\n' % stuff.name +
        '        </joints>\n' +
        '        <vertex_weights count="%d">\n' % nVerts +
        '          <input offset="0" semantic="JOINT" source="#%s-skin-joints"/>\n' % stuff.name +
        '          <input offset="1" semantic="WEIGHT" source="#%s-skin-weights"/>\n' % stuff.name +
        '          <vcount>\n' +
        '            ')

    for wts in stuff.vertexWeights.values():
        fp.write('%d ' % len(wts))

    fp.write('\n' +
        '          </vcount>\n'
        '          <v>\n' +
        '           ')

    #print(stuff.vertexWeights)
    for (vn,wts) in stuff.vertexWeights.items():
        wtot = 0.0
        for (bn,wn) in wts:
            wtot += wn
        if wtot < 0.01:
            # print("wtot", vn, wtot)
            wtot = 1
        for (bn,wn) in wts:
            fp.write(' %d %d' % (bn, wn))

    fp.write('\n' +
        '          </v>\n' +
        '        </vertex_weights>\n' +
        '      </skin>\n' +
        '    </controller>\n')

    # Morph controller
    
    if stuff.meshInfo.shapes:
        nShapes = len(stuff.meshInfo.shapes)
        
        fp.write(        
            '    <controller id="%sMorph" name="%sMorph">\n' % (stuff.name, stuff.name)+
            '      <morph source="#%sMesh" method="NORMALIZED">\n' % (stuff.name) +
            '        <source id="%sTargets">\n' % (stuff.name) +
            '          <IDREF_array id="%sTargets-array" count="%d">' % (stuff.name, nShapes))

        for key,_ in stuff.meshInfo.shapes:
            fp.write(" %sMeshMorph_%s" % (stuff.name, key))

        fp.write(
            '        </IDREF_array>\n' +
            '          <technique_common>\n' +
            '            <accessor source="#%sTargets-array" count="%d" stride="1">\n' % (stuff.name, nShapes) +
            '              <param name="IDREF" type="IDREF"/>\n' +
            '            </accessor>\n' +
            '          </technique_common>\n' +
            '        </source>\n' +
            '        <source id="%sWeights">\n' % (stuff.name) +
            '          <float_array id="%sWeights-array" count="%d">' % (stuff.name, nShapes))

        fp.write(nShapes*" 0")

        fp.write('\n' +
            '        </float_array>\n' +
            '          <technique_common>\n' +
            '            <accessor source="#%sWeights-array" count="%d" stride="1">\n' % (stuff.name, nShapes) +
            '              <param name="MORPH_WEIGHT" type="float"/>\n' +
            '            </accessor>\n' +
            '          </technique_common>\n' +
            '        </source>\n' +
            '        <targets>\n' +
            '          <input semantic="MORPH_TARGET" source="#%sTargets"/>\n' % (stuff.name) +
            '          <input semantic="MORPH_WEIGHT" source="#%sWeights"/>\n' % (stuff.name) +
            '        </targets>\n' +
            '      </morph>\n' +
            '    </controller>\n')



#
#    writeGeometry(fp, stuff, config):
#
        
def writeGeometry(fp, stuff, config):
    obj = stuff.meshInfo.object
    nVerts = len(obj.coord)
    nUvVerts = len(obj.texco)
    nWeights = len(stuff.skinWeights)
    nBones = len(stuff.boneInfo.bones)
    nShapes = len(stuff.meshInfo.shapes)

    fp.write('\n' +
        '    <geometry id="%sMesh" name="%s">\n' % (stuff.name,stuff.name) +
        '      <mesh>\n' +
        '        <source id="%s-Position">\n' % stuff.name +
        '          <float_array count="%d" id="%s-Position-array">\n' % (3*nVerts,stuff.name) +
        '          ')


    for co in obj.coord:
        (x,y,z) = rotateLoc(co, config)
        fp.write("%.4f %.4f %.4f " % (x,y,z))

    fp.write('\n' +
        '          </float_array>\n' +
        '          <technique_common>\n' +
        '            <accessor count="%d" source="#%s-Position-array" stride="3">\n' % (nVerts,stuff.name) +
        '              <param type="float" name="X"></param>\n' +
        '              <param type="float" name="Y"></param>\n' +
        '              <param type="float" name="Z"></param>\n' +
        '            </accessor>\n' +
        '          </technique_common>\n' +
        '        </source>\n')

    # Normals
    
    if config.useNormals:
        obj.calcFaceNormals()
        nNormals = len(obj.fnorm)
        fp.write(
            '        <source id="%s-Normals">\n' % stuff.name +
            '          <float_array count="%d" id="%s-Normals-array">\n' % (3*nNormals,stuff.name) +
            '          ')

        for no in obj.fnorm:
            (x,y,z) = rotateLoc(no, config)
            fp.write("%.4f %.4f %.4f " % (x,y,z))

        fp.write('\n' +
            '          </float_array>\n' +
            '          <technique_common>\n' +
            '            <accessor count="%d" source="#%s-Normals-array" stride="3">\n' % (nNormals,stuff.name) +
            '              <param type="float" name="X"></param>\n' +
            '              <param type="float" name="Y"></param>\n' +
            '              <param type="float" name="Z"></param>\n' +
            '            </accessor>\n' +
            '          </technique_common>\n' +
            '        </source>\n')
    
    # UV coordinates
    
    fp.write(
        '        <source id="%s-UV">\n' % stuff.name +
        '          <float_array count="%d" id="%s-UV-array">\n' % (2*nUvVerts,stuff.name) +
        '           ')


    for uv in obj.texco:
        fp.write(" %.4f %.4f" % tuple(uv))

    fp.write('\n' +
        '          </float_array>\n' +
        '          <technique_common>\n' +
        '            <accessor count="%d" source="#%s-UV-array" stride="2">\n' % (nUvVerts,stuff.name) +
        '              <param type="float" name="S"></param>\n' +
        '              <param type="float" name="T"></param>\n' +
        '            </accessor>\n' +
        '          </technique_common>\n' +
        '        </source>\n')

    # Faces
    
    fp.write(
        '        <vertices id="%s-Vertex">\n' % stuff.name +
        '          <input semantic="POSITION" source="#%s-Position"/>\n' % stuff.name +
        '        </vertices>\n')

    checkFaces(stuff, nVerts, nUvVerts)
    #writePolygons(fp, stuff, config)
    writePolylist(fp, stuff, config)
    
    fp.write(
        '      </mesh>\n' +
        '    </geometry>\n')

    for name,shape in stuff.meshInfo.shapes:
        writeShapeKey(fp, name, shape, stuff, config)
    return
    
    
def writeShapeKey(fp, name, shape, stuff, config):  
    obj = stuff.meshInfo.object
    nVerts = len(obj.coord)    
    
    # Verts
    
    fp.write(
        '    <geometry id="%sMeshMorph_%s" name="%s">\n' % (stuff.name, name, name) +
        '      <mesh>\n' +
        '        <source id="%sMeshMorph_%s-positions">\n' % (stuff.name, name) +
        '          <float_array id="%sMeshMorph_%s-positions-array" count="%d">\n' % (stuff.name, name, 3*nVerts) +
        '           ')

    target = numpy.array(obj.coord)
    for n,dr in shape.items():
        target[n] += numpy.array(dr)
    for co in target:
        loc = rotateLoc(co, config)
        fp.write(" %.4g %.4g %.4g" % tuple(loc))

    fp.write('\n' +
        '          </float_array>\n' +
        '          <technique_common>\n' +
        '            <accessor source="#%sMeshMorph_%s-positions-array" count="%d" stride="3">\n' % (stuff.name, name, nVerts) +
        '              <param name="X" type="float"/>\n' +
        '              <param name="Y" type="float"/>\n' +
        '              <param name="Z" type="float"/>\n' +
        '            </accessor>\n' +
        '          </technique_common>\n' +
        '        </source>\n')

    # Normals
    """
    fp.write(
'        <source id="%sMeshMorph_%s-normals">\n' % (stuff.name, name) +
'          <float_array id="%sMeshMorph_%s-normals-array" count="18">\n' % (stuff.name, name))
-0.9438583 0 0.3303504 0 0.9438583 0.3303504 0.9438583 0 0.3303504 0 -0.9438583 0.3303504 0 0 -1 0 0 1
    fp.write(
        '          </float_array>\n' +
        '          <technique_common>\n' +
        '            <accessor source="#%sMeshMorph_%s-normals-array" count="6" stride="3">\n' % (stuff.name, name) +
        '              <param name="X" type="float"/>\n' +
        '              <param name="Y" type="float"/>\n' +
        '              <param name="Z" type="float"/>\n' +
        '            </accessor>\n' +
        '          </technique_common>\n' +
        '        </source>\n')
    """

    # Polylist

    fp.write(
        '        <vertices id="%sMeshMorph_%s-vertices">\n' % (stuff.name, name) +
        '          <input semantic="POSITION" source="#%sMeshMorph_%s-positions"/>\n' % (stuff.name, name) +
        '        </vertices>\n' +
        '        <polylist count="%d">\n' % len(obj.fvert) +
        '          <input semantic="VERTEX" source="#%sMeshMorph_%s-vertices" offset="0"/>\n' % (stuff.name, name) +
        #'          <input semantic="NORMAL" source="#%sMeshMorph_%s-normals" offset="1"/>\n' % (stuff.name, name) +
        '          <vcount>')

    for fv in obj.fvert:
        if fv[0] == fv[3]:
            fp.write("3 ")
        else:
            fp.write("4 ")
        
    fp.write('\n' +
        '          </vcount>\n' +
        '          <p>')

    for fv in obj.fvert:
        if fv[0] == fv[3]:
            fp.write("%d %d %d " % (fv[0], fv[1], fv[2]))
        else:
            fp.write("%d %d %d %s " % (fv[0], fv[1], fv[2], fv[3]))

    fp.write('\n' +
        '          </p>\n' +
        '        </polylist>\n' +
        '      </mesh>\n' +
        '    </geometry>\n')

    
#
#   writePolygons(fp, stuff, config):
#   writePolylist(fp, stuff, config):
#

def writePolygons(fp, stuff, config):
    obj = stuff.meshInfo.object
    fp.write(        
        '        <polygons count="%d">\n' % len(obj.fvert) +
        '          <input offset="0" semantic="VERTEX" source="#%s-Vertex"/>\n' % stuff.name +
        '          <input offset="1" semantic="NORMAL" source="#%s-Normals"/>\n' % stuff.name +
        '          <input offset="2" semantic="TEXCOORD" source="#%s-UV"/>\n' % stuff.name)

    for fn,fverts in enumerate(obj.fvert):
        fuv = obj.fuvs[fn]
        fp.write('          <p>')
        for n,vn in enumerate(fverts):
            fp.write("%d %d %d " % (vn, vn, fuv[n]))
        fp.write('</p>\n')
    
    fp.write('\n' +
        '        </polygons>\n')
    return

def writePolylist(fp, stuff, config):
    obj = stuff.meshInfo.object
    fp.write(        
        '        <polylist count="%d">\n' % len(obj.fvert) +
        '          <input offset="0" semantic="VERTEX" source="#%s-Vertex"/>\n' % stuff.name)
        
    if config.useNormals:
        fp.write(
        '          <input offset="1" semantic="NORMAL" source="#%s-Normals"/>\n' % stuff.name +
        '          <input offset="2" semantic="TEXCOORD" source="#%s-UV"/>\n' % stuff.name +
        '          <vcount>')
    else:
        fp.write(
        '          <input offset="1" semantic="TEXCOORD" source="#%s-UV"/>\n' % stuff.name +
        '          <vcount>')

    for fv in obj.fvert:
        if fv[0] == fv[3]:
            fp.write('3 ')
        else:
            fp.write('4 ')

    fp.write('\n' +
        '          </vcount>\n'
        '          <p>')

    for fn,fv in enumerate(obj.fvert):
        fuv = obj.fuvs[fn]
        if fv[0] == fv[3]:
            nverts = 3
        else:
            nverts = 4
        if config.useNormals:
            for n in range(nverts):
                fp.write("%d %d %d " % (fv[n], fn, fuv[n]))
        else:
            for n in range(nverts):
                fp.write("%d %d " % (fv[n], fuv[n]))

    fp.write(
        '          </p>\n' +
        '        </polylist>\n')
    return

#
#   checkFaces(stuff, nVerts, nUvVerts):
#

def checkFaces(stuff, nVerts, nUvVerts):
    obj = stuff.meshInfo.object
    for fn,fverts in enumerate(obj.fvert):
        for n,vn in enumerate(fverts):
            uv = obj.fuvs[fn][n]
            if vn > nVerts:
                raise NameError("v %d > %d" % (vn, nVerts))
            if uv > nUvVerts:
                raise NameError("uv %d > %d" % (uv, nUvVerts))            
    return 
    
#
#    writeNode(fp, pad, stuff, config):
#

def writeNode(fp, pad, stuff, config):    
    fp.write('\n' +
        '%s<node id="%sObject" name="%s">\n' % (pad, stuff.name,stuff.name) +
        '%s  <translate sid="translate">0 0 0</translate>\n' % pad +
        '%s  <rotate sid="rotateZ">0 0 1 0</rotate>\n' % pad +
        '%s  <rotate sid="rotateY">0 1 0 0</rotate>\n' % pad +
        '%s  <rotate sid="rotateX">1 0 0 0</rotate>\n' % pad+
        #'%s  <scale sid="scale">1 1 1</scale>\n' % pad+
        '%s  <instance_controller url="#%s-skin">\n' % (pad, stuff.name) +
        '%s    <skeleton>#%s</skeleton>\n' % (pad, stuff.boneInfo.root))

    (texname, texfile, matname) = exportutils.collect.getTextureNames(stuff)    
    if matname:
        matname = matname.replace(" ", "_")    
        fp.write(
            '%s    <bind_material>\n' % pad +
            '%s      <technique_common>\n' % pad +
            '%s        <instance_material symbol="%s" target="#%s">\n' % (pad, matname, matname) +
            '%s          <bind_vertex_input semantic="UVTex" input_semantic="TEXCOORD" input_set="0"/>\n' % pad +
            '%s        </instance_material>\n' % pad +
            '%s      </technique_common>\n' % pad +
            '%s    </bind_material>\n' % pad)

    fp.write(
        '%s  </instance_controller>\n' % pad +
        '%s</node>\n' % pad)
    return


def rotateLoc(loc, config):    
    (x,y,z) = loc
    if config.rotate90X:
        yy = -z
        z = y
        y = yy
    if config.rotate90Z:
        yy = x
        x = -y
        y = yy        
    return (x,y,z)        


def writeBone(fp, bone, orig, extra, pad, stuff, config):
    (name, children) = bone
    if name:
        nameStr = 'sid="%s"' % name
        idStr = 'id="%s" name="%s"' % (name, name)
    else:
        nameStr = ''
        idStr = ''

    head = stuff.boneInfo.heads[name]
    vec = head - orig
    (x,y,z) = rotateLoc(vec, config)

    fp.write('\n'+
        '%s      <node %s %s type="JOINT" %s>\n' % (pad, extra, nameStr, idStr) +
        '%s        <translate sid="translate"> %.4f %.4f %.4f </translate>\n' % (pad,x,y,z) +
        '%s        <rotate sid="rotateZ">0 0 1 0.0</rotate>\n' % pad +
        '%s        <rotate sid="rotateY">0 1 0 0.0</rotate>\n' % pad +
        '%s        <rotate sid="rotateX">1 0 0 0.0</rotate>\n' % pad +
        '%s        <scale sid="scale">1.0 1.0 1.0</scale>' % pad)    

    for child in children:
        writeBone(fp, child, head, '', pad+'  ', stuff, config)    

    fp.write('\n%s      </node>' % pad)
    return
    
            
