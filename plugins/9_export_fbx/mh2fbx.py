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
Fbx exporter

"""

import os.path
import sys

import gui3d
import exportutils
import posemode
import log

import io_fbx
# bpy must be imported after io_fbx
import bpy


def exportFbx(human, filepath, config):
    posemode.exitPoseMode()        
    posemode.enterPoseMode()
    
    config.setHuman(human)
    config.setupTexFolder(filepath)        

    log.message("Write FBX file %s" % filepath)
    print(config)

    rigfile = "data/rigs/%s.rig" % config.rigtype
    rawTargets = exportutils.collect.readTargets(human, config)
    filename = os.path.basename(filepath)
    name = config.goodName(os.path.splitext(filename)[0])
    stuffs = exportutils.collect.setupObjects(
        name, 
        human, 
        config=config,
        rigfile=rigfile, 
        rawTargets=rawTargets,
        helpers=config.helpers, 
        eyebrows=config.eyebrows, 
        lashes=config.lashes)

    bpy.initialize(human, config)
    boneInfo = stuffs[0].boneInfo
    rig = bpy.addRig(name, boneInfo, scale=config.scale)
    for stuff in stuffs:
        ob = bpy.addMesh(stuff.name, stuff, rig, isStuff=True, scale=config.scale)
        
    #name = os.path.splitext(os.path.basename(filepath))[0]
    #bpy.addMesh(name, human.meshData, isStuff=False)
    
    gui3d.app.progress(0, text="Exporting %s" % filepath)
    io_fbx.fbx_export.exportFbxFile(bpy.context, filepath, scale=1.0, encoding=config.encoding)
    gui3d.app.progress(1)
    posemode.exitPoseMode()        
    return

