#!/usr/bin/python
# -*- coding: utf-8 -*-

##
# PCL/People export plugin for Makehuman Alpha 0.7
#
# Author: Jonas Hauquier, Koen Buys
##
# TODO license to be determined
# Is this part allowed to be BSD?

# TODO be more explicit in readme about paths (to create or where MH can be installed)
# TODO export images only to ~/makehuman/
# TODO remove some of the verbose console prints
# TODO add bone highlighting with weights visualisation like in skeleton library?
# TODO visualize source to target rig mapping using colored bones?
# TODO also allow manual choice of source rig? (or at least guess from bvh files)
# TODO add vertex group loading again (accelerated using numpy)
# TODO visualize MHX to human mapping using colors?
# TODO visualize source to target rig mapping using colored bones
# TODO bake skin with color regions
# TODO properly document blender workflow for labeling body on blog
# TODO also allow manual choice of source rig
# TODO make compatible with new post-alpha 7 API
# TODO MHX bodypart loading might be broken after Revision: r3802, post alpha 7 (verify!)
# TODO Implement texture rendering
# TODO automate from script? (camera position, input files, ...)


import gui3d, gui
import module3d
import log
import mh
import bvh
import skeleton
import skeleton_drawing
import animation
import numpy as np
import sys, os

import events3d
import geometry3d
import projection
import language
import texture


from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GL import shaders
from PyQt4 import QtCore, QtGui, QtOpenGL

from glmodule import *

RENDER_HELPERS = False
WARNINGS = False
SHOW_PICTURES = False
SPARSIFY = True # If set to true, reduce animation framerate to 30 FPS if it is higher (probably not necessary


# Retrieve data path
DATA_PATH = os.path.join(mh.getPath(''), 'data', 'people_export')


log.message('PCL/People pipeline plugin imported')

