#!/usr/bin/python
# -*- coding: utf-8 -*-

""" 
**Project Name:**      MakeHuman

**Product Home Page:** http://www.makehuman.org/

**Code Home Page:**    http://code.google.com/p/makehuman/

**Authors:**           Koen Buys

**Copyright(c):**      MakeHuman Team 2001-2013

**Licensing:**         AGPL3 (see also http://www.makehuman.org/node/318)

**Coding Standards:**  See http://www.makehuman.org/node/165

Abstract
--------

Animation library.
A library of sets of animations to choose from that can be exported alongside a MH model.
"""

import gui3d
import mh
import gui
import module3d
import log

import os
import numpy as np

import bvh
import skeleton
import skeleton_drawing
import animation
import filechooser

class BVHAnimLibrary(gui3d.TaskView):

    def __init__(self, category):
        gui3d.TaskView.__init__(self, category, 'BVH')
        
        self.BVH = bvh.BVH()

        #self.systemAnims = os.path.join('data', 'animations')
        #self.userAnims = os.path.join(mh.getPath(''), 'data', 'animations')
        #self.animPaths = [self.userAnims, self.systemAnims]
        #if not os.path.exists(self.userAnims):
        #    os.makedirs(self.userAnims)
        #self.extension = "mhanim"
        
        self.skelObj = None             # indicates skeleton object attached
        self.lastSkeleton = None
        
        self.human = gui3d.app.selectedHuman
        self.oldHumanTransp = self.human.meshData.transparentPrimitives
        
        displayBox = self.addLeftWidget(gui.GroupBox('Display'))
        
        self.showHumanTggl = displayBox.addWidget(gui.ToggleButton("Show human"))
        @self.showHumanTggl.mhEvent
        def onClicked(event):
            if self.showHumanTggl.selected:
                self.human.show()
            else:
                self.human.hide()
        self.showHumanTggl.setSelected(True)
        
        self.showSkeletonTggl = displayBox.addWidget(gui.ToggleButton("Show skeleton"))
        @self.showSkeletonTggl.mhEvent
        def onClicked(event):
            if not self.skelObj:
                return
            if self.showSkeletonTggl.selected:
                self.skelObj.show()
                self.setHumanTransparency(True)
            else:
                self.skelObj.hide()
                self.setHumanTransparency(False)
        self.showSkeletonTggl.setSelected(True)

        self.skinProxiesTggl = displayBox.addWidget(gui.ToggleButton("Skin clothes and hair"))
        @self.skinProxiesTggl.mhEvent
        def onClicked(event):
            self.setupProxySkinning()
        self.skinProxiesTggl.setSelected(False)
        
        pathBox = self.addLeftWidget(gui.GroupBox('BVH  path'))
        self.path = pathBox.addWidget(gui.TextEdit('/'), 0, 0, 1, 2)
        self.file = pathBox.addWidget(gui.BrowseButton('open'), 1, 0, 1, 1)
        self.file.setLabel("Select BVH")
        
        @self.path.mhEvent
        def onChange(value):
            print '[BVHAnimLibrary: onChange] Path value changed:' + value

        @self.file.mhEvent
        def onClicked(file):
            #if os.path.isdir(path):
            print '[BVHAnimLibrary: onClicked] File value changed:' + file
            self.path.setText(file)
            if os.path.isfile(file):
                self.BVH = bvh.load(file)
                #self.BVH.fromFile(file)
                print '[BVHAnimLibrary: onClicked] Loaded BVH file'
        
        # ----------------------------------------------------------------------------------------------------
    def onShow(self, event):
        gui3d.TaskView.onShow(self, event)
        print '[BVHAnimLibrary: onShow] called'

        if not self.human.getSkeleton():
            gui3d.app.statusPersist("No skeleton selected. Please select a skeleton rig from the Skeleton library first.")
            return

        # Detect when skeleton (rig type) has changed
        if self.human.getSkeleton() and self.human.getSkeleton().name != self.lastSkeleton:
            # Remove cached animation tracks (as they are mapped to a specific skeleton)
            self.human.animated.removeAnimations()
            self.anim = None
            self.animTrack = None
            # NOTE that animation tracks only need to be removed when the rig
            # structure changes, not when only joint positions are translated
            # a bit because of a change to the human model.

        self.lastSkeleton = self.human.getSkeleton().name

        # Disable smoothing in animation library
        self.oldSmoothValue = self.human.isSubdivided()
        self.human.setSubdivided(False)

        self.oldHumanTransp = self.human.meshData.transparentPrimitives
        self.human.meshData.setPickable(False)
        mh.updatePickingBuffer()

        self.skelObj = self.human.getSkeleton().object
        if self.skelObj:
            self.skelMesh = self.skelObj.mesh

            if self.showSkeletonTggl.selected:
                self.skelObj.show()
                # Show skeleton through human 
                self.setHumanTransparency(True)
            else:
                self.skelObj.hide()
        else:
            self.skelMesh = None

        self.setupProxySkinning()

    def onHide(self, event):
        gui3d.TaskView.onHide(self, event)

        self.setToRestPose()
        self.setHumanTransparency(False)
        self.human.meshData.setPickable(True)
        mh.updatePickingBuffer()

        if self.skelObj:
            self.skelObj.hide()

        self.skelObj = None 
        self.skelMesh = None

        # Restore possible hidden proxies (clothes and hair)
        for (name,obj) in self.human.clothesObjs.items():
            obj.show()
        if self.human.hairObj:
            self.human.hairObj.show()

        # Reset smooth setting
        self.human.setSubdivided(self.oldSmoothValue)
        
def load(app):
    category = app.getCategory('Pose/Animate')
    taskview = BVHAnimLibrary(category)
    taskview.sortOrder = 3.5
    category.addTask(taskview)

    #app.addLoadHandler('animations', taskview.loadHandler)
    #app.addSaveHandler(taskview.saveHandler)

# This method is called when the plugin is unloaded from makehuman
# At the moment this is not used, but in the future it will remove the added GUI elements

def unload(app):
    pass

