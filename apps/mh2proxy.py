#!/usr/bin/python
# -*- coding: utf-8 -*-

""" 
**Project Name:**      MakeHuman

**Product Home Page:** http://www.makehuman.org/

**Code Home Page:**    http://code.google.com/p/makehuman/

**Authors:**           Thomas Larsson

**Copyright(c):**      MakeHuman Team 2001-2013

**Licensing:**         AGPL3 (see also http://www.makehuman.org/node/318)

**Coding Standards:**  See http://www.makehuman.org/node/165

Abstract
--------

TODO
"""

import os
import numpy
import module3d
import exportutils
import log


class CProxyRefVert:

    def __init__(self, parent, scale):
        self._parent = parent        
        self._scale = scale
    

    def fromSingle(self, words, vnum, proxy):
        self._exact = True        
        v0 = int(words[0])
        self._verts = (v0,v0,v0)
        self._weights = (1,0,0)
        self._offset = numpy.array((0,0,0), float)
        self.addProxyVertWeight(proxy, v0, vnum, 1)
        return self

        
    def fromTriple(self, words, vnum, proxy):
        self._exact = False
        v0 = int(words[0])
        v1 = int(words[1])
        v2 = int(words[2])
        w0 = float(words[3])
        w1 = float(words[4])
        w2 = float(words[5])            
        if len(words) > 6:
            d0 = float(words[6])
            d1 = float(words[7])
            d2 = float(words[8])
        else:
            (d0,d1,d2) = (0,0,0)
        
        self._verts = (v0,v1,v2)
        self._weights = (w0,w1,w2)
        self._offset = numpy.array((d0,d1,d2), float)

        self.addProxyVertWeight(proxy, v0, vnum, w0)
        self.addProxyVertWeight(proxy, v1, vnum, w1)
        self.addProxyVertWeight(proxy, v2, vnum, w2)
        return self


    def addProxyVertWeight(self, proxy, v, pv, w):
        try:
            proxy.vertWeights[v].append((pv, w))
        except KeyError:
            proxy.vertWeights[v] = [(pv,w)]
        return

    def getHumanVerts(self):
        return self._verts    

    def getWeights(self):
        return self._weights            

    def getOffset(self):
        return self._offset            

    def getCoord(self):
        rv0,rv1,rv2 = self._verts
        v0 = self._parent.coord[rv0]
        v1 = self._parent.coord[rv1]
        v2 = self._parent.coord[rv2]
        w0,w1,w2 = self._weights
        return (w0*v0 + w1*v1 + w2*v2 + self._scale*self._offset)


#
#    class CProxy
#

class CProxy:
    def __init__(self, file, typ, layer):
        self.name = None
        self.type = typ
        self.file = file
        self.uuid = None
        self.basemesh = "alpha_7"
        self.tags = []
        
        self.vertWeights = {}       # (proxy-vert, weight) list for each parent vert
        self.refVerts = []          
                
        self.xScaleData = None
        self.yScaleData = None
        self.zScaleData = None
        self.z_depth = 50
        self.cull = False
        self.transparent = False
        self.layer = layer
        self.material = CMaterial()
        self.faces = []
        self.texFaces = []
        self.texVerts = []
        self.texFacesLayers = {}
        self.texVertsLayers = {}
        self.useBaseMaterials = False
        self.faceNumbers = []
        self.rig = None
        self.mask = None
        self.texture = None
        self.specular = None
        self.bump = None
        self.normal = None
        self.displacement = None
        self.transparency = None
        self.specularStrength = 1.0
        self.bumpStrength = 1.0
        self.normalStrength = 1.0
        self.dispStrength = 0.2
        self.obj_file = None
        self.material_file = None
        self.maskLayer = -1
        self.textureLayer = 0
        self.objFileLayer = 0
        self.uvtexLayerName = {0 : "UVTex"}
        self.materials = []
        self.constraints = []
        self.neighbors = {}
        self.deleteGroups = []
        self.deleteVerts = None
        self.wire = False
        self.cage = False
        self.modifiers = []
        self.shapekeys = []
        self.weights = None
        self.clothings = []
        self.transparencies = dict()
        self.textures = []
        return
        
    def __repr__(self):
        return ("<CProxy %s %s %s %s>" % (self.name, self.type, self.file, self.uuid))
        
    def update(self, obj):
        coords = [refVert.getCoord() for refVert in self.refVerts]
        obj.changeCoords(coords)      
        
    def getUuid(self):
        if self.uuid:
            return self.uuid
        else:
            return self.name        