class PeopleExportTaskView(gui3d.TaskView):

    def __init__(self, category):
        # Setup GUI elements
        gui3d.TaskView.__init__(self, category, 'Actions')

        box = self.addLeftWidget(gui.GroupBox('Export'))
        self.rigButton = box.addWidget(FileSelectView('Load BVH'))
        self.rigButton.setDirectory(DATA_PATH)
        self.rigButton.setFilter('Biovision Motion Hierarchy (*.bvh)')
        self.exportButton = box.addWidget(gui.Button('Export animation'))
        self.exportAllButton = box.addWidget(gui.Button('Export all'))

        self.window = None
        @self.rigButton.mhEvent
        def onFilesSelected(filenames):
            if not self.skel:
                self.loadRig()
            loadFirst = (self.animationList.rowCount() == 0)
            for filename in filenames:
                if filename not in self.selectedBVHs:
                    item = self.animationList.addItem(os.path.splitext(os.path.basename(filename))[0])
                    item.filename = filename
                    self.selectedBVHs.add(filename)
            if loadFirst:
                self.loadAnimation(filenames[0])

        @self.exportButton.mhEvent
        def onClicked(event):
            self.export()

        @self.exportAllButton.mhEvent
        def onClicked(event):
            self.exportAll()

        self.human = gui3d.app.selectedHuman
        self.humanChanged = False
        self.humanTransparent = False

        self.selectedBVHs = set()

        self.skel = None
        self.animated = None

        self.bvhAnimated = None

        self.skelMesh = None
        self.skelObj = None

        self.bvhMesh = None
        self.bvhObj = None

        self.timer = None
        self.currFrame = 0
        self.anim = None

        self.bvhAnim = None

        self.oldHumanTransp = self.human.meshData.transparentPrimitives

        optionsBox = self.addLeftWidget(gui.GroupBox('Options'))
        self.kinectCamTggle = optionsBox.addWidget(gui.ToggleButton("Kinect camera"))
        self.kinectCamTggle.setSelected(True)

        self.useMHCamTggl = optionsBox.addWidget(gui.ToggleButton("Use camera pos"))
        self.useMHCamTggl.setSelected(False)

        mesh = BackPlane(20, 20, centered=True)
        self.bgPlane = self.addObject(gui3d.Object([0, 0, 0], mesh))
        mesh.setColor([255, 255, 255, 255])
        mesh.setShadeless(True)
        mesh.priority = -90

        mesh = GroundPlane(20, 20, centered=True)
        self.groundPlane = self.addObject(gui3d.Object([0, 0, 0], mesh))
        mesh.setColor([0, 0, 0, 255])
        mesh.setShadeless(True)
        mesh.priority = -90

        yOffset = self.getFeetOnGroundOffset()
        self.groundposSlider = optionsBox.addWidget(gui.Slider(value=int(yOffset), min=-125,max=125, label = "Ground Pos: %d"))
        self.groundposVal = int(yOffset)
        self.groundPlane.mesh.move(0,yOffset,0)

        @self.groundposSlider.mhEvent
        def onChanging(value):
            val = value - self.groundposVal
            self.groundPlane.mesh.move(0,val,0)
            self.groundposVal = self.groundposVal + val
        @self.groundposSlider.mhEvent
        def onChange(value):
            val = value - self.groundposVal
            self.groundPlane.mesh.move(0,val,0)
            self.groundposVal = self.groundposVal + val

        self.backposSlider = optionsBox.addWidget(gui.Slider(value=-9, min=-125,max=125, label = "Back Pos: %d"))
        self.backposVal = -9

        @self.backposSlider.mhEvent
        def onChanging(value):
            val = value - self.backposVal
            self.bgPlane.mesh.move(0,0,val)
            self.backposVal = self.backposVal + val
        @self.backposSlider.mhEvent
        def onChange(value):
            val = value - self.backposVal
            self.bgPlane.mesh.move(0,0,val)
            self.backposVal = self.backposVal + val

        self.bgPlane.mesh.move(0,0,self.backposVal)
        
        displayBox = self.addRightWidget(gui.GroupBox('Display'))
        self.showHumanTggl = displayBox.addWidget(gui.ToggleButton("Show human"))
        @self.showHumanTggl.mhEvent
        def onClicked(event):
            if self.showHumanTggl.selected:
                self.human.show()
            else:
                self.human.hide()
        self.showHumanTggl.setSelected(True)

        self.showMHXRigTggl = displayBox.addWidget(gui.ToggleButton("Show human Rig"))
        @self.showMHXRigTggl.mhEvent
        def onClicked(event):
            self.setShowRig(self.showMHXRigTggl.selected)
        self.showMHXRigTggl.setSelected(True)
 
        self.showBVHRigTggl = displayBox.addWidget(gui.ToggleButton("Show BVH Rig"))
        @self.showBVHRigTggl.mhEvent
        def onClicked(event):
            self.setShowBVHRig(self.showBVHRigTggl.selected)
        self.showBVHRigTggl.setSelected(False)

        self.imageExported = False

        self.playbackBox = None
        self.playPause = None

        self.createPlaybackControl()
        animationListBox = self.addRightWidget(gui.GroupBox('BVHs'))
        self.animationList = animationListBox.addWidget(gui.ListView())
        self.animationList.setSizePolicy(QtGui.QSizePolicy.Ignored, QtGui.QSizePolicy.MinimumExpanding)
        self.animationList.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        @self.animationList.mhEvent
        def onClicked(item):
            self.loadAnimation(item.filename)
        self.removeAnimBtn = animationListBox.addWidget(gui.Button('Remove selected'))
        @self.removeAnimBtn.mhEvent
        def onClicked(item):
            print "remove clicked"
            if len(self.animationList.selectedItems()) > 0:
                print "taking action"
                item = self.animationList.selectedItems()[0]
                self.removeAnimation(item.filename)

    def loadRig(self):
        if self.animated:
            # Set human mesh back to rest pose before removing the animatedMesh
            self.animated.setToRestPose()

        rigtype = "soft1"
        filename = os.path.join("data", "rigs", rigtype+".rig")
        self.skel, boneWeights = skeleton.loadRig(filename, self.human.meshData)
        self.animated = animation.AnimatedMesh(self.skel, self.human.meshData, boneWeights)

        # (Re-)draw the skeleton
        self.drawSkeleton(self.skel)

    # TODO load multiple animations

    def loadAnimation(self, filename):
        global SPARSIFY

        log.message("Loading BVH animation %s", filename)
        animName = unicode(os.path.splitext(os.path.basename(filename))[0])
        self.stopPlayback()
        if not self.animated.hasAnimation(animName):
            # TODO cache bvh file (and mappings)
            bvhRig = bvh.load(filename)
            # TODO scale bvh by comparing upper leg length
            bvhRig.scale(0.7)
            bvhRig.filename = filename

            # TODO cache mapping
            #jointToBoneMap = skeleton.loadJointsMapping("soft1", self.skel)
            retargetMapping = skeleton.getRetargetMapping('mb', 'soft1', self.skel)
            #retargetMapping = skeleton.getRetargetMappingFromBVH(bvhRig, 'soft1', self.skel)
            # TODO guess format of source rig

            animTrack = bvhRig.createAnimationTrack(retargetMapping, animName)
            if SPARSIFY:
                if animTrack.frameRate > 30:
                    animTrack.sparsify(30)

            self.animated.addAnimation(animTrack)

            #self.__bvhRigCache['mb']  # TODO cache rig for all BVH rig types, for now we assume all BVHs are mb format
        else:
            animTrack = self.animated.getAnimation(animName)

        if not self.bvhAnimated or not self.bvhAnimated.hasAnimation(animName):
            # Draw BVH rig and/or add animation
            self.loadBVHRig(bvhRig)

        self.animated.setActiveAnimation(animName)
        self.anim = animTrack
        self.anim.interpolationType = 0
        self.createPlaybackControl()
        self.animated.setAnimateInPlace(self.animateInPlaceTggl.selected)
        self.animated.setToFrame(0)
        self.setShowRig(self.showMHXRigTggl.selected)

        self.bvhAnimated.setActiveAnimation(animName)
        self.bvhAnimated.setAnimateInPlace(self.animateInPlaceTggl.selected)
        self.bvhAnimated.setToFrame(0)
        self.setShowBVHRig(self.showBVHRigTggl.selected)

        self.__setSelectedAnimation(filename)
        self.startPlayback()

    def removeAnimation(self, filename):
        print "removing %s" % filename
        animName = unicode(os.path.splitext(os.path.basename(filename))[0])
        self.stopPlayback()
        if self.animated.hasAnimation(animName):
            print "removed from anim"
            self.animated.removeAnimation(animName)
        if self.bvhAnimated.hasAnimation(animName):
            print "removed from bvh anim"
            self.bvhAnimated.removeAnimation(animName)
        for listItem in self.animationList.getItems():
            if listItem.filename == filename:
                print "removed from list"
                self.animationList.takeItem(self.animationList.row(listItem))
                return

    def drawSkeleton(self, skel):
        # Create a mesh from the skeleton in rest pose
        skel.setToRestPose() # Make sure skeleton is in rest pose when constructing the skeleton mesh
        self.skelMesh = skeleton_drawing.meshFromSkeleton(skel, "Prism")
        self.skelMesh.priority = 100
        self.skelObj = self.addObject(gui3d.Object(self.human.getPosition(), self.skelMesh) )
        self.skelObj.setRotation(self.human.getRotation())

        # Add the skeleton mesh to the human AnimatedMesh so it animates together with the skeleton
        # The skeleton mesh is supposed to be constructed from the skeleton in rest and receives
        # rigid vertex-bone weights (for each vertex exactly one weight of 1 to one bone)
        mapping = skeleton_drawing.getVertBoneMapping(skel, self.skelMesh)
        self.animated.addMesh(self.skelMesh, mapping)
        self.setShowRig(self.showMHXRigTggl.selected)

    def loadBVHRig(self, bvhRig):
        global SPARSIFY

        # Draw BVH skeleton if it does not exist yet
        if not self.bvhMesh:
            self.bvhSkel = bvhRig.createSkeleton()
            self.bvhMesh = skeleton_drawing.meshFromSkeleton(self.bvhSkel, "Prism")
            self.bvhMesh.priority = 100
            self.bvhMesh.setColor([0, 255, 0, 255])
            self.bvhObj = self.addObject(gui3d.Object(self.human.getPosition(), self.bvhMesh) )
            self.bvhObj.setRotation(self.human.getRotation())

            # Get rigid weights for skeleton mesh
            boneWeights = skeleton_drawing.getVertBoneMapping(self.bvhSkel, self.bvhMesh)
            self.bvhAnimated = animation.AnimatedMesh(self.bvhSkel, self.bvhMesh, boneWeights)

        # Load animation to BVH rig
        animName = unicode(os.path.splitext(os.path.basename(bvhRig.filename))[0])
        trivialMap = [bone.name for bone in self.bvhSkel.getBones()]
        animTrack = bvhRig.createAnimationTrack(trivialMap, animName)
        animTrack.interpolationType = 0
        if animTrack.frameRate > 30:
            animTrack.sparsify(30)

        self.bvhAnimated.addAnimation(animTrack)

    def setShowRig(self, visible):
        if not self.skelObj:
            if not self.bvhObj or not self.bvhObj.visible:
                self.setHumanTransparency(False)
            return

        if visible:
            self.skelObj.show()
            self.setHumanTransparency(True)
        else:
            self.skelObj.hide()
            if not self.bvhObj or not self.bvhObj.visible:
                self.setHumanTransparency(False)

    def setShowBVHRig(self, visible):
        if not self.bvhObj:
            if not self.skelObj or not self.skelObj.visible:
                self.setHumanTransparency(False)
            return

        if visible:
            self.bvhObj.show()
            self.setHumanTransparency(True)
        else:
            self.bvhObj.hide()
            if not self.skelObj or not self.skelObj.visible:
                self.setHumanTransparency(False)

    def setHumanTransparency(self, enabled):
        self.humanTransparent = enabled
        if enabled:
            log.message("Enable human Transparency")
            self.human.meshData.setTransparentPrimitives(len(self.human.meshData.fvert))
        else:
            log.message("Disable human Transparency")
            self.human.meshData.setTransparentPrimitives(self.oldHumanTransp)
        #self.renderTextures = False # TODO check if this line is still needed?

    def createPlaybackControl(self):
        if self.anim:
            maxFrames = self.anim.nFrames
            if maxFrames < 1:
                maxFrames = 1
        else:
            maxFrames = 1

        if self.playbackBox:
            self.frameSlider.setMin(0)
            self.frameSlider.setMax(maxFrames)
            self.currFrame = 0
            self.frameSlider.setValue(0)
            return

        self.playbackBox = self.addRightWidget(gui.GroupBox('BVH playback'))
        self.frameSlider = self.playbackBox.addWidget(gui.Slider(value = 0, min = 0, max = maxFrames, label = 'Frame: %d', vertical=False, valueConverter=None, image=None, scale=100000))
        @self.frameSlider.mhEvent
        def onChanging(value):
            self.updateAnimation(value)
        @self.frameSlider.mhEvent
        def onChange(value):
            self.updateAnimation(value)
            
        self.playPause = self.playbackBox.addWidget(gui.Button("Play"))
        @self.playPause.mhEvent
        def onClicked(value):
            if self.playPause.text() == 'Play':
                self.startPlayback()
            else:
                self.stopPlayback()

        self.animateInPlaceTggl = self.playbackBox.addWidget(gui.ToggleButton("In-place animation"))
        @self.animateInPlaceTggl.mhEvent
        def onClicked(event):
            if not self.animated:
                return
            if self.animated:
                self.animated.setAnimateInPlace(self.animateInPlaceTggl.selected)
            if self.bvhAnimated:
                self.bvhAnimated.setAnimateInPlace(self.animateInPlaceTggl.selected)
            self.updateAnimation(self.currFrame)
        self.animateInPlaceTggl.setSelected(True)

        self.restPoseBtn = self.playbackBox.addWidget(gui.Button("Set to Rest Pose"))
        @self.restPoseBtn.mhEvent
        def onClicked(value):
            self.setToRestPose()

    def startPlayback(self):
        self.playPause.setText('Pause')
        if self.timer:
            mh.removeTimer(self.timer)
            self.timer = None
        self.timer = mh.addTimer(max(30, int(1.0/self.anim.frameRate * 1000)), self.onFrameChanged)

    def stopPlayback(self):
        if not self.playPause:
            return
        self.playPause.setText('Play')
        if self.timer:
            mh.removeTimer(self.timer)
            self.timer = None

    def setToRestPose(self):
        if not self.animated:
            return
        self.stopPlayback()
        self.animated.setToRestPose()
        if self.bvhAnimated:
            self.bvhAnimated.setToRestPose()

    def onFrameChanged(self):
        frame = self.currFrame + 1
        
        if frame > self.frameSlider.max:
            frame = 1

        self.frameSlider.setValue(frame)
        self.updateAnimation(frame)
        gui3d.app.redraw()

    def updateAnimation(self, frame):
        if not self.anim or not self.skel:
            return
        self.currFrame = frame
        self.animated.setActiveAnimation(self.anim.name)
        self.animated.setToFrame(frame)
        self.animated.setAnimateInPlace(self.animateInPlaceTggl.selected)

        self.bvhAnimated.setActiveAnimation(self.anim.name)
        self.bvhAnimated.setToFrame(frame)
        self.bvhAnimated.setAnimateInPlace(self.animateInPlaceTggl.selected)

    def getFeetOnGroundOffset(self):
        bBox = self.human.meshData.calcBBox()
        dy = bBox[0][1]
        return dy

    def onHumanRotated(self, event):
        if self.skelObj:
            self.skelObj.setRotation(gui3d.app.selectedHuman.getRotation())
        if self.bvhObj:
            self.bvhObj.setRotation(gui3d.app.selectedHuman.getRotation())
        self.groundPlane.setRotation(gui3d.app.selectedHuman.getRotation())
        self.bgPlane.setRotation(gui3d.app.selectedHuman.getRotation())

    def onHumanTranslated(self, event):
        if self.skelObj:
            self.skelObj.setPosition(gui3d.app.selectedHuman.getPosition())
        if self.bvhObj:
            self.bvhObj.setPosition(gui3d.app.selectedHuman.getPosition())
        self.groundPlane.setPosition(gui3d.app.selectedHuman.getPosition())
        self.bgPlane.setPosition(gui3d.app.selectedHuman.getPosition())

    def onHumanChanging(self, event):
        human = event.human
        self.humanChanged = True
        if event.change == 'reset':
            self.stopPlayback()
            self.anim = None

    def onShow(self, event):
        self.oldHumanTransp = self.human.meshData.transparentPrimitives
        self.oldTex = self.human.getTexture()
        self.human.setTexture(os.path.join(DATA_PATH, '..', 'skins', 'bodyparts.png'))  # TODO change hardcoded texture with loaded one??

        if self.humanChanged and self.skel:
            log.message("Reloading skeleton and animation")
            # Reload skeleton and animation
            self.resetSkeletons()
            self.humanChanged = False
            self.loadRig()
            #self.loadAnimation()
        self.setShowRig(self.showMHXRigTggl.selected)

    def onHide(self, event):
        self.stopPlayback()
        if self.animated:
            self.animated.setToRestPose()
        self.setShowRig(False)
        self.setShowBVHRig(False)
        self.human.setTexture(self.oldTex)

    def export(self):
        log.message("Exporting")
        oldTransp = self.humanTransparent
        self.setHumanTransparency(False)
        animName = self.anim.name
        self.renderAnimation(animName)
        self.setHumanTransparency(oldTransp)

    def exportAll(self):
        log.message("Exporting All")
        for bvhFile in [item.filename for item in self.animationList.getItems()]:
            self.loadAnimation(bvhFile)
            self.export()

    def renderAnimation(self, animName, clearColor=[150.0/255, 57.0/255, 80.0/255, 1.0], width=800, height=600):
        # TODO this creates an error with me
        #from glmodule import *
        from texture import Texture
        from core import G

        dst = Texture( size = (width, height) )

        # Bind a framebuffer (render-to-texture)
        framebuffer = glGenFramebuffers(1)
        glBindFramebuffer(GL_FRAMEBUFFER, framebuffer)
        glFramebufferTexture2D(GL_DRAW_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_2D, dst.textureId, 0)
        glFramebufferTexture2D(GL_READ_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_2D, dst.textureId, 0)

        # Bind the depth buffer
        depthrenderbuffer = glGenRenderbuffers(1)
        glBindRenderbuffer(GL_RENDERBUFFER, depthrenderbuffer)
        glRenderbufferStorage(GL_RENDERBUFFER, GL_DEPTH_COMPONENT24, width, height)
        glFramebufferRenderbuffer(GL_FRAMEBUFFER, GL_DEPTH_ATTACHMENT, GL_RENDERBUFFER, depthrenderbuffer)

        if clearColor is not None:
            glClearColor(clearColor[0], clearColor[1], clearColor[2], clearColor[3])
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glDepthFunc(GL_LEQUAL)
        glEnable(GL_DEPTH_TEST)

        glViewport(0, 0, width, height)
        self.defineCamera(width, height, not self.kinectCamTggle.selected)

        self.animated.setActiveAnimation(animName)
        anim = self.animated.getAnimation(animName)
        surface = np.empty((height, width, 4), dtype = np.uint8)
        depth_surface = np.empty((height, width, 1), dtype = np.float32)
        depth_surface_16 = np.empty((height, width, 1), dtype = np.uint16)
        
        obj = self.human.mesh.object3d
        oldShading = obj.shadeless
        obj.parent.setShadeless(True)
        #obj.parent.transparentPrimitives = 0
        
        bg = self.backgroundImage.mesh.object3d
        
        for frameIdx in xrange(anim.nFrames):
            self.animated.setToFrame(frameIdx)
            
            bg.draw() # TODO fix how to get this into depth image as well
            obj.draw()

            glReadPixels(0, 0, width, height, GL_RGBA, GL_UNSIGNED_BYTE, surface)
            img = Image(data = np.ascontiguousarray(surface[::-1,:,:3]))
            outpath = os.path.join(DATA_PATH, 'rgb_%s_%s.png' % (animName, frameIdx))  # TODO this doesn't indicate the projection matrix, not enough info to differ
            log.message("Saving to " + outpath)
            img.save(outpath)
            
            # http://pyopengl.sourceforge.net/documentation/manual-3.0/glReadPixels.xhtml#param-format
            glReadPixels(0, 0, width, height, GL_DEPTH_COMPONENT, GL_FLOAT, depth_surface)
            depth_img = Image(data = np.ascontiguousarray(depth_surface[::-1,:,:3]))
            depth_outpath = os.path.join(DATA_PATH, 'd_32f_%s_%s.png' % (animName, frameIdx))  # TODO this doesn't indicate the projection matrix, not enough info to differ
            log.message("Saving to " + depth_outpath)
            depth_img.save(depth_outpath)
            
            # Also save the image as uint8 image
            glReadPixels(0, 0, width, height, GL_DEPTH_COMPONENT, GL_UNSIGNED_SHORT, depth_surface_16)
            #depth_img8 = Image(data = np.ascontiguousarray(depth_surface_8[::-1,:,:3]))
            depth_img_16 = Image(data = np.ascontiguousarray(depth_surface_16[::-1,:,:1]))
            depth_outpath_16 = os.path.join(DATA_PATH, 'd_ui16_%s_%s.png' % (animName, frameIdx))  # TODO this doesn't indicate the projection matrix, not enough info to differ
            log.message("Saving to " + depth_outpath_16)
            depth_img_16.save(depth_outpath_16)
            
            
            glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        obj.parent.setShadeless(oldShading)

        # Unbind texture
        glFramebufferTexture2D(GL_DRAW_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_2D, 0, 0)
        glFramebufferTexture2D(GL_READ_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_2D, 0, 0)
        glBindFramebuffer(GL_FRAMEBUFFER, 0)

        glDeleteFramebuffers(np.array([framebuffer]))

        gui3d.app.mainwin.canvas.resizeGL(G.windowWidth, G.windowHeight)
        # TODO save alpha as depth

        return surface

    def getProjMat(self, f, W, H, zNear, zFar):
        '''buildPMat(float f, int W, int H, float zNear, float zFar, float* PMat)'''
        PMat = [ [-2.0*f/W, 0,       0,                            0],
                 [0,       2.0*f/H, 0,                            0],
                 [0,       0,       (zFar+zNear)/(zFar-zNear),    1],
                 [0,       0,       -(2*zFar*zNear)/(zFar-zNear), 0] ]
        # we ll have to add 1/H and 1/W to get the 1/2 pixel offset later
        return np.asarray(PMat, dtype=np.float32)

    def defineCamera(self, width, height, simple=False):
        # TODO copy mh camera proj matrix in case of simple
        if simple:
            # Default makehuman camera projection
            log.message("Using makehuman camera projection")
            glMatrixMode(GL_PROJECTION)
            glLoadIdentity()
            camera = gui3d.app.modelCamera
            # Same camera as in MH viewport

            gluPerspective(camera.fovAngle, 
                           float(width)/float(height), 
                           camera.nearPlane, 
                           camera.farPlane)
        else:
            # Kinect camera projection
            log.message("Using kinect-style camera projection")
            glMatrixMode(GL_PROJECTION)
            glLoadIdentity()
            pMat = self.getProjMat(640, width, height, 0.1, 100.0)
            glLoadMatrixf(pMat)

        self.defineModelView(simple, self.useMHCamTggl.selected)

    def defineModelView(self, simple, mhOrientation=False):

        if mhOrientation:
            log.message("Applying model transformation from Makehuman viewport")

        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()

        if simple:
            if mhOrientation:
                # Define camera position
                camera = gui3d.app.modelCamera
                gluLookAt(camera.eyeX,
                          camera.eyeY,
                          camera.eyeZ,
                          camera.focusX,
                          camera.focusY,
                          camera.focusZ,
                          camera.upX,
                          camera.upY,
                          camera.upZ)
                # Apply inverse transformations for human translate and rotate
                glPushMatrix()
                position = self.human.getPosition()
                glTranslatef(position[0], position[1], position[2])
                rotation = self.human.getRotation()
                glRotatef(rotation[0], 1, 0, 0) # rx
                glRotatef(rotation[1], 0, 1, 0) # ry
                glRotatef(rotation[2], 0, 0, 1) # rz
                #scale = self.human.getScale()
                #glScalef(self.human.sx, self.human.sy, self.human.sz)
            else:
                # Move camera backwards from origin.
                glTranslatef(0.0, 0.0, -50.0)
        else:
            if mhOrientation:
                # Define camera position
                camera = gui3d.app.modelCamera
                '''
                gluLookAt(-camera.eyeX,
                          camera.eyeY,
                          -camera.eyeZ,
                          -camera.focusX,
                          camera.focusY,
                          -camera.focusZ,
                          -camera.upX,
                          camera.upY,
                          -camera.upZ)
                '''
                glTranslatef(0.0, 0.0, 25.0)
                glRotatef(180.0, 0.0, 1.0, 0.0)
                # TODO calculate camera position and orientation
                #glTranslatef(camera.eyeX, -camera.eyeY, -camera.eyeZ)

                position = self.human.getPosition()
                glTranslatef(position[0], position[1], -position[2])

                rotation = self.human.getRotation()
                glRotatef(rotation[0], 1, 0, 0) # rx
                glRotatef(rotation[1], 0, 1, 0) # ry
                glRotatef(rotation[2], 0, 0, 1) # rz
            else:
                # Move camera backwards from origin.
                glTranslatef(0.0, 0.0, 25.0)
                # Rotate camera 180 degrees around center (along the up vector)
                #glPushMatrix()
                glRotatef(180.0, 0.0, 1.0, 0.0)

    def initShaders(self):
        self.shader_vp = '''
            #version 120
            // Vertex shader

            // Output parameters
            varying float lin_z;

            // Entry point
            void main() {
                gl_Position = gl_ModelViewMatrix * gl_Vertex;
                lin_z = gl_Position.z;
                gl_Position = gl_ProjectionMatrix * gl_Position;
                gl_FrontColor = gl_Color;
            }
        '''

        self.shader_fp = '''
            #version 120
            // Fragment (pixel) shader

            // Input parameters
            // also the output parameters for the vertex shader
            varying float lin_z;

            // Entry point
            void main() {
                gl_FragColor = gl_Color;
                // Store scaled depth value in alpha channel
                gl_FragColor.a = lin_z/100;
                    // Divide by far plane (TODO calculate from matrix)
            }
        '''
        self.vertex_shader = shaders.compileShader(self.shader_vp, 
                                                        GL_VERTEX_SHADER)
        self.fragment_shader = shaders.compileShader(self.shader_fp,
                                                        GL_FRAGMENT_SHADER)
        self.shader = shaders.compileProgram(self.vertex_shader,
                                             self.fragment_shader)

    def resetSkeletons(self):
        if self.skelObj:
            # Remove old skeleton mesh
            gui3d.app.removeObject(self.skelObj)
            self.skelObj = None
            self.skelMesh = None
            self.animated = None
        if self.bvhObj:
            # Remove old bvh mesh
            gui3d.app.removeObject(self.bvhObj)
            self.bvhObj = None
            self.bvhMesh = None
            self.bvhAnimated = None

    def __setSelectedAnimation(self, filename):
        """
        Set the selected animation in the animation list widget.
        """
        for listItem in self.animationList.getItems():
            if listItem.filename == filename:
                self.animationList.setCurrentItem(listItem)
                return

