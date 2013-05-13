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
import mh
import shutil
import log

#
#   class Config
#

class Config:

    def __init__(self):
        self.encoding           = 'utf-8'
        self.useTexFolder       = True
        self.eyebrows           = True
        self.lashes             = True
        self.helpers            = False
        self.scale,self.unit    = 1.0, "decimeter"

        self.useNormals         = False
        self.useRelPaths        = True
        self.feetOnGround       = False
        self.skirtRig           = "inh"
        self.rigtype            = None
        self.facepanel          = False
        self.cage               = False
        self.texFolder          = None
        self.customPrefix       = ""
        self.human              = None


    def selectedOptions(self, exporter):
        self.encoding           = exporter.taskview.getEncoding()
        self.useTexFolder       = exporter.useTexFolder.selected
        self.eyebrows           = exporter.eyebrows.selected
        self.lashes             = exporter.lashes.selected
        self.helpers            = exporter.helpers.selected
        self.scale,self.unit    = exporter.taskview.getScale()
        
        return self


    @property
    def subdivide(self):
        if not self.human:
            log.warning('No human set in config, disabled subdivision for export.')
            return False
        else:
            return self.human.isSubdivided()
    

    def setHuman(self, human):
        """
        Set the human object for this config.
        """
        self.human = human
    
    
    def getProxyList(self):
        """
        Get the proxy list from the current state of the set human object.
        Proxy list will contain all proxy items such as proxy mesh and clothes,
        hair and cages.
        """
        proxyList = []
        if not self.human:
            return proxyList

        if self.human.hairProxy:
            words = self.human.hairObj.mesh.name.split('.')
            pfile = CProxyFile()
            pfile.set('Hair', 2)
            pfile.obj = self.human.hairObj
            name = self.goodName(words[0])
            pfile.file = self.human.hairProxy.file
            proxyList.append(pfile)
    
        for (key,clo) in self.human.clothesObjs.items():
            if clo:
                name = self.goodName(key)
                pfile = CProxyFile()
                pfile.set('Clothes', 3)            
                pfile.obj = clo
                proxy = self.human.clothesProxies[key]
                pfile.file = proxy.file
                proxyList.append(pfile)
                
        if self.human.proxy:
            name = self.goodName(self.human.proxy.name)
            pfile = CProxyFile()
            pfile.set('Proxy', 4)
            pfile.obj = self.human
            pfile.file = self.human.proxy.file
            proxyList.append(pfile)    
    
        if self.cage:
            pfile = CProxyFile()
            pfile.set('Cage', 4)
            pfile.file = os.path.realpath("./data/cages/cage/cage.mhclo")
            proxyList.append(pfile)  
            
        return proxyList


    def setupTexFolder(self, filepath):
        (fname, ext) = os.path.splitext(filepath)
        fname = self.goodName(os.path.basename(fname))
        self.outFolder = os.path.realpath(os.path.dirname(filepath))
        self.filename = os.path.basename(filepath)
        if self.useTexFolder:
            self.texFolder = self.getSubFolder(self.outFolder, "textures")
            self.copiedFiles = {}
    
    
    def getSubFolder(self, path, name):
        folder = os.path.join(path, name)
        print "Using folder", folder
        if not os.path.exists(folder):
            log.message("Creating folder %s", folder)
            try:
                os.mkdir(folder)
            except:
                log.error("Unable to create separate folder:", exc_info=True)
                return None
        return folder        
        
        
    def getTexturePath(self, filePath, fromDir, isTexture, human):
        srcDir = os.path.realpath(os.path.expanduser(fromDir))
        filename = os.path.basename(filePath)

        if human and (filename == "texture.png"):
            fromPath = human.getTexture()
            fileDir = os.path.dirname(fromPath)         
            filename = os.path.basename(fromPath)
            #print(filePath, fromDir, fileDir, fromPath)
            if fileDir == fromDir:
                fromPath = os.path.join(srcDir, filename)
        else:
            fromPath = os.path.join(srcDir, filename)

        if self.useTexFolder:
            if isTexture:
                toPath = os.path.join(self.texFolder, filename)
            else:
                toPath = os.path.join(self.outFolder, filename)
            try:
                self.copiedFiles[fromPath]
                done = True
            except:
                done = False
            if not done:
                if 0 and human:
                    img = mh.Image(human.getTexture())
                    log.debug("%s", dir(img))
                    img.save(toPath)
                    halt
                try:
                    shutil.copyfile(fromPath, toPath)
                except:
                    pass    
                self.copiedFiles[fromPath] = True
            texPath = toPath
        else:
            texPath = os.path.abspath(fromPath)
            
        if not self.useRelPaths:
            return texPath
        else:
            return str(os.path.normpath(os.path.relpath(texPath, self.outFolder)))
            
            
    def goodName(self, name):
        string = name.replace(" ", "_").replace("-","_").lower()
        try:
           return string.encode(self.encoding, 'replace')
        except UnicodeEncodeError:
            log.message("%s cannot encode this file path. Try a different encoding" % self.encoding)
            return string

#
#   class CProxyFile:
#

class CProxyFile:
    def __init__(self):
        self.type = 'Clothes'
        self.layer = 0
        self.file = ""
        self.obj = None
        
    def set(self, type, layer):
        self.type = type
        self.layer = layer
        
    def __repr__(self):
        return ("<CProxyFile %s %d \"%s\">" % (self.type, self.layer, self.file))
        
#
#
#
        
def getExistingProxyFile(path, uuid, category):
    if not uuid:
        if not os.path.exists(os.path.realpath(path)):
            return None
        log.message("Found %s", path)
        return path
    else:
        file = os.path.basename(path)
        paths = []
        folder = os.path.join(mh.getPath(''), 'data', category)
        addProxyFiles(file, folder, paths, 6)
        folder = os.path.join('data', category)
        addProxyFiles(file, folder, paths, 6)
        for path in paths:        
            uuid1 = scanFileForUuid(path)
            if uuid1 == uuid:
                log.message("Found %s %s", path, uuid)
                return path
        return None                


def addProxyFiles(file, folder, paths, depth):
    if depth < 0:
        return None
    try:
        files = os.listdir(folder)        
    except OSError:
        return None
    for pname in files:
        path = os.path.join(folder, pname)
        if pname == file:
            paths.append(path)
        elif os.path.isdir(path):
            addProxyFiles(file, path, paths, depth-1)
    return            


def scanFileForUuid(path):           
    fp = open(path)
    for line in fp:
        words = line.split()
        if len(words) == 0:
            break
        elif words[0] == '#':
            if words[1] == "uuid":
                fp.close()
                return words[2]
        else:
            break
    fp.close()
    return None

def scanFileForTags(path):
    tags = set()
    fp = open(path)
    for line in fp:
        words = line.split()
        if len(words) == 0:
            continue
        elif words[0] == '#':
            if words[1] == "tag":
                tags.add(words[2])
        else:
            break
    fp.close()
    return tags
