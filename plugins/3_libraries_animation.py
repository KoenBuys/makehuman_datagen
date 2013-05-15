#!/usr/bin/python
# -*- coding: utf-8 -*-

""" 
**Project Name:**      MakeHuman

**Product Home Page:** http://www.makehuman.org/

**Code Home Page:**    http://code.google.com/p/makehuman/

**Authors:**           Jonas Hauquier

**Copyright(c):**      MakeHuman Team 2001-2013

**Licensing:**         AGPL3 (see also http://www.makehuman.org/node/318)

**Coding Standards:**  See http://www.makehuman.org/node/165

Abstract
--------

Animation library.
A library of sets of animations to choose from that can be exported alongside
a MH model.
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

class AnimationAction(gui3d.Action):
    def __init__(self, name, library, add, anim):
        super(AnimationAction, self).__init__(name)
        self.library = library
        self.add = add
        self.anim = anim

    def do(self):
        if self.add:
            self.library.selectAnimation(self.anim)
        else:
            self.library.deselectAnimation(self.anim)
        return True

    def undo(self):
        if self.add:
            self.library.deselectAnimation(self.anim)
        else:
            self.library.selectAnimation(self.anim)
        return True

class AnimationCollection(object):
    def __init__(self, path):
        self.path = path
        self.uuid = None
        self.rig = None
        self.tags = set()
        self.animations = []
        self.scale = 1.0

    def getAnimation(self, name):
        for anim in self.animations:
            if anim.name == name:
                return anim

class Animation(object):
    def __init__(self, name):
        self.name = name
        self.bvh = None
        self.options = []
        self.collection = None

    def getPath(self):
        folder = os.path.dirname(self.collection.path)
        return os.path.join(folder, self.bvh)

    def getAnimationTrackName(self):
        return getAnimationTrackName(self.collection.uuid, self.name)

    def getAnimationTrack(self):
        """
        Retrieve animation track for this animation, cached in human.animated,
        or loads and caches it if it does not exist.
        """
        human = gui3d.app.selectedHuman
        if human.animated.hasAnimation(self.getAnimationTrackName()):
            return human.animated.getAnimation(self.getAnimationTrackName())
        else:
            animationTrack = loadAnimationTrack(self)
            if not animationTrack:
                return None
            human.animated.addAnimation(animationTrack)
            return animationTrack

class MhAnimLoader(filechooser.FileHandler):

    def __init__(self, animationChooser):
        self.animationChooser = animationChooser

    def refresh(self, files):
        self.animationChooser.clearAnimations()

        for filename in files:
            mhAnim = readAnimCollectionFile(filename)
            if mhAnim:
                for ani in mhAnim.animations:
                    # Add entry to animation chooser
                    item = self.fileChooser.addItem(file, ani.name, None, mhAnim.tags)
                    item.animId = (mhAnim.uuid, ani.name)
                # Add entry to animation chooser task
                self.animationChooser.addAnimationCollection(mhAnim)
            else:
                log.debug("Failed to parse mhanim file %s", filename)

    def getSelection(self, item):
        return item.animId

    def matchesItem(self, listItem, item):
        return listItem.animId == item

    def matchesItems(self, listItem, items):
        return listItem.animId in items

class AnimationLibrary(gui3d.TaskView):

    def __init__(self, category):
        gui3d.TaskView.__init__(self, category, 'Animations')

        self.systemAnims = os.path.join('data', 'animations')
        self.userAnims = os.path.join(mh.getPath(''), 'data', 'animations')
        self.animPaths = [self.userAnims, self.systemAnims]
        if not os.path.exists(self.userAnims):
            os.makedirs(self.userAnims)
        self.extension = "mhanim"

        # Test config param
        self.perFramePlayback = False   # Set to false to use time for playback

        self.interpolate = True     # Only useful when using time for playback

        self.skelMesh = None
        self.skelObj = None

        self.bvhRig = None
        self.animations = []
        self.anim = None
        self.animTrack = None
        self.collections = {}

        self.tags = set()

        self.oldSmoothValue = False

        self.lastSkeleton = None
        self.human = gui3d.app.selectedHuman
        self.oldHumanTransp = self.human.meshData.transparentPrimitives

        # Stores all selected animations and makes them available globally
        self.human.animations = []

        if not hasattr(self.human, 'animated'):
            self.human.animated = None

        self.timer = None
        self.currFrame = 0

        displayBox = self.addLeftWidget(gui.GroupBox('Display'))
        self.playbackBox = None
        self.frameSlider = None
        self.playPauseBtn = None
        self.animateInPlaceTggl = None

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

        self.createPlaybackControl()

        self.filechooser = self.addRightWidget(filechooser.ListFileChooser(self.animPaths, self.extension, 'Animations', True))

        self.filechooser.setFileLoadHandler(MhAnimLoader(self))
        self.addLeftWidget(self.filechooser.createSortBox())
        self.addLeftWidget(self.filechooser.createTagFilter())
        #self.update = self.filechooser.sortBox.addWidget(gui.Button('Check for updates'))
        self.mediaSync = None

        @self.filechooser.mhEvent
        def onFileHighlighted(animId):
            collectionUuid, animName = animId
            self.anim = self.getAnimation(collectionUuid, animName)
            self.highlightAnimation(self.anim)
            self.startPlayback()

        @self.filechooser.mhEvent
        def onFileSelected(animId):
            collectionUuid, animName = animId
            anim = self.getAnimation(collectionUuid, animName)
            gui3d.app.do(AnimationAction("Add animation",
                                        self,
                                        True,
                                        anim))

        @self.filechooser.mhEvent
        def onFileDeselected(animId):
            collectionUuid, animName = animId
            anim = self.getAnimation(collectionUuid, animName)
            gui3d.app.do(AnimationAction("Remove animation",
                                        self,
                                        False,
                                        anim))

    def clearAnimations(self):
        self.anim = None
        self.animTrack = None
        if self.human.animated:
            self.human.animated.removeAnimations()

    def addAnimationCollection(self, mhAnim):
        self.collections[mhAnim.uuid] = mhAnim
        self.tags = self.tags.union(mhAnim.tags)

    def getAnimation(self, uuid, animName):
        if not uuid in self.collections:
            log.error('No animation collection with UUID %s loaded.', uuid)
            return None
        collection = self.collections[uuid]
        anim = collection.getAnimation(animName)
        if not anim:
            log.error('No animation with name %s loaded in collection %s (%s).', animName, collection.path, uuid)
        return anim

    def loadAnimation(self, uuid, animName):
        if not human.getSkeleton():
            log.error("Cannot load animations when no skeleton is selected.")
            gui3d.app.statusPersist("Error: cannot load animations when no skeleton is selected.")
            return

        anim = self.getAnimation(uuid, animName)
        if not anim:
            log.error('Failed to load animation.')
            return

        self.selectAnimation(anim)
    
    def onShow(self, event):
        gui3d.TaskView.onShow(self, event)

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

        self.frameSlider.setValue(0)

        if self.anim:
            # Start playing previously highlighted animation
            self.highlightAnimation(self.anim)
            self.startPlayback()

        self.printAnimationsStatus()

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

    def createPlaybackControl(self):
        self.playbackBox = self.addRightWidget(gui.GroupBox('Playback'))
        self.frameSlider = self.playbackBox.addWidget(gui.Slider(value = 0, min = 0, max = 1, label = 'Frame: %d'))
        # TODO make slider use time instead of frames?
        @self.frameSlider.mhEvent
        def onChanging(value):
            self.updateAnimation(value)
        @self.frameSlider.mhEvent
        def onChange(value):
            self.updateAnimation(value)

        self.playPauseBtn = self.playbackBox.addWidget(gui.Button("Play"))
        @self.playPauseBtn.mhEvent
        def onClicked(value):
            if self.playPauseBtn.text() == 'Play':
                self.startPlayback()
            else:
                self.stopPlayback()

        self.animateInPlaceTggl = self.playbackBox.addWidget(gui.ToggleButton("In-place animation"))
        @self.animateInPlaceTggl.mhEvent
        def onClicked(event):
            self.human.animated.setAnimateInPlace(self.animateInPlaceTggl.selected)
            self.updateAnimation(self.currFrame)
        self.animateInPlaceTggl.setSelected(True)

        self.restPoseBtn = self.playbackBox.addWidget(gui.Button("Set to Rest Pose"))
        @self.restPoseBtn.mhEvent
        def onClicked(value):
            self.setToRestPose()

        self.interpolateTggl = self.playbackBox.addWidget(gui.ToggleButton("Interpolate animation"))
        @self.interpolateTggl.mhEvent
        def onClicked(event):
            self.interpolate = self.interpolateTggl.selected
        self.interpolateTggl.setSelected(True)

    def startPlayback(self):
        self.playPauseBtn.setText('Pause')
        if self.timer:
            mh.removeTimer(self.timer)
            self.timer = None
        if self.perFramePlayback:
            self.timer = mh.addTimer(max(30, int(1.0/self.animTrack.frameRate * 1000)), self.onFrameChanged)
        else: # 30 FPS fixed
            self.timer = mh.addTimer(30, self.onFrameChanged)

    def stopPlayback(self):
        if not self.playPauseBtn:
            return
        self.playPauseBtn.setText('Play')
        if self.timer:
            mh.removeTimer(self.timer)
            self.timer = None

    def setToRestPose(self):
        if not self.human.animated:
            return
        self.stopPlayback()
        self.human.animated.setToRestPose()

    def selectAnimation(self, anim):
        if not anim in self.human.animations:
            self.human.animations.append(anim)

        self.filechooser.selectItem( (anim.collection.uuid, anim.name) )
        self.printAnimationsStatus()

    def deselectAnimation(self, anim):
        try:
            self.human.animations.remove(anim)
        except:
            pass

        self.filechooser.deselectItem( (anim.collection.uuid, anim.name) )
        self.printAnimationsStatus()
        
    def printAnimationsStatus(self):
        nAnimations = len(self.human.animations)
        if nAnimations == 1:
            gui3d.app.statusPersist('1 animation selected')
        else:
            gui3d.app.statusPersist('%s animations selected' % nAnimations)

    def highlightAnimation(self, anim):
        self.stopPlayback()
        if not self.human.getSkeleton():
            return

        if self.filechooser.getHighlightedItem() != (anim.collection.uuid, anim.name):
            self.filechooser.setHighlightedItem((anim.collection.uuid, anim.name))

        if not self.human.animated.hasAnimation(anim.getAnimationTrackName()):
            # Load animation track (containing the actual animation data)
            # Actually loading the BVH is only necessary when previewing the
            # animation or exporting when the human is exported
            animationTrack = loadAnimationTrack(anim)
            if not animationTrack:
                return
            self.human.animated.addAnimation(animationTrack)

        self.anim = anim
        self.human.animated.setActiveAnimation(anim.getAnimationTrackName())
        self.animTrack = self.human.animated.getAnimation(anim.getAnimationTrackName())
        log.debug("Setting animation to %s", anim.name)

        self.human.animated.setAnimateInPlace(self.animateInPlaceTggl.selected)

        if self.frameSlider:
            self.frameSlider.setMin(0)
            maxFrame = self.animTrack.nFrames-1
            if maxFrame < 1:
                maxFrame = 1
            self.frameSlider.setMax(maxFrame)
            self.currFrame = 0
            self.frameSlider.setValue(0)
        self.updateAnimation(0)
        gui3d.app.redraw()

        self.startPlayback()

    def onFrameChanged(self):
        if not self.anim or not hasattr(self.human, 'animated') or not self.human.animated:
            return
        if self.perFramePlayback:
            frame = self.currFrame + 1
            if frame > self.frameSlider.max:
                frame = 0

            self.frameSlider.setValue(frame)
            self.updateAnimation(frame)
        else:
            self.human.animated.setActiveAnimation(self.animTrack.name)
            self.animTrack.interpolationType = 1 if self.interpolate else 0
            self.human.animated.update(1.0/30.0)
            frame = self.animTrack.getFrameIndexAtTime(self.human.animated.getTime())[0]
            self.frameSlider.setValue(frame)
            #self.updateProxies()
        gui3d.app.redraw()

    def updateAnimation(self, frame):
        if not self.anim or not self.human.getSkeleton():
            return
        self.currFrame = frame
        self.human.animated.setActiveAnimation(self.animTrack.name)
        self.animTrack.interpolationType = 1 if self.interpolate else 0
        self.human.animated.setToFrame(frame)
        #self.updateProxies()

    def setupProxySkinning(self):
        # Remove all meshes but the human and skeleton mesh from the animatedMesh object
        for mName in self.human.animated.getMeshes()[2:]:
            self.human.animated.removeMesh(mName)
            # TODO it's more optimized not to remove all proxy object meshes every time

        _, bodyWeights = self.human.animated.getMesh("base.obj")

        # Proxy mesh (always animate)
        if self.human.proxy and self.human.isProxied():
            weights = skeleton.getProxyWeights(self.human.proxy, bodyWeights, self.human.getProxyMesh())
            self.human.animated.addMesh(self.human.getProxyMesh(), weights)

        # Generate a vertex-to-bone mapping derived from that of the human for all proxy objects
        if self.skinProxiesTggl.selected:
            # Clothes
            for (name,obj) in self.human.clothesObjs.items():
                proxy = self.human.clothesProxies[name]
                weights = skeleton.getProxyWeights(proxy, bodyWeights, obj.mesh)
                self.human.animated.addMesh(obj.mesh, weights)
                obj.show()

            # Hair
            if self.human.hairObj and self.human.hairProxy:
                weights = skeleton.getProxyWeights(self.human.hairProxy, bodyWeights, self.human.hairObj.mesh)
                self.human.animated.addMesh(self.human.hairObj.mesh, weights)
                self.human.hairObj.show()
        else:
            # Hide not animated proxies (clothes and hair)
            for (name,obj) in self.human.clothesObjs.items():
                obj.hide()
            if self.human.hairObj:
                self.human.hairObj.hide()

    def updateProxies(self):
        """
        Apply animation (pose) on proxy objects (proxy mesh, clothes, hair)
        by fitting them to the basemesh (the slow way).
        It is faster to skin them along with the basemesh (by adding them to
        an animatedMesh object together with a vertex-bone mapping and weighting).
        """
        if self.human.proxy:
            self.human.updateProxyMesh()

        if self.human.hairObj and self.human.hairProxy:            
            mesh = self.human.hairObj.getSeedMesh()
            self.human.hairProxy.update(mesh)
            mesh.update()
            if self.human.hairObj.isSubdivided():
                self.human.hairObj.getSubdivisionMesh()

        for (name,clo) in self.human.clothesObjs.items():            
            if clo:
                mesh = clo.getSeedMesh()
                self.human.clothesProxies[name].update(mesh)
                mesh.update()
                if clo.isSubdivided():
                    clo.getSubdivisionMesh()

    def setHumanTransparency(self, enabled):
        if self.human.proxy and self.human.isProxied():
            if enabled:
                self.human.getProxyMesh().setTransparentPrimitives(len(self.human.getProxyMesh().fvert))
            else:
                self.human.getProxyMesh().setTransparentPrimitives(0)
        else:
            if enabled:
                self.human.meshData.setTransparentPrimitives(len(self.human.meshData.fvert))
            else:
                self.human.meshData.setTransparentPrimitives(self.oldHumanTransp)

    def loadHandler(self, human, values):
        if values[0] == "animations" and len(values) >= 3:
            uuid = values[1]
            animName = values[2]

            anim = self.getAnimation(uuid, animName)
            if not anim:
                log.error("Failed to load animation %s (%s).", anim.name, anim.collection.uuid)
                return
            self.selectAnimation(anim)

    def saveHandler(self, human, file):
        if self.human.animated and self.human.getSkeleton():
            for anim in self.human.animations:
                file.write('animations %s %s\n' % (anim.collection.uuid, anim.name))

    def onHumanRotated(self, event):
        if self.skelObj:
            self.skelObj.setRotation(gui3d.app.selectedHuman.getRotation())

    def onHumanTranslated(self, event):
        if self.skelObj:
            self.skelObj.setPosition(gui3d.app.selectedHuman.getPosition())

    def onHumanChanging(self, event):
        human = event.human
        if event.change == 'reset':
            self.stopPlayback()
            human.animations = []
            self.anim = None
            self.animTrack = None
            self.filechooser.deselectAll()

    def onMouseEntered(self, event):
        pass

    def onMouseExited(self, event):
        pass

def setColorForFaceGroup(mesh, fgName, color):
    color = np.asarray(color, dtype=np.uint8)
    mesh.color[mesh.getVerticesForGroups([fgName])] = color[None,:]
    mesh.markCoords(colr=True)
    mesh.sync_color()

def load(app):
    category = app.getCategory('Pose/Animate')
    taskview = AnimationLibrary(category)
    taskview.sortOrder = 3.5
    category.addTask(taskview)

    app.addLoadHandler('animations', taskview.loadHandler)
    app.addSaveHandler(taskview.saveHandler)

# This method is called when the plugin is unloaded from makehuman
# At the moment this is not used, but in the future it will remove the added GUI elements

def unload(app):
    pass

def readAnimCollectionFile(filename):
    """
    Parse a .mhanim file.
    """
    try:
        fh = open(filename, "rU")
    except:
        return None

    anims = AnimationCollection(filename)

    for line in fh:
        words = line.split()
        if len(words) == 0:
            pass

        elif words[0] == '#':
            if len(words) == 1:
                continue

            key = words[1]

            if key == 'uuid':
                anims.uuid = " ".join(words[2:])
            elif key == 'tag':
                anims.tags.add( " ".join(words[2:]) )
            elif key == 'rig':
                anims.rig = ( " ".join(words[2:]) )
            elif key == 'scale':
                anims.scale = float(words[2])
            elif key == 'anim':
                anim = Animation(name = words[2])
                anim.options = words[4:]
                anim.bvh = words[3]
                anim.collection = anims

                anims.animations.append(anim)
            else:
                # Unknown keyword
                pass
    return anims

def getAnimationTrackName(collectionUuid, animationName):
    return "%s_%s" % (collectionUuid, animationName)

def loadAnimationTrack(anim):
    """
    Load animation from a BVH file specified by anim.
    """
    if "z_is_up" in anim.options:
        swapYZ = True
    else:
        swapYZ = False

    human = gui3d.app.selectedHuman

    log.debug("Loading BVH %s", anim.getPath())

    # Load BVH data
    bvhRig = bvh.load(anim.getPath(), swapYZ)
    if anim.collection.scale != 1.0:
        # Scale rig
        bvhRig.scale(scale)
        # Scale is only useful when using the joint locations of the BVH rig
        # or when drawing the BVH rig.

    if human.getSkeleton().name == anim.collection.rig:
        # Skeleton and joint rig in BVH match, do a straight mapping of the
        # motion:

        # Load animation data from BVH file and add it to AnimatedMesh
        # This is a list that references a joint name in the BVH for each 
        # bone in the skeleton (breadth-first order):
        jointToBoneMap = [bone.name for bone in human.getSkeleton().getBones()]
        animTrack = bvhRig.createAnimationTrack(jointToBoneMap, anim.getAnimationTrackName())
        gui3d.app.statusPersist("")
    else:
        # Skeleton and joint rig in BVH are not the same, retarget/remap
        # the motion data:
        gui3d.app.statusPersist("Currently, animation are only working with soft1 rig, please choose the soft1 rig from the skeleton chooser.")
        return None

        if not os.path.isfile("tools/blender26x/mh_mocap_tool/target_rigs/%s.trg" % human.getSkeleton().name):
            gui3d.app.statusPersist("Cannot apply motion on the selected skeleton %s because there is no target mapping file for it.", human.getSkeleton().name)
            return None

        jointToBoneMap = skeleton.loadJointsMapping(human.getSkeleton().name, human.getSkeleton())
        animTrack = bvhRig.createAnimationTrack(jointToBoneMap, anim.getAnimationTrackName())

    log.debug("Created animation track for %s rig.", human.getSkeleton().name)
    log.debug("Frames: %s", animTrack.nFrames)
    log.debug("Playtime: %s", animTrack.getPlaytime())

    return animTrack