################################################################################

class GroundPlane(geometry3d.RectangleMesh):
    """
    Horizontal plane.
    """

    def __init__(self, width, height, centered = False, texture=None):
        super(GroundPlane, self).__init__(width, height, centered, texture)
        self.setCameraProjection(0)

    def _getVerts(self, width, height):
        v = super(GroundPlane, self)._getVerts(width, height)
        v = np.asarray(v, dtype=np.float32)
        v[:,:] = v[:, [0,2,1]]
        return v

    def move(self, dx, dy, dz):
        self.coord += (dx, dy, dz)
        self.markCoords(coor=True)
        self.update()

class BackPlane(GroundPlane):
    """
    Vertical plane.
    """
    def __init__(self, width, height, centered = False, texture=None):
        super(BackPlane, self).__init__(width, height, centered, texture)

    def _getVerts(self, width, height):
        return geometry3d.RectangleMesh._getVerts(self, width, height)

################################################################################

class FileSelectView(gui.Button):
    def __init__(self, buttonLabel):
        super(FileSelectView, self).__init__(buttonLabel)

        self.directory = os.getcwd()
        self.filter = ''

        self.connect(self, QtCore.SIGNAL('clicked(bool)'), self._browse)

    def setDirectory(self, directory):
        self.directory = directory

    def setFilter(self, filter):
        self.filter = gui.getLanguageString(filter)
        if '(*.*)' not in self.filter:
            self.filter = ';;'.join([self.filter, gui.getLanguageString('All Files')+' (*.*)'])

    def _browse(self, state = None):
        paths = gui.QtGui.QFileDialog.getOpenFileNames(gui3d.app.mainwin, gui.getLanguageString("Load BVH animation"), self.directory, self.filter)
        if not paths.isEmpty():
            paths = [unicode(filename) for filename in paths]
            self.callEvent('onFilesSelected', paths)