#
#    classes CMaterial, CTexture
#

class CTexture:
    def __init__(self, fname):
        self.file = fname
        self.types = []

        
class CMaterial:
    def __init__(self):
        self.name = None
        self.settings = []
        self.textureSettings = []
        self.mtexSettings = []

        self.diffuse_color = (0.8,0.8,0.8)
        self.diffuse_intensity = 0.8
        self.specular_color = (1,1,1)
        self.specular_intensity = 0.1
        self.specular_hardness = 25
        self.transparency = 1
        self.translucency = 0.0
        self.ambient_color = (0,0,0)
        self.emit_color = (0,0,0)
        self.use_transparency = False
        self.alpha = 1
        
        self.textures = []
 
                
#
#   class CMeshInfo:
#

class CMeshInfo:

    def __init__(self, name):
        self.name = name
        self.object = None
        self.weights = {}
        self.shapes = []
        self.vertexMask = None
        self.faceMask = None
        self.vertexMapping = None   # Maps vertex index of original object to the attached filtered object 


    def fromProxy(self, coords, texVerts, faceVerts, faceUvs, weights, shapes):
        obj = self.object = module3d.Object3D(self.name)
        obj.setCoords(coords)
        obj.setUVs(texVerts)
        
        for fv in faceVerts:
            if len(fv) != 4:
                raise NameError("Mesh %s has non-quad faces and can not be handled by MakeHuman" % self.name)

        obj.createFaceGroup("Full Object")
        obj.setFaces(faceVerts, faceUvs)
        self.weights = weights
        self.shapes = shapes
        return self


    def fromObject(self, object3d, weights, shapes):
        self.object = object3d
        self.name = object3d.name
        self.weights = weights
        self.shapes = shapes
        return self
        
        
    def __repr__(self):
        return ("<CMeshInfo %s w %d t %d>" % (self.object, len(self.weights), len(self.shapes)))       
        

def getFileName(folder, file, suffix):
    folder = os.path.realpath(os.path.expanduser(folder))
    (name, ext) = os.path.split(file)
    if ext:
        return (folder, file)
    else:
        return (folder, file+suffix)

#
#    readProxyFile(obj, file, evalOnLoad=False, scale=1.0):
#

doFaces = 2
doMaterial = 3
doTexVerts = 4
doObjData = 5
doWeights = 6
doRefVerts = 7
doFaceNumbers = 8
doTexFaces = 9    
doDeleteVerts = 10

