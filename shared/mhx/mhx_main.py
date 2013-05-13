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

MakeHuman to MHX (MakeHuman eXchange format) exporter. MHX files can be loaded into Blender
"""

MAJOR_VERSION = 1
MINOR_VERSION = 15
BODY_LANGUAGE = True

import module3d
import gui3d
import os
import time
import numpy
import math
import log

#import cProfile

import mh2proxy
import exportutils
import warpmodifier
import posemode
import exportutils

from armature.rigdefs import CArmature

from . import posebone
from . import mhx_materials
from . import mhx_mesh
from . import mhx_proxy
from . import mhx_armature
from . import mhx_pose

#-------------------------------------------------------------------------------        
#   Export MHX file
#-------------------------------------------------------------------------------        

def exportMhx(human, filepath, config):  
    gui3d.app.progress(0, text="Exporting MHX")
    log.message("Exporting %s" % filepath.encode('utf-8'))
    time1 = time.clock()
    posemode.exitPoseMode()        
    posemode.enterPoseMode()
    
    config.setHuman(human)
    config.setupTexFolder(filepath)    

    filename = os.path.basename(filepath)
    name = config.goodName(os.path.splitext(filename)[0])
    fp = open(filepath, 'w')
        
    if config.rigtype == 'mhx':
        amt = mhx_armature.MhxArmature(name, human, config)
    elif config.rigtype == 'rigify':
        amt = mhx_armature.RigifyArmature(name, human, config)
    else:
        amt = mhx_armature.ExportArmature(name, human, config)
    
    fp.write(
        "# MakeHuman exported MHX\n" +
        "# www.makeinfo.human.org\n" +
        "MHX %d %d ;\n" % (MAJOR_VERSION, MINOR_VERSION) +
        "#if Blender24\n" +
        "  error 'This file can only be read with Blender 2.5' ;\n" +
        "#endif\n")

    scanProxies(config, amt)
    amt.setup()
    
    if not config.cage:
        fp.write(
            "#if toggle&T_Cage\n" +
            "  error 'This MHX file does not contain a cage. Unselect the Cage import option.' ;\n" +
            "#endif\n")

    fp.write(
        "NoScale True ;\n" +
        "Object CustomShapes EMPTY None\n" +
        "  layers Array 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1  ;\n" +
        "end Object\n\n")

    amt.setupCustomShapes(fp)
        
    gui3d.app.progress(0.1, text="Exporting armature")
    amt.writeArmature(fp, MINOR_VERSION)
    
    gui3d.app.progress(0.15, text="Exporting materials")    
    fp.write("\nNoScale False ;\n\n")
    mhx_materials.writeMaterials(fp, amt, config)

    if config.cage:
        mhx_proxy.writeProxyType('Cage', 'T_Cage', amt, config, fp, 0.2, 0.25)
    
    gui3d.app.progress(0.25, text="Exporting main mesh")    
    fp.write("#if toggle&T_Mesh\n")
    mhx_mesh.writeMesh(fp, amt, config)
    fp.write("#endif\n")

    mhx_proxy.writeProxyType('Proxy', 'T_Proxy', amt, config, fp, 0.35, 0.4)
    mhx_proxy.writeProxyType('Clothes', 'T_Clothes', amt, config, fp, 0.4, 0.55)
    mhx_proxy.writeProxyType('Hair', 'T_Clothes', amt, config, fp, 0.55, 0.6)

    mhx_pose.writePose(fp, amt, config)

    writeGroups(fp, amt)

    if config.rigtype == 'rigify':
        fp.write("Rigify %s ;\n" % amt.name)

    fp.close()
    log.message("%s exported" % filepath.encode('utf-8'))
    gui3d.app.progress(1.0)
    return
    
#-------------------------------------------------------------------------------        
#   Scan proxies
#-------------------------------------------------------------------------------        
    
def scanProxies(config, amt):
    amt.proxies = {}
    for pfile in config.getProxyList():
        if pfile.file:
            proxy = mh2proxy.readProxyFile(amt.mesh, pfile, True)
            if proxy:
                amt.proxies[proxy.name] = proxy        

#-------------------------------------------------------------------------------        
#   Groups   
#-------------------------------------------------------------------------------        
    
def writeGroups(fp, amt):    
    fp.write("""
# ---------------- Groups -------------------------------- # 

""")
    fp.write(
        "PostProcess %sMesh %s 0000003f 00080000 %s 0000c000 ;\n" % (amt.name, amt.name, amt.boneLayers) + 
        "Group %s\n"  % amt.name +
        "  Objects\n" +
        "    ob %s ;\n" % amt.name +
        "#if toggle&T_Mesh\n" +
        "    ob %sMesh ;\n" % amt.name +
        "#endif\n")

    groupProxy('Cage', 'T_Cage', fp, amt)
    groupProxy('Proxy', 'T_Proxy', fp, amt)
    groupProxy('Clothes', 'T_Clothes', fp, amt)
    groupProxy('Hair', 'T_Clothes', fp, amt)

    fp.write(
        "    ob CustomShapes ;\n" + 
        "  end Objects\n" +
        "  layers Array 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1  ;\n" +
        "end Group\n")
    return
    

def groupProxy(typ, test, fp, amt):
    fp.write("#if toggle&%s\n" % test)
    for proxy in amt.proxies.values():
        if proxy.type == typ:
            name = amt.name + proxy.name
            fp.write("    ob %sMesh ;\n" % name)
    fp.write("#endif\n")
    return