#### BodyParts #################################################################
import os

class BodyParts:
    def readVertexDefinitions(self):
        self.bodyparts = dict()    # List of all body part groups
        self.vertices = dict()     # Dict per vertgroup index, all vertex indices
        self.groups = dict()

        infile = open(DATA_PATH+"/vertgroup_mapping.txt", "r")
        lineCnt = 0
        for line in infile:
            lineCnt = lineCnt +1
            line = line.strip()
            # Ignore comments and empty lines
            if(not line or line.startswith("#")):
                continue
            # Define bodypart vertex group
            if(line.startswith("vertgroup")):
                items = line.split()
                try:
                    gIdx = int(items[1])
                    gName = items[2]
                    self.bodyparts[gIdx] = gName
                    continue
                except:
                    if WARNINGS:
                        log.warning("Warning: error at line "+str(lineCnt)+" of file "+ os.path.abspath(infile.name)+"!")
                    continue
            # Parse vertex - vertgroups assignment
            try:
                items = line.split()
                vertIdx = int(items[0])
                if(len(items) == 1):
                    if WARNINGS:
                        log.warning("Warning: vertex "+str(vertIdx)+" at line "+str(lineCnt)+" of file "+ os.path.abspath(infile.name)+" is not assigned to any vertex group!")
                    continue
                self.groups[vertIdx] = list()
                # Assign vertex groups
                for i in range(1,len(items)):
                    vGroupIdx = int(items[i])
                    if(vGroupIdx in self.vertices):
                        vList = self.vertices[vGroupIdx]
                    else:
                        vList = list()
                        self.vertices[int(vGroupIdx)] = vList
                    #print "Adding "+str(vertIdx)+" to group "+str(vGroupIdx)
                    vList.append(vertIdx)
                    self.groups[vertIdx].append(vGroupIdx)
            except:
                if WARNINGS:
                    log.warning("Warning: Parsing error at line "+str(lineCnt)+" of file "+ os.path.abspath(infile.name)+"!")