def readProxyFile(obj, file, evalOnLoad=False, scale=1.0):
    if not file:
        return CProxy(None, 'Proxy', 2)
    elif isinstance(file, basestring):
        pfile = exportutils.config.CProxyFile()
        pfile.file = file
    else:
        pfile = file
    #print "Loading", pfile
    folder = os.path.dirname(pfile.file)
    objfile = None
    
    try:
        tmpl = open(pfile.file, "rU")
    except:
        tmpl = None
    if tmpl == None:
        log.error("*** Cannot open %s", pfile.file)
        return None
        return CProxy(None, proxy.type, pfile.layer)

    locations = {}
    tails = {}
    proxy = CProxy(pfile.file, pfile.type, pfile.layer)
    proxy.deleteVerts = numpy.zeros(len(obj.coord), bool)
    proxy.name = "MyProxy"

    useProjection = True
    ignoreOffset = False
    scales = numpy.array((1.0,1.0,1.0), float)
    status = 0
    vnum = 0
    for line in tmpl:
        words= line.split()
        if len(words) == 0:
            pass

        elif words[0] == '#':        
            theGroup = None
            if len(words) == 1:
                continue
            key = words[1]
            if key == 'verts':
                status = doRefVerts
            elif key == 'faces':
                status = doFaces
            elif key == 'weights':
                status = doWeights
                if proxy.weights == None:
                    proxy.weights = {}
                weights = []
                proxy.weights[words[2]] = weights
            elif key == 'material':
                status = doMaterial
                proxy.material.name = " ".join(words[2:])
            elif key == 'useBaseMaterials':
                proxy.useBaseMaterials = True
            elif key == 'faceNumbers':
                status = doFaceNumbers
            elif key == 'texVerts':
                status = doTexVerts
                if len(words) > 2:
                    layer = int(words[2])
                else:
                    layer = 0
                proxy.texVerts = []
                proxy.texVertsLayers[layer] = proxy.texVerts
            elif key == 'texFaces':
                status = doTexFaces
                if len(words) > 2:
                    layer = int(words[2])
                else:
                    layer = 0
                proxy.texFaces = []
                proxy.texFacesLayers[layer] = proxy.texFaces
            elif key == 'name':
                proxy.name = " ".join(words[2:])
            elif key == 'uuid':
                proxy.uuid = " ".join(words[2:])
            elif key == 'tag':
                proxy.tags.append( " ".join(words[2:]) )
            elif key == 'z_depth':
                proxy.z_depth = int(words[2])
            elif key == 'wire':
                proxy.wire = True
            elif key == 'cage':
                proxy.cage = True
            elif key == 'x_scale':
                proxy.xScaleData = getScaleData(words)
                scales[0] = getScale(proxy.xScaleData, obj, 0)
            elif key == 'y_scale':
                proxy.yScaleData = getScaleData(words)
                scales[1] = getScale(proxy.yScaleData, obj, 1)
            elif key == 'z_scale':
                proxy.zScaleData = getScaleData(words)
                scales[2] = getScale(proxy.zScaleData, obj, 2)
            elif key == 'use_projection':
                useProjection = int(words[2])
            elif key == 'ignoreOffset':
                ignoreOffset = int(words[2])
            elif key == 'delete':
                proxy.deleteGroups.append(words[2])
            elif key == 'delete_connected':
                selectConnected(proxy, obj, int(words[2]))
            elif key == "delete_verts":
                status = doDeleteVerts
            elif key == 'rig':
                proxy.rig = getFileName(folder, words[2], ".rig")
            elif key == 'mask':
                proxy.mask = getFileName(folder, words[2], ".png")
                if len(words) > 3:
                    proxy.maskLayer = int(words[3])
            elif key == 'specular':
                proxy.specular = getFileName(folder, words[2], ".png")
                if len(words) > 4:
                    proxy.specularStrength = float(words[4])
            elif key == 'bump':
                proxy.bump = getFileName(folder, words[2], ".png")
                if len(words) > 4:
                    proxy.bumpStrength = float(words[4])
            elif key == 'normal':
                proxy.normal = getFileName(folder, words[2], ".png")
                if len(words) > 4:
                    proxy.normalStrength = float(words[4])
            elif key == 'transparency':
                proxy.transparency = getFileName(folder, words[2], ".png")
            elif key == 'displacement':
                proxy.displacement = getFileName(folder, words[2], ".png")
                if len(words) > 4:
                    proxy.dispStrength = float(words[4])
            elif key == 'texture':
                proxy.texture = getFileName(folder, words[2], ".png")
                if len(words) > 3:
                    proxy.textureLayer = int(words[3])
            elif key == 'objfile_layer':
                proxy.objFileLayer = int(words[2])
            elif key == 'uvtex_layer':
                proxy.uvtexLayerName[int(words[2])] = words[3]
            elif key == 'material_file':
                pass
                #proxy.material_file = getFileName(folder, words[2], ".mhx")
            elif key == 'obj_file':
                proxy.obj_file = getFileName(folder, words[2], ".obj")
            elif key == 'backface_culling':
                proxy.cull = words[2].lower() in ["1", "yes", "true", "enable", "enabled"]
            elif key == 'transparent':
                proxy.transparent = words[2].lower() in ["1", "yes", "true", "enable", "enabled"]
            elif key == 'clothing':
                if len(words) > 3:
                    clothingPiece = (words[2], words[3])
                else:
                    clothingPiece = (words[2], None)
                proxy.clothings.append(clothingPiece)
            elif key == 'transparencies':
                uuid = words[2]
                proxy.transparencies[uuid] = words[3].lower() in ["1", "yes", "true", "enable", "enabled"]
            elif key == 'textures':
                proxy.textures.append( (words[2], words[3]) )
            elif key == 'subsurf':
                levels = int(words[2])
                if len(words) > 3:
                    render = int(words[3])
                else:
                    render = levels+1
                proxy.modifiers.append( ['subsurf', levels, render] )
            elif key == 'shrinkwrap':
                offset = float(words[2])
                proxy.modifiers.append( ['shrinkwrap', offset] )
            elif key == 'solidify':
                thickness = float(words[2])
                offset = float(words[3])
                proxy.modifiers.append( ['solidify', thickness, offset] )
            elif key == 'shapekey':
                proxy.shapekeys.append( words[2] )
            elif key == 'basemesh':
                proxy.basemesh = words[2]
            else:
                pass
                #print "Ignored proxy keyword", key

        elif status == doObjData:
            if words[0] == 'vt':
                newTexVert(1, words, proxy)
            elif words[0] == 'f':
                newFace(1, words, theGroup, proxy)
            elif words[0] == 'g':
                theGroup = words[1]

        elif status == doFaceNumbers:
            proxy.faceNumbers.append(line)

        elif status == doRefVerts:
            refVert = CProxyRefVert(obj, scales)
            proxy.refVerts.append(refVert)
            if len(words) == 1:
                refVert.fromSingle(words, vnum, proxy)
            else:                
                refVert.fromTriple(words, vnum, proxy)
            vnum += 1

        elif status == doFaces:
            newFace(0, words, theGroup, proxy)

        elif status == doTexVerts:
            newTexVert(0, words, proxy)

        elif status == doTexFaces:
            newTexFace(words, proxy)

        elif status == doMaterial:
            readMaterial(line, proxy.material, proxy, False)

        elif status == doWeights:
            v = int(words[0])
            w = float(words[1])
            weights.append((v,w))

        elif status == doDeleteVerts:
            sequence = False
            for v in words:            
                if v == "-":
                    sequence = True
                else:
                    v1 = int(v)
                    if sequence:
                        for vn in range(v0,v1+1):
                            proxy.deleteVerts[vn] = True
                        sequence = False                            
                    else:
                        proxy.deleteVerts[v1] = True
                    v0 = v1
                        
            
    if evalOnLoad and proxy.obj_file:
        if not copyObjFile(proxy):
            return None
    return proxy

