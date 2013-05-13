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

Skeleton library.
Allows a selection of skeletons which can be exported with the MH character.
Skeletons are used for skeletal animation (skinning) and posing.
"""

# TODO add sort by number of bones

import gui3d
import mh
import gui
import module3d
import log
import filechooser as fc

import skeleton
import skeleton_drawing
import animation

import numpy as np
import os

class SkeletonAction(gui3d.Action):
    def __init__(self, name, library, before, after):
        super(SkeletonAction, self).__init__(name)
        self.library = library
        self.before = before
        self.after = after

    def do(self):
        self.library.chooseSkeleton(self.after)
        return True

    def undo(self):
        self.library.chooseSkeleton(self.before)
        return True

def _getSkeleton(self):
    if not self._skeleton:
        return None
    if self._skeleton.dirty:
        log.debug("Rebuilding skeleton.")
        # Rebuild skeleton (when human has changed)
        # Loads new skeleton, creates new skeleton mesh and new animatedMesh object (with up-to-date rest coords)
        self._skeleton._library.chooseSkeleton(self._skeleton.file)
        # TODO have a more efficient way of adapting skeleton to new joint positions without re-reading rig files
        # TODO Also, currently a tiny change in joints positions causes a new animatedMesh to be constructed, requiring all BVH motions to be reloaded (which is not necessary if the rig structure does not change). It should be enough to re-sync the rest coordinates in the animatedMesh and move the coord positions of the skeleton mesh.
        self._skeleton.dirty = False
    return self._skeleton

def _getVertexWeights(self):
    if not self.getSkeleton():
        return None
    if not self.animated:
        return None

    _, bodyWeights = self.animated.getMesh("base.obj")
    return bodyWeights

class SkeletonLibrary(gui3d.TaskView):

    def __init__(self, category):
        gui3d.TaskView.__init__(self, category, 'Skeleton')

        self.systemRigs = os.path.join('data', 'rigs')
        self.userRigs = os.path.join(mh.getPath(''), 'data', 'rigs')
        self.rigPaths = [self.userRigs, self.systemRigs]
        if not os.path.exists(self.userRigs):
            os.makedirs(self.userRigs)
        self.extension = "rig"

        self.human = gui3d.app.selectedHuman
        self.human._skeleton = None
        self.human.animated = None
        # Attach getter to human to access the skeleton, that takes care of deferred
        # updating when the skeleton should change
        import types
        self.human.getSkeleton = types.MethodType(_getSkeleton, self.human, self.human.__class__)
        self.human.getVertexWeights = types.MethodType(_getVertexWeights, self.human, self.human.__class__)

        self.oldSmoothValue = False

        self.humanChanged = False   # Used for determining when joints need to be redrawn

        self.skelMesh = None
        self.skelObj = None

        self.jointsMesh = None
        self.jointsObj = None

        self.selectedBone = None
        self.selectedJoint = None

        self.oldHumanTransp = self.human.meshData.transparentPrimitives

        self.filechooser = self.addRightWidget(fc.ListFileChooser(self.rigPaths, self.extension, 'Skeleton rig'))
        self.addLeftWidget(self.filechooser.createSortBox())

        @self.filechooser.mhEvent
        def onFileSelected(filename):
            if self.human.getSkeleton():
                oldSkelFile = self.human.getSkeleton().file
            else:
                oldSkelFile = None
            gui3d.app.do(SkeletonAction("Change skeleton",
                                        self,
                                        oldSkelFile,
                                        filename))

        @self.filechooser.mhEvent
        def onRefresh(fileChooser):
            noSkelPath = os.path.join(self.rigPaths[0], 'clear.rig')
            fileChooser.addItem(noSkelPath, 'No skeleton', None)
            if not self.human.getSkeleton():
                self.filechooser.selectItem(noSkelPath)

        self.filechooser.refresh()

        displayBox = self.addLeftWidget(gui.GroupBox('Display'))
        self.showHumanTggl = displayBox.addWidget(gui.ToggleButton("Show human"))
        @self.showHumanTggl.mhEvent
        def onClicked(event):
            if self.showHumanTggl.selected:
                self.human.show()
            else:
                self.human.hide()
        self.showHumanTggl.setSelected(True)

        self.showJointsTggl = displayBox.addWidget(gui.ToggleButton("Show joints"))
        @self.showJointsTggl.mhEvent
        def onClicked(event):
            if not self.jointsObj:
                return
            if self.showJointsTggl.selected:
                self.jointsObj.show()
            else:
                self.jointsObj.hide()
        self.showJointsTggl.setSelected(True)

        self.showWeightsTggl = displayBox.addWidget(gui.ToggleButton("Show bone weights"))
        @self.showWeightsTggl.mhEvent
        def onClicked(event):
            if self.showWeightsTggl.selected:
                # Highlight bone selected in bone explorer again
                for rdio in self.boneSelector:
                    if rdio.selected:
                        self.highlightBone(str(rdio.text()))
            else:
                self.clearBoneWeights()
        self.showWeightsTggl.setSelected(True)

        self.boneBox = self.addLeftWidget(gui.GroupBox('Bones'))
        self.boneSelector = []

        self.infoBox = self.addRightWidget(gui.GroupBox('Rig info'))
        self.boneCountLbl = self.infoBox.addWidget(gui.TextView('Bones: '))
        self.descrLbl = self.infoBox.addWidget(gui.TextView('Description: '))
        self.descrLbl.setSizePolicy(gui.QtGui.QSizePolicy.Ignored, gui.QtGui.QSizePolicy.Preferred)
        self.descrLbl.setWordWrap(True)

        self.rigDescriptions = { 
            "soft1":       "Soft skinned rig. Simple version of the MHX reference rig containing only its deforming bones.",
            "xonotic":     "Rig compatible with the open-source game Xonotic.",
            "second_life": "Rig compatible with Second Life.",
            "game":        "A simple rig with a minimal amount of bones. Has limited expressivity in hands and face.",
            "humanik":     "Rig compatible with the HumanIK software.",
            "rigid":       "Same as soft1 a simple version of the MHX reference rig, but with rigid weighting.",
        }

    def onShow(self, event):
        gui3d.TaskView.onShow(self, event)

        # Disable smoothing in skeleton library
        self.oldSmoothValue = self.human.isSubdivided()
        self.human.setSubdivided(False)

        self.oldHumanTransp = self.human.meshData.transparentPrimitives
        self.setHumanTransparency(True)
        self.human.meshData.setPickable(False)
        mh.updatePickingBuffer()

        if self.skelObj:
            self.skelObj.show()

        if not self.jointsObj:
            self.drawJointHelpers()

        self.filechooser.refresh()

        # Make sure skeleton is updated when human has changed
        self.human.getSkeleton()

        # Re-draw joints positions if human has changed
        if self.humanChanged:
            self.drawJointHelpers()
            self.humanChanged = False

    def onHide(self, event):
        gui3d.TaskView.onHide(self, event)

        if self.skelObj:
            self.skelObj.hide()
        self.setHumanTransparency(False)
        self.human.meshData.setPickable(True)
        mh.updatePickingBuffer()
        try:
            self.removeBoneHighlights()
        except:
            pass

        # Reset smooth setting
        self.human.setSubdivided(self.oldSmoothValue)

    def chooseSkeleton(self, filename):
        """
        Load skeleton from rig definition in a .rig file.
        """
        log.debug("Loading skeleton from rig file %s", filename)

        try:
            self.removeBoneHighlights()
        except:
            pass

        if not filename or os.path.basename(filename) == 'clear.rig':
            # Unload current skeleton
            self.human._skeleton = None
            self.human.animated = None
            if self.skelObj:
                # Remove old skeleton mesh
                gui3d.app.removeObject(self.skelObj)
                self.skelObj = None
                self.skelMesh = None
            self.filechooser.deselectAll()
            self.selectedBone = None
            self.reloadBoneExplorer()
            self.boneCountLbl.setText("Bones: ")
            self.descrLbl.setText("Description: ")
            self.filechooser.selectItem(os.path.join(self.rigPaths[0], 'clear.rig'))
            return

        # Load skeleton definition from .rig file
        self.human._skeleton, boneWeights = skeleton.loadRig(filename, self.human.meshData)

        # Store a reference to the currently loaded rig
        self.human._skeleton.file = filename
        self.human._skeleton.dirty = False   # Flag used for deferred updating
        self.human._skeleton._library = self  # Temporary member, used for rebuilding skeleton

        self.filechooser.selectItem(filename)

        # Created an AnimatedMesh object to manage the skeletal animation on the
        # human mesh and optionally additional meshes.
        # The animation manager object is accessible by other plugins via 
        # gui3d.app.currentHuman.animated.
        self.human.animated = animation.AnimatedMesh(self.human.getSkeleton(), self.human.meshData, boneWeights)

        # (Re-)draw the skeleton
        self.drawSkeleton(self.human.getSkeleton())

        self.reloadBoneExplorer()
        self.boneCountLbl.setText("Bones: %s" % self.human.getSkeleton().getBoneCount())
        if self.human.getSkeleton().name in self.rigDescriptions.keys():
            descr = self.rigDescriptions[self.human.getSkeleton().name]
        else:
            descr = "None available"
        self.descrLbl.setText("Description: %s" % descr)

    def drawSkeleton(self, skel):
        if self.skelObj:
            # Remove old skeleton mesh
            gui3d.app.removeObject(self.skelObj)
            self.skelObj = None
            self.skelMesh = None
            self.selectedBone = None

        # Create a mesh from the skeleton in rest pose
        skel.setToRestPose() # Make sure skeleton is in rest pose when constructing the skeleton mesh
        self.skelMesh = skeleton_drawing.meshFromSkeleton(skel, "Prism")
        self.skelMesh.priority = 100
        self.skelMesh.setPickable(True)
        mh.updatePickingBuffer()
        self.skelObj = gui3d.app.addObject(gui3d.Object(self.human.getPosition(), self.skelMesh) )
        self.skelObj.setRotation(self.human.getRotation())

        # Add the skeleton mesh to the human AnimatedMesh so it animates together with the skeleton
        # The skeleton mesh is supposed to be constructed from the skeleton in rest and receives
        # rigid vertex-bone weights (for each vertex exactly one weight of 1 to one bone)
        mapping = skeleton_drawing.getVertBoneMapping(skel, self.skelMesh)
        self.human.animated.addMesh(self.skelMesh, mapping)

        # Store a reference to the skeleton mesh object for other plugins
        self.human._skeleton.object = self.skelObj

        # Add event listeners to skeleton mesh for bone highlighting
        @self.skelObj.mhEvent
        def onMouseEntered(event):
            """
            Event fired when mouse hovers over a skeleton mesh facegroup
            """
            gui3d.TaskView.onMouseEntered(self, event)
            try:
                self.removeBoneHighlights()
            except:
                pass
            self.highlightBone(event.group.name)

        @self.skelObj.mhEvent
        def onMouseExited(event):
            """
            Event fired when mouse hovers off of a skeleton mesh facegroup
            """
            gui3d.TaskView.onMouseExited(self, event)
            try:
                self.removeBoneHighlights()
            except:
                pass

            # Highlight bone selected in bone explorer again
            for rdio in self.boneSelector:
                if rdio.selected:
                    self.clearBoneWeights()
                    self.highlightBone(str(rdio.text()))

    def highlightBone(self, name):
        # Highlight bones
        self.selectedBone = name
        setColorForFaceGroup(self.skelMesh, self.selectedBone, [216, 110, 39, 255])
        gui3d.app.statusPersist(name)

        # Draw bone weights
        if self.showWeightsTggl.selected:
            boneWeights = self.human.getVertexWeights()
            self.showBoneWeights(name, boneWeights)

        gui3d.app.redraw()

    def removeBoneHighlights(self):
        # Disable highlight on bone
        if self.selectedBone:
            setColorForFaceGroup(self.skelMesh, self.selectedBone, [255,255,255,255])
            gui3d.app.statusPersist('')

            self.clearBoneWeights()
            self.selectedBone = None

            gui3d.app.redraw()

    def drawJointHelpers(self):
        """
        Draw the joint helpers from the basemesh that define the default or
        reference rig.
        """
        if self.jointsObj:
            self.removeObject(self.jointsObj)
            self.jointsObj = None
            self.jointsMesh = None
            self.selectedJoint = None

        jointGroupNames = [group.name for group in self.human.meshData.faceGroups if group.name.startswith("joint-")]
        # TODO maybe define a getter for this list in the skeleton module
        jointPositions = []
        for groupName in jointGroupNames:
            jointPositions.append(skeleton.getHumanJointPosition(self.human.meshData, groupName))

        self.jointsMesh = skeleton_drawing.meshFromJoints(jointPositions, jointGroupNames)
        self.jointsMesh.priority = 100
        self.jointsMesh.setPickable(True)
        mh.updatePickingBuffer()
        self.jointsObj = self.addObject( gui3d.Object(self.human.getPosition(), self.jointsMesh) )
        self.jointsObj.setRotation(self.human.getRotation())

        color = np.asarray([255, 255, 0, 255], dtype=np.uint8)
        self.jointsMesh.color[:] = color[None,:]
        self.jointsMesh.markCoords(colr=True)
        self.jointsMesh.sync_color()

        # Add event listeners to joint mesh for joint highlighting
        @self.jointsObj.mhEvent
        def onMouseEntered(event):
            """
            Event fired when mouse hovers over a joint mesh facegroup
            """
            gui3d.TaskView.onMouseEntered(self, event)

            # Highlight joint
            self.selectedJoint = event.group
            setColorForFaceGroup(self.jointsMesh, self.selectedJoint.name, [216, 110, 39, 255])
            gui3d.app.statusPersist(event.group.name)
            gui3d.app.redraw()

        @self.jointsObj.mhEvent
        def onMouseExited(event):
            """
            Event fired when mouse hovers off of a joint mesh facegroup
            """
            gui3d.TaskView.onMouseExited(self, event)
            
            # Disable highlight on joint
            if self.selectedJoint:
                setColorForFaceGroup(self.jointsMesh, self.selectedJoint.name, [255,255,0,255])
                gui3d.app.statusPersist('')
                gui3d.app.redraw()

    def showBoneWeights(self, boneName, boneWeights):
        mesh = self.human.meshData
        try:
            weights = np.asarray(boneWeights[boneName][1], dtype=np.float32)
            verts = boneWeights[boneName][0]
        except:
            return
        red = np.maximum(weights, 0)
        green = 1.0 - red
        blue = np.zeros_like(red)
        alpha = np.ones_like(red)
        color = np.array([red,green,blue,alpha]).T
        color = (color * 255.99).astype(np.uint8)
        mesh.color[verts,:] = color
        mesh.markCoords(verts, colr = True)
        mesh.sync_all()

    def clearBoneWeights(self):
        mesh = self.human.meshData
        mesh.color[...] = (255,255,255,255)
        mesh.markCoords(colr = True)
        mesh.sync_all()

    def reloadBoneExplorer(self):
        # Remove old radio buttons
        for radioBtn in self.boneSelector:
            radioBtn.hide()
            radioBtn.destroy()
        self.boneSelector = []

        if not self.human.getSkeleton():
            return

        for bone in self.human.getSkeleton().getBones():
            radioBtn = self.boneBox.addWidget(gui.RadioButton(self.boneSelector, bone.name))
            @radioBtn.mhEvent
            def onClicked(event):
                for rdio in self.boneSelector:
                    if rdio.selected:
                        try:
                            self.removeBoneHighlights()
                        except:
                            pass
                        self.highlightBone(str(rdio.text()))

    def setHumanTransparency(self, enabled):
        if enabled:
            self.human.meshData.setTransparentPrimitives(len(self.human.meshData.fvert))
        else:
            self.human.meshData.setTransparentPrimitives(self.oldHumanTransp)

    def onHumanChanged(self, event):
        human = event.human
        # Set flag to do a deferred skeleton update in the future
        if human._skeleton:
            human._skeleton.dirty = True
        self.humanChanged = True    # Used for updating joints

    def onHumanChanging(self, event):
        human = event.human
        if event.change == 'reset':
            self.chooseSkeleton(None)

    def onHumanRotated(self, event):
        if self.skelObj:
            self.skelObj.setRotation(gui3d.app.selectedHuman.getRotation())
        if self.jointsObj:
            self.jointsObj.setRotation(gui3d.app.selectedHuman.getRotation())

    def onHumanTranslated(self, event):
        if self.skelObj:
            self.skelObj.setPosition(gui3d.app.selectedHuman.getPosition())
        if self.jointsObj:
            self.jointsObj.setPosition(gui3d.app.selectedHuman.getPosition())

    def loadHandler(self, human, values):
        if values[0] == "skeleton":
            skelFile = values[1]
            for path in self.rigPaths:
                skelPath = os.path.join(path, skelFile)
                if os.path.isfile(skelPath):
                    self.chooseSkeleton(skelPath)
                    return
            log.warn("Could not load rig %s, file does not exist." % skelFile)

        # Make sure no skeleton is drawn
        if self.skelObj:
            self.skelObj.hide()

    def saveHandler(self, human, file):
        if human.getSkeleton():
            file.write('skeleton %s ' % os.path.basename(human.getSkeleton().file))


def load(app):
    category = app.getCategory('Pose/Animate')
    taskview = SkeletonLibrary(category)
    taskview.sortOrder = 3
    category.addTask(taskview)

    human = gui3d.app.selectedHuman
    app.addLoadHandler('skeleton', taskview.loadHandler)
    app.addSaveHandler(taskview.saveHandler)

# This method is called when the plugin is unloaded from makehuman
# At the moment this is not used, but in the future it will remove the added GUI elements
def unload(app):
    pass


def setColorForFaceGroup(mesh, fgName, color):
    color = np.asarray(color, dtype=np.uint8)
    mesh.color[mesh.getVerticesForGroups([fgName])] = color[None,:]
    mesh.markCoords(colr=True)
    mesh.sync_color()