#### ColorMap ##################################################################

#TODO perhaps define in data file

colors = dict()

colors["FaceLT"] = [185, 59, 247]
colors["FaceRT"] = [10, 57, 141]
colors["FaceLB"] = [56, 181, 49]
colors["FaceRB"] = [72, 153, 52]
colors["Neck"] = [146, 169, 230]
colors["Lshoulder"] = [254, 254, 0]
colors["Rshoulder"] = [253, 53, 0]
colors["Lchest"] = [249, 175, 200]
colors["Rchest"] = [0, 197, 245]
colors["Larm"] = [106, 3, 13]
colors["Rarm"] = [91, 110, 218]
colors["Lelbow"] = [104, 122, 177]
colors["Relbow"] = [159, 125, 91]
colors["Lforearm"] = [166, 76, 156]
colors["Rforearm"] = [83, 2, 120]
colors["Lhand"] = [70, 87, 212]
colors["Rhand"] = [44, 166, 73]
colors["Lhips"] = [183, 197, 145]
colors["Rhips"] = [15, 165, 241]
colors["Lthigh"] = [126, 193, 252]
colors["Rthigh"] = [226, 155, 99]
colors["Lknee"] = [188, 206, 32]
colors["Rknee"] = [0, 88, 12]
colors["Lleg"] = [194, 245, 22]
colors["Rleg"] = [122, 90, 109]
colors["Lfoot"] = [20, 32, 48]
colors["Rfoot"] = [173, 113, 86]
colors["Background"] = [150, 57, 80]

################################################################################

category = None
taskview = None

def load(app):
    category = app.getCategory('People Export')
    taskview = category.addTask(PeopleExportTaskView(category))

    log.message('PCL/People loaded')

def unload(app):
    pass