#
#   selectConnected(proxy, obj, vn):
#
    
def selectConnected(proxy, obj, vn):
    if not proxy.neighbors:
        for n in range(nVerts):    
            proxy.neighbors[n] = []
        for fv in obj.fvert:
            for vn1 in fv:
                for vn2 in fv:
                    if vn1 != vn2:
                        proxy.neighbors[vn1].append(vn2)
                    
        #for f in obj.faces:
        #    for v1 in f.verts:            
        #        for v2 in f.verts:
        #            if v1 != v2:
        #                proxy.neighbors[v1.idx].append(v2.idx)
    walkTree(proxy, vn)
    return
    
    
def walkTree(proxy, vn):    
    proxy.deleteVerts[vn] = True
    for vk in proxy.neighbors[vn]:
        if not proxy.deleteVerts[vk]:
            walkTree(proxy, vk)
    return            


def deleteGroup(name, groups):
    for part in groups:
        if part in name:
            return True
    return False
       

def copyObjFile(proxy):
    (folder, name) = proxy.obj_file
    objpath = os.path.join(folder, name)
    try:
        tmpl = open(objpath, "rU")
    except:
        log.error("*** Cannot open %s", objpath)
        return False

    proxy.texVerts = []
    proxy.texFaces = []
    layer = proxy.objFileLayer
    proxy.texVertsLayers[layer] = proxy.texVerts
    proxy.texFacesLayers[layer] = proxy.texFaces
    theGroup = None    
    for line in tmpl:
        words= line.split()        
        if len(words) == 0:
            pass
        elif words[0] == 'vt':
            newTexVert(1, words, proxy)
        elif words[0] == 'f':
            newFace(1, words, theGroup, proxy)
        elif words[0] == 'g':
            theGroup = words[1]
    tmpl.close()            
    return True            
    

def getScaleData(words):
    v1 = int(words[2])
    v2 = int(words[3])
    den = float(words[4])
    return (v1, v2, den)

    
