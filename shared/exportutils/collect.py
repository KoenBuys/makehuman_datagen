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
MakeHuman to Collada (MakeHuman eXchange format) exporter. Collada files can be loaded into
Blender by collada_import.py.

TODO
"""

import module3d
import mh
import files3d
import os
import time
import numpy
import shutil

import export
import mh2proxy
import log
import catmull_clark_subdivision as cks
import subtextures

from .config import Config
from . import rig as rigfile

#
#    class CStuff
#

class CStuff:
    def __init__(self, name, proxy = None, obj = None):
        self.name = os.path.basename(name)
        self.proxy = proxy
        self.object = obj
        self.meshInfo = None
        self.boneInfo = None
        self.vertexWeights = None
        self.skinWeights = None
        self.textureImage = None
        if proxy:
            self.type = proxy.type
            self.material = proxy.material
            self.texture = proxy.texture
            self.specular = proxy.specular
            self.normal = proxy.normal
            self.transparency = proxy.transparency
            self.bump = proxy.bump
            self.displacement = proxy.displacement
        else:                    
            if obj:
                self.texture = obj.mesh.texture
            else:
                self.texture = None
            self.type = None
            self.material = None
            self.specular = ("data/textures", "texture_ref.png") 
            self.normal = None
            self.transparency = None
            self.bump = ("data/textures", "bump.png")
            self.displacement = None

    #def setObject3dMesh(self, object3d, weights, shapes):
    #    self.meshInfo.setObject3dMesh(object3d, weights, shapes)
        
    def __repr__(self):
        return "<CStuff %s %s mat %s tex %s>" % (self.name, self.type, self.material, self.texture)

    def hasMaterial(self):
        return (
            self.material != None or
            self.texture != None or
            self.specular != None or
            self.normal != None or
            self.transparency != None or
            self.bump != None or
            self.displacement != None)
    

class CBoneInfo:
    def __init__(self, root, heads, tails, rolls, hier, bones, weights):
        self.root = root
        self.heads = heads
        self.tails = tails
        self.rolls = rolls
        self.hier = hier
        self.bones = bones
        self.weights = weights
        
    def __repr__(self):
        return ("<CBoneInfo r %s h %d t %s r %d\n   h %s\n   b %s\n   w %s" % 
            (self.root, len(self.heads), len(self.tails), len(self.rolls), 
             self.hier, self.bones, self.weights))
       

#
#   readTargets(config):
#

from .shapekeys import readExpressionUnits
from .custom import listCustomFiles, readCustomTarget

def readTargets(human, config):
    targets = []
    if config.expressions:
        shapeList = readExpressionUnits(human, 0, 1)
        targets += shapeList

    if config.useCustomShapes:
        listCustomFiles(config)                            

        log.message("Custom shapes:")    
        for path,name in config.customShapeFiles:
            log.message("    %s", path)
            shape = readCustomTarget(path)
            targets.append((name,shape))

    return targets            

#
#   setupObjects
#

def setupObjects(name, human, config=None, rigfile=None, rawTargets=[], helpers=False, hidden=False, eyebrows=True, lashes=True, subdivide = False, progressCallback=None):
    global theStuff, theTextures, theTexFiles, theMaterials

    def progress(prog):
        if progressCallback == None:
            pass
        else:
            progressCallback (prog)

    if not config:
        config = Config()
        config.setHuman(human)
        
    obj = human.meshData
    theTextures = {}
    theTexFiles = {}
    theMaterials = {}
    
    stuffs = []
    stuff = CStuff(name, obj = human)

    if rigfile:
        stuff.boneInfo = getArmatureFromRigFile(rigfile, obj, config.scale)
        log.message("Using rig file %s" % rigfile)
            
    meshInfo = mh2proxy.getMeshInfo(obj, None, config, None, rawTargets, None)
    if stuff.boneInfo:
        meshInfo.weights = stuff.boneInfo.weights

    theStuff = stuff
    deleteGroups = []
    deleteVerts = None  # Don't load deleteVerts from proxies directly, we use the facemask set in the gui module3d
    _,deleteVerts = setupProxies('Clothes', None, obj, stuffs, meshInfo, config, deleteGroups, deleteVerts)
    _,deleteVerts = setupProxies('Hair', None, obj, stuffs, meshInfo, config, deleteGroups, deleteVerts)
    foundProxy,deleteVerts = setupProxies('Proxy', name, obj, stuffs, meshInfo, config, deleteGroups, deleteVerts)
    progress(0.06*(3-2*subdivide))
    if not foundProxy:
        if helpers:     # helpers override everything
            if config.scale == 1.0:
                stuff.meshInfo = meshInfo
            else:
                stuff.meshInfo = meshInfo.fromProxy(config.scale*obj.coord, obj.texco, obj.fvert, obj.fuvs, meshInfo.weights, meshInfo.shapes)
        else:
            stuff.meshInfo = filterMesh(meshInfo, config.scale, deleteGroups, deleteVerts, eyebrows, lashes, not hidden)
        stuffs = [stuff] + stuffs
    progbase = 0.12*(3-2*subdivide)
    progress(progbase)

    # Apply textures, and subdivide, if requested.
    stuffnum = float(len(stuffs))
    i = 0.0
    for stuff in stuffs:
        progress(progbase+(i/stuffnum)*(1-progbase))
        texture = stuff.object.mesh.texture
        stuff.texture = (os.path.dirname(texture), os.path.basename(texture))
        if subdivide:
            subMesh = cks.createSubdivisionObject(
                stuff.meshInfo.object, lambda p: progress(progbase+((i+p)/stuffnum)*(1-progbase)))
            stuff.meshInfo.fromObject(subMesh, stuff.meshInfo.weights, rawTargets)
        i += 1.0

    # Apply subtextures.
    stuffs[0].textureImage = mh.Image(os.path.join(stuffs[0].texture[0], stuffs[0].texture[1]))
    mhstx = mh.G.app.getCategory('Textures').getTaskByName('Texture').eyeTexture
    if mhstx:
        stuffs[0].textureImage = subtextures.combine(stuffs[0].textureImage, mhstx)
    
    progress(1)
    return stuffs

#
#    setupProxies(typename, name, obj, stuffs, meshInfo, config, deleteGroups, deleteVerts):
#

def setupProxies(typename, name, obj, stuffs, meshInfo, config, deleteGroups, deleteVerts):
    # TODO document that this method does not only return values, it also modifies some of the passed parameters (deleteGroups and stuffs, deleteVerts is modified only if it is not None)
    global theStuff
    
    foundProxy = False    
    for pfile in config.getProxyList():
        if pfile.type == typename and pfile.file:
            proxy = mh2proxy.readProxyFile(obj, pfile, evalOnLoad=True, scale=config.scale)
            if proxy and proxy.name and proxy.texVerts:
                foundProxy = True
                deleteGroups += proxy.deleteGroups
                if deleteVerts != None:
                    deleteVerts = deleteVerts | proxy.deleteVerts
                if name:
                    stuff = CStuff(name, proxy, pfile.obj)
                else:
                    stuff = CStuff(proxy.name, proxy, pfile.obj)
                stuff.boneInfo = theStuff.boneInfo
                if stuff:
                    if pfile.type == 'Proxy':
                        theStuff = stuff
                    if theStuff:
                        stuffname = theStuff.name
                    else:
                        stuffname = None

                    stuff.meshInfo = mh2proxy.getMeshInfo(obj, proxy, config, meshInfo.weights, meshInfo.shapes, stuffname)

                    stuffs.append(stuff)
    return foundProxy, deleteVerts

#
#
#

def filterMesh(meshInfo, scale, deleteGroups, deleteVerts, eyebrows, lashes, useFaceMask = False):
    """
    Filter out vertices and faces from the mesh that are not desired for exporting.
    """
    # TODO scaling does not belong in a filter method
    obj = meshInfo.object

    killUvs = numpy.zeros(len(obj.texco), bool)
    killFaces = numpy.zeros(len(obj.fvert), bool)
        
    if deleteVerts is not None:
        killVerts = deleteVerts
        for fn,fverts in enumerate(obj.fvert):
            for vn in fverts:
                if killVerts[vn]:
                    killFaces[fn] = True             
    else:
        killVerts = numpy.zeros(len(obj.coord), bool)

    killGroups = []        
    for fg in obj.faceGroups:
        if (("joint" in fg.name) or 
           ("helper" in fg.name) or
           ((not eyebrows) and 
           (("eyebrown" in fg.name) or ("cornea" in fg.name))) or
           ((not lashes) and 
           ("lash" in fg.name)) or
           mh2proxy.deleteGroup(fg.name, deleteGroups)):
            killGroups.append(fg.name)

    faceMask = obj.getFaceMaskForGroups(killGroups)
    if useFaceMask:
        # Apply the facemask set on the module3d object (the one used for rendering within MH)
        faceMask = numpy.logical_or(faceMask, numpy.logical_not(obj.getFaceMask()))
    killFaces[faceMask] = True

    #verts = obj.fvert[faceMask]
    verts = obj.fvert[numpy.logical_not(faceMask)]
    vertMask = numpy.ones(len(obj.coord), bool)
    vertMask[verts] = False
    verts = numpy.argwhere(vertMask)
    del vertMask
    killVerts[verts] = True

    #uvs = obj.fuvs[faceMask]
    uvs = obj.fuvs[numpy.logical_not(faceMask)]
    uvMask = numpy.ones(len(obj.texco), bool)
    uvMask[uvs] = False
    uvs = numpy.argwhere(uvMask)
    del uvMask
    killUvs[uvs] = True
    
    n = 0
    newVerts = {}
    coords = []
    for m,co in enumerate(obj.coord):
        if not killVerts[m]:
            coords.append(scale*co)
            newVerts[m] = n
            n += 1
    
    n = 0
    texVerts = []
    newUvs = {}
    for m,uv in enumerate(obj.texco):
        if not killUvs[m]:
            texVerts.append(uv)
            newUvs[m] = n
            n += 1   
    
    faceVerts = []
    faceUvs = []
    for fn,fverts in enumerate(obj.fvert):
        if not killFaces[fn]:
            fverts2 = []
            fuvs2 = []
            for vn in fverts:
                fverts2.append(newVerts[vn])
            for uv in obj.fuvs[fn]:
                fuvs2.append(newUvs[uv])
            faceVerts.append(fverts2)
            faceUvs.append(fuvs2)
    
    weights = {}
    if meshInfo.weights:
        for (b, wts1) in meshInfo.weights.items():
            wts2 = []
            for (v1,w) in wts1:
                if not killVerts[v1]:
                   wts2.append((newVerts[v1],w))
            weights[b] = wts2
    
    shapes = []
    if meshInfo.shapes:
        for (name, morphs1) in meshInfo.shapes:
            morphs2 = {}
            for (v1,dx) in morphs1.items():
                if not killVerts[v1]:
                    morphs2[newVerts[v1]] = scale*dx
            shapes.append((name, morphs2))

    meshInfo.fromProxy(coords, texVerts, faceVerts, faceUvs, weights, shapes)
    meshInfo.vertexMask = numpy.logical_not(killVerts)
    meshInfo.vertexMapping = newVerts
    meshInfo.faceMask = numpy.logical_not(faceMask)
    return meshInfo
 
#
#   getTextureNames(stuff):
#

def getTextureNames(stuff):
    global theTextures, theTexFiles, theMaterials

    if not stuff.type:
        return ("SkinShader", None, "SkinShader")
        
    try:
        texname = theTextures[stuff.name]
        texfile = theTexFiles[stuff.name]
        matname = theMaterials[stuff.name]
        return (texname, texfile, matname)
    except KeyError:
        pass
    
    texname = None
    texfile = None
    matname = None
    if stuff.texture:        
        (folder, fname) = stuff.texture
        (texname, ext) = os.path.splitext(fname)
        texfile = ("%s_%s" % (texname, ext[1:]))
        while texname in theTextures.values():
            texname = nextName(texname)
        theTextures[stuff.name] = texname
        theTexFiles[stuff.name] = texfile
    if stuff.material:
        matname = stuff.material.name
        while matname in theMaterials.values():
            matname = nextName(matname)
        theMaterials[stuff.name] = matname
    return (texname, texfile, matname)
    
    
def nextName(string):
    try:
        n = int(string[-3:])
    except:
        n = -1
    if n >= 0:
        return "%s%03d" % (string[:-3], n+1)
    else:
        return string + "_001"
        
#
#    getArmatureFromRigFile(fileName, obj, scale):    
#

def getArmatureFromRigFile(fileName, obj, scale):
    (locations, armature, weights) = rigfile.readRigFile(fileName, obj)
    
    hier = []
    heads = {}
    tails = {}
    rolls = {}
    root = None
    for (bone, head, tail, roll, parent, options) in armature:
        heads[bone] = head*scale
        tails[bone] = tail*scale
        rolls[bone] = roll
        if parent == '-':
            hier.append((bone, []))
            if root is None:
                root = bone
        else:
            parHier = findInHierarchy(parent, hier)
            try:
                (p, children) = parHier
            except:
                raise NameError("Did not find %s parent %s" % (bone, parent))
            children.append((bone, []))
    
    if root is None:
        raise NameError("No root bone found in rig file %s" % fileName)
    bones = []
    flatten(hier, bones)
    return CBoneInfo(root, heads, tails, rolls, hier, bones, weights)


def findInHierarchy(bone, hier):
    if hier == []:
        return []
    for pair in hier:
        (b, children) = pair
        if b == bone:
            return pair
        else:
            b = findInHierarchy(bone, children)
            if b: return b
    return []


def flatten(hier, bones):
    for (bone, children) in hier:
        bones.append(bone)
        flatten(children, bones)
    return

#
#   setStuffSkinWeights(stuff):
#

def setStuffSkinWeights(stuff):
    obj = stuff.meshInfo.object
    
    stuff.vertexWeights = {}
    for vn in range(len(obj.coord)):
        stuff.vertexWeights[vn] = []

    stuff.skinWeights = []
    wn = 0    
    for (bn,b) in enumerate(stuff.boneInfo.bones):
        try:
            wts = stuff.meshInfo.weights[b]
        except KeyError:
            wts = []
        for (vn,w) in wts:
            stuff.vertexWeights[int(vn)].append((bn,wn))
            wn += 1
        stuff.skinWeights.extend(wts)
    return

def getpath(path):
    if isinstance(path, tuple):
        (folder, file) = path
        path = os.path.join(folder, file)
    if path:
        return os.path.realpath(os.path.expanduser(path))
    else:
        return None
            
def copy(frompath, topath):
    frompath = getpath(frompath)
    if frompath:
        try:
            shutil.copy(frompath, topath)
        except (IOError, os.error), why:
            log.error("Can't copy %s" % str(why))