def getScale(data, obj, index):
    if not data:
        return 1.0
    (vn1, vn2, den) = data
    num = abs(obj.coord[vn1][index] - obj.coord[vn2][index])
    return num/den


def readMaterial(line, mat, proxy, multiTex):
    words= line.split()
    key = words[0]
    if key in ['diffuse_color', 'specular_color', 'ambient', 'emit']:
        mat.settings.append( (key, [float(words[1]), float(words[2]), float(words[3])]) )
    elif key in ['diffuse_shader', 'specular_shader']:
        mat.settings.append( (key, words[1]) )
    elif key in ['use_shadows', 'use_transparent_shadows', 'use_transparency', 'use_raytrace']:
        mat.settings.append( (key, int(words[1])) )
    elif key in ['diffuse_intensity', 'specular_intensity', 'specular_hardness', 'translucency', 
        'alpha', 'specular_alpha']:
        mat.settings.append( (key, float(words[1])) )
    elif key in ['diffuse_color_factor', 'alpha_factor', 'translucency_factor']:
        mat.mtexSettings.append( (key, float(words[1])) )
    elif key in ['use_map_color_diffuse', 'use_map_alpha']:
        mat.mtexSettings.append( (key, int(words[1])) )
    elif key in ['use_alpha']:
        mat.textureSettings.append( (key, int(words[1])) )
    elif key == 'texture':
        fname = os.path.realpath(os.path.expanduser(words[1]))
        if multiTex:
            tex = CTexture(fname)
            nmax = len(words)
            n = 2
            while n < nmax:
                tex.types.append((words[n], words[n+1]))
                n += 2
            mat.textures.append(tex)
        else:
            proxy.texture = os.path.split(fname)
    else:
        raise NameError("Material %s?" % key)
    if key == 'alpha':
        mat.alpha = float(words[1])
        mat.use_transparency = True


class CUvSet:
    def __init__(self, name):
        self.name = name
        self.type = "UvSet"
        self.filename = None
        self.faceMaterials = None
        self.materials = []
        self.faceNumbers = []
        self.texVerts = []
        self.texFaces = []


    def read(self, human, filename):
        try:
            fp = open(filename, "r")
        except:
            raise NameError("Cannot open %s" % filename)
                
        status = 0
        for line in fp:
            words = line.split()
            if words == []:
                continue
            elif words[0] == '#':
                if words[1] == "name":
                    self.name = words[2]
                elif words[1] == "material":
                    mat = CMaterial()
                    mat.name = words[2]
                    self.materials.append(mat)
                    status = doMaterial
                elif words[1] == "faceNumbers":
                    status = doFaceNumbers
                elif words[1] == "texVerts":
                    status = doTexVerts
                elif words[1] == "texFaces":
                    status = doTexFaces
            elif status == doMaterial:
                readMaterial(line, mat, self, True)
            elif status == doFaceNumbers:
                self.faceNumbers.append(line)
            elif status == doTexVerts:
                self.texVerts.append([float(words[0]), float(words[1])])
            elif status == doTexFaces:
                newTexFace(words, self)
        fp.close()   
        self.filename = filename
            
        nFaces = len(human.meshData.fvert)                
        self.faceMaterials = numpy.zeros(nFaces, int)
        fn = 0
        for line in self.faceNumbers:
            words = line.split()
            if len(words) < 2:
                log.debug(line)
                halt
            elif words[0] == "ft":        
                self.faceMaterials[fn] = int(words[1])
                fn += 1
            elif words[0] == "ftn":
                nfaces = int(words[1])
                mn = int(words[2])
                for n in range(nfaces):
                    self.faceMaterials[fn] = mn
                    fn += 1
        while fn < nFaces:
            self.faceMaterials[fn] = mn
            fn += 1


def getJoint(joint, obj, locations):
    try:
        loc = locations[joint]
    except KeyError:
        loc = locations[joint] = calcJointPos(obj, joint)
    return loc
    

def calcJointPos(obj, joint):
    verts = obj.getVerticesForGroups(["joint-"+joint])
    coords = obj.coord[verts]
    return coords.mean(axis=0)
    return numpy.array(coords).mean(axis=0)
    
    #g = obj.getFaceGroup("joint-"+joint)
    #coords = []
    #for f in g.faces:
    #    for v in f.verts:
    #        coords.append(v.co)
    #return numpy.array(coords).mean(axis=0)
    

def newFace(first, words, group, proxy):
    face = []
    texface = []
    nCorners = len(words)
    for n in range(first, nCorners):
        numbers = words[n].split('/')
        face.append(int(numbers[0])-1)
        if len(numbers) > 1:
            texface.append(int(numbers[1])-1)
    proxy.faces.append((face,group))
    if texface:
        proxy.texFaces.append(texface)
        if len(face) != len(texface):
            raise NameError("texface %s %s", face, texface)
    return


def newTexFace(words, proxy):
    texface = [int(word) for word in words]
    proxy.texFaces.append(texface)


def newTexVert(first, words, proxy):
    vt = [float(word) for word in words[first:]]
    proxy.texVerts.append(vt)


def getMeshInfo(obj, proxy, config, rawWeights, rawShapes, rigname):
    if proxy:
        coords = [config.scale*refVert.getCoord() for refVert in proxy.refVerts]
        faceVerts = [[v for v in f] for (f,g) in proxy.faces]
        
        if proxy.texVerts:
            texVerts = proxy.texVertsLayers[proxy.objFileLayer]
            texFaces = proxy.texFacesLayers[proxy.objFileLayer]        
            fnmax = len(texFaces)
            faceVerts = faceVerts[:fnmax]
        else:
            texVerts = []
            texFaces = []

        weights = getProxyWeights(rawWeights, proxy)
        shapes = getProxyShapes(rawShapes, proxy, config.scale)
        meshInfo = CMeshInfo(proxy.name).fromProxy(coords, texVerts, faceVerts, texFaces, weights, shapes)

    else:
        meshInfo = CMeshInfo(obj.name).fromObject(obj, rawWeights, rawShapes)
    return meshInfo
        
        
def getProxyWeights(rawWeights, proxy):
    if not rawWeights:
        return {}
    weights = {}
    for key in rawWeights.keys():
        vgroup = []
        empty = True
        for (v,wt) in rawWeights[key]:
            try:
                vlist = proxy.vertWeights[v]
            except KeyError:
                vlist = []
            for (pv, w) in vlist:
                pw = w*wt
                if (pw > 1e-4):
                    vgroup.append((pv, pw))
                    empty = False
        if not empty:
            weights[key] = fixProxyVGroup(vgroup)
    return weights


def fixProxyVGroup(vgroup):
    fixedVGroup = []
    vgroup.sort()
    pv = -1
    while vgroup:
        (pv0, wt0) = vgroup.pop()
        if pv0 == pv:
            wt += wt0
        else:
            if pv >= 0 and wt > 1e-4:
                fixedVGroup.append((pv, wt))
            (pv, wt) = (pv0, wt0)
    if pv >= 0 and wt > 1e-4:
        fixedVGroup.append((pv, wt))
    return fixedVGroup


def getProxyShapes(rawShapes, proxy, scale):
    if (not rawShapes) or (proxy.type not in ['Proxy', 'Clothes']):
        return []
    shapes = []
    for (key, rawShape) in rawShapes:
        shape = []
        for (v,dr) in rawShape.items():    
            (dx,dy,dz) = dr
            try:
                vlist = proxy.vertWeights[v]
            except KeyError:
                vlist = []
            for (pv, w) in vlist:
                shape.append((pv, scale*w*dx, scale*w*dy, scale*w*dz))
        if shape != []:
            fixedShape = fixProxyShape(shape)
            shapes.append((key,fixedShape))
    return shapes


def fixProxyShape(shape):
    fixedShape = {}
    shape.sort()
    pv = -1
    #while shape:
    #    (pv0, dx0, dy0, dz0) = shape.pop()
    for (pv0, dx0, dy0, dz0) in shape:
        if pv0 == pv:
            dx += dx0
            dy += dy0
            dz += dz0
        else:
            if pv >= 0 and (dx*dx + dy*dy + dz*dz) > 1e-8:
                fixedShape[pv] = (dx, dy, dz)
            (pv, dx, dy, dz) = (pv0, dx0, dy0, dz0)        
    if pv >= 0 and (dx*dx + dy*dy + dz*dz) > 1e-8:
        fixedShape[pv] = (dx, dy, dz)
    return fixedShape
    
