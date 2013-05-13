#!/usr/bin/python
# -*- coding: utf-8 -*-

""" 
Skeleton structure.

**Project Name:**      MakeHuman

**Product Home Page:** http://www.makehuman.org/

**Code Home Page:**    http://code.google.com/p/makehuman/

**Authors:**           Marc Flerackers, Jonas Hauquier

**Copyright(c):**      MakeHuman Team 2001-2012

**Licensing:**         GPL3 (see also http://sites.google.com/site/makehumandocs/licensing)

**Coding Standards:**  See http://sites.google.com/site/makehumandocs/developers-guide

Abstract
--------

Generic re-useable skeleton structure with drawing funcions

"""

from aljabr import vadd, vsub, vlen, vmul, centroid, vcross, vdot, vnorm, axisAngleToQuaternion, makeUnit, makeScale, makeTranslation, mmul, euler2matrix, invTransform, _transpose, degree2rad
from math import acos, pi, cos, sin, radians

import module3d, gui3d

import primitive_drawing

from numpy import array, dot


def fromBvhSkeleton(bvhSkeleton, human):
    '''Create a generic skeleton from a bvh_importer.bvhSkeleton'''
    skeleton = Skeleton(human)
    bvhSkeleton.updateFrame(-1) # Put BVH file in rest pose
    _fromBvhJoint(skeleton.root, bvhSkeleton.root)
    skeleton.updateFrame(-1)    # Put created rig in rest pose
    return skeleton


def _fromBvhJoint(genericSkeletonJoint, joint):
    if not joint.parent:
        # Replace the generic skeleton root bone
        newJoint = genericSkeletonJoint
        newJoint.roll = 0
        newJoint.name = joint.name
    else:
        # Create a new child bone
        newJoint = genericSkeletonJoint.addJoint(joint.parent.name, 0)
        
    #newJoint.position = joint.getPosition()  # absolute position

    newJoint.length = vlen(joint.offset)
    newJoint.offset = joint.offset           # position relative to parent
    newJoint.roll = 0

    # Copy animation data
    for frame in joint.frames:
        Rxyz = [0.0, 0.0, 0.0]
        Txyz = [0.0, 0.0, 0.0]
        rOrder = ""
        for index, channel in enumerate(joint.channels):
            if channel == 'Xposition':
                Txyz[0] = frame[index]
            elif channel == 'Yposition':
                Txyz[1] = frame[index]
            elif channel == 'Zposition':
                Txyz[2] = frame[index]

            # Rotation channels are swapped to proper XYZ order
            if channel == 'Xrotation':
                Rxyz[0] = frame[index]# * degree2rad
                rOrder = rOrder + "x"
            elif channel == 'Yrotation':
                Rxyz[1] = frame[index]# * degree2rad
                rOrder = rOrder + "y"
            elif channel == 'Zrotation':
                Rxyz[2] = frame[index]# * degree2rad
                rOrder = rOrder + "z"
        newJoint.addFrame(Rxyz, Txyz, rOrder)

    # Recurse over children
    for child in joint.children:
        _fromBvhJoint(newJoint, child)


# TODO should actually be a bone, not a joint
# TODO clean up unused members
class Joint:

    def __init__(self, name, skeleton, children):
        self.name = name
        self.skeleton = skeleton
        self.parent = None
        self.children = children
        self.offset = [0.0, 0.0, 0.0]  # Position Relative to the parent joint
        #self.position = [0.0, 0.0, 0.0]# absolute world position of head joint
        #euler rotation. order is plugin dependent
        self.rotation = [0.0, 0.0, 0.0]
        self.length = 0	# bone length
        self.transform = makeUnit()
        self.normalTransform = makeUnit()
        #limits same order as rotation
        self.limits = [[-180,180],[-180,180],[-180,180]]
        self.radius = 0

        self._draw = True

        self.roll = 0

        self.stransmat = None   # static rest pose world transformation mat
        self.worldpos = None    # animation world position
        self.worldposrot = None # animation world pos transf mat for children

        # List containing [0] rotation and [1] translation vectors 
        # for each frame (rotation is in regular xyz order)
        self.frames = [] 
        
        for child in children:
            child.parent = self


    def addJoint(self, name, roll):
        joint = Joint(name, self.skeleton, [])
        joint.parent = self
        joint.roll = roll
        self.children.append(joint)
        return joint


    def addFrame(self, rotation, translation, rotOrder):
        self.frames.append([rotation, translation, rotOrder])


    def scale(self, scale):
        #self.position = vmul(self.position, scale)
        #self.tail = vmul(self.tail, scale)
        self.length = self.length * scale
        self.offset = vmul(self.offset, scale)
        self.calcTransform()

        for child in self.children:
            child.scale(scale)


    def getBones(self):
        result = list()

        if self.parent:
            result.append(self)

        for child in self.children:
            result.extend(child.getBones())

        return result


    def canonalizeNames(self):
        self.name = self.name.lower().replace(' ','_').replace('-','_')
        for child in self.children:
            child.canonalizeNames()


    # TODO calculate static transformation some place else and execute it after skeleton creation
    def updateFrame(self, frame, inPlace=False, scale=1):
        # Calculate (static) local rest position transformation
        # TODO this only has to be calculated once
        self.stransmat = array([ [1.,0.,0.,self.offset[0]],
                                 [0.,1.,0.,self.offset[1]],
                                 [0.,0.,1.,self.offset[2]],
                                 [0.,0.,0.,1.] ])

        # Build a translation matrix for this keyframe
        dtransmat = array([ [1.,0.,0.,0.],[0.,1.,0.,0.],[0.,0.,1.,0.],[0.,0.,0.,1.] ])

        # Build up drotmat one rotation at a time so that matrix
        # multiplication order is correct.
        drotmat = array([ [1.,0.,0.,0.],[0.,1.,0.,0.],[0.,0.,1.,0.],[0.,0.,0.,1.] ])

        # Apply dynamic pose animation data
        if frame >= 0 and frame < len(self.frames):
            # Dynamic translation
            # Position (usually only for root bone)
            if inPlace:
                Txyz = [0.0, 0.0, 0.0]
            else:
                Txyz = self.frames[frame][1]
            # scale translation
            Txyz[0] = Txyz[0] * scale
            Txyz[1] = Txyz[1] * scale
            Txyz[2] = Txyz[2] * scale

            dtransmat[0,3] = Txyz[0]
            dtransmat[1,3] = Txyz[1]
            dtransmat[2,3] = Txyz[2]

            # Dynamic rotation
            Rxyz = self.frames[frame][0]

            # Maintain correct rotation order
            rOrder = self.frames[frame][2]
            for r in rOrder:
                if r == 'x':
                    xrot = Rxyz[0]
                    theta = radians(xrot)
                    mycos = cos(theta)
                    mysin = sin(theta)
                    drotmat2 = array([ [1.,0.,0.,0.],[0.,1.,0.,0.],[0.,0.,1.,0.], [0.,0.,0.,1.] ])
                    drotmat2[1,1] = mycos
                    drotmat2[1,2] = -mysin
                    drotmat2[2,1] = mysin
                    drotmat2[2,2] = mycos
                    drotmat = dot(drotmat, drotmat2)

                if r == 'y':
                    yrot = Rxyz[1]
                    theta = radians(yrot)
                    mycos = cos(theta)
                    mysin = sin(theta)
                    drotmat2 = array([ [1.,0.,0.,0.],[0.,1.,0.,0.],[0.,0.,1.,0.], [0.,0.,0.,1.] ])
                    drotmat2[0,0] = mycos
                    drotmat2[0,2] = mysin
                    drotmat2[2,0] = -mysin
                    drotmat2[2,2] = mycos
                    drotmat = dot(drotmat, drotmat2)

                if r == 'z':
                    zrot = Rxyz[2]
                    theta = radians(zrot)
                    mycos = cos(theta)
                    mysin = sin(theta)
                    drotmat2 = array([ [1.,0.,0.,0.],[0.,1.,0.,0.],[0.,0.,1.,0.], [0.,0.,0.,1.] ])
                    drotmat2[0,0] = mycos
                    drotmat2[0,1] = -mysin
                    drotmat2[1,0] = mysin
                    drotmat2[1,1] = mycos
                    drotmat = dot(drotmat, drotmat2)

        # Calculate complete worldspace position
        # Only add transformation on root bone
        # TODO we can change this
        if self.parent:
            localtoworld = dot(self.parent.worldposrot, self.stransmat)
        else:
            localtoworld = dot(self.stransmat, dtransmat)

        # Add rotation of this joint to stack to use for determining
        # children positions.
        # Note that position of this joint is not affected by its rotation
        self.worldposrot = dot(localtoworld, drotmat)

        # Position is the translation part of the mat (fourth column)
        self.worldpos = array([ localtoworld[0][3],
                                localtoworld[1][3],
                                localtoworld[2][3], 
                                localtoworld[3][3] ])

        for child in self.children:
            child.updateFrame(frame, inPlace, scale)


    @property
    def direction(self):
        direction = vnorm(self.offset)
        axis = vnorm(vcross([0.0, 0.0, 1.0], direction))
        angle = acos(vdot([0.0, 0.0, 1.0], direction))
        return axisAngleToQuaternion(axis, angle)
    

    def calcTransform(self, recursive=True):
        # TODO 
        pass


    def getPosition(self):
        return [self.worldpos[0], self.worldpos[1], self.worldpos[2]]


    def draw(self, skeletonMesh):
        # Draw self
        if self.parent and self._draw:
            self.p = primitive_drawing.addPrism(skeletonMesh, self.parent.getPosition(), self.getPosition(), 'bone-' + self.name)

        # Draw children
        for c in self.children:
            c.draw(skeletonMesh)

    def updateDrawing(self, skeletonMesh, index):
        if self.parent and self._draw:
            primitive_drawing.updatePrism(skeletonMesh, self.parent.getPosition(), self.getPosition(), index, self.p)
            index += 6 # Each prism consists of 6 verts (assuming fixed joint order)
            self.p = primitive_drawing.addPrism(skeletonMesh, self.parent.getPosition(), self.getPosition(), 'bone-' + self.name)

        # Draw children
        for child in self.children:
            index = child.updateDrawing(skeletonMesh, index)

        return index


class Skeleton:
    
    def __init__(self, human):
        self.human = human
        self.root = Joint("_Root_", self, [])
        self.currentFrame = -1
        self._scale = 1


    def draw(self):
        skeletonMesh = module3d.Object3D('skeleton')
        skeletonMesh.uvValues = []
        skeletonMesh.indexBuffer = []

        self.root.draw(skeletonMesh)

        skeletonMesh.setCameraProjection(0)
        skeletonMesh.setShadeless(0)
        skeletonMesh.setSolid(0)
        skeletonMesh.calcNormals()
        skeletonMesh.updateIndexBuffer()

        skeletonObject = gui3d.Object(vadd(self.human.getPosition(), [0.0, 0.0, 0.0]), skeletonMesh)
        skeletonObject.mesh.setCameraProjection(0)
        skeletonObject.setRotation(self.human.getRotation())
        return skeletonObject


    def updateDrawing(self, skeletonMesh):
        self.root.updateDrawing(skeletonMesh, 0)
        skeletonMesh.calcNormals()
        skeletonMesh.update()


    def scale(self, scale):
        self._scale = scale
        self.root.scale(scale)


    def getBones(self):
        return self.root.getBones()


    def canonalizeNames(self):
        self.root.canonalizeNames()


    def calcTransform(self):
        self.root.calcTransform()

            
    def update(self, mesh):
        self.__calcJointOffsets(mesh, self.root)
        #self.root.calcInverseTransform()

        
    def getJoint(self, name):
        return self.__getJoint(self.root, name)

            
    def __getJoint(self, joint, name):
        if joint.name == name:
            return joint
            
        for child in joint.children:
            j = self.__getJoint(child, name)
            if j:
                return j
                
        return None

    def updateFrame(self, frame, inPlace = False):
        self.root.updateFrame(frame, inPlace, self._scale)
        self.currentFrame = frame


    def __calcJointOffsets(self, mesh, joint, parent=None):
        """
        This function calculates the position and offset for a joint and calls itself for 
        each 'child' joint in the hierarchical joint structure. 
        
        Parameters
        ----------
        
        mesh:     
          *Object3D*.  The object whose information is to be used for the calculation.
        joint:     
          *Joint Object*.  The joint object to be processed by this function call.
        parent:     
          *Joint Object*.  The parent joint object or 'None' if not specified.
        """
        # Calculate joint positions
        g = mesh.getFaceGroup(joint.name)
        verts = []
        for f in g.faces:
            for v in f.verts:
                verts.append(v.co)
        joint.position = centroid(verts)
        joint.transform[3], joint.transform[7], joint.transform[11] = joint.position

        # Calculate offset
        if parent:
            joint.offset = vsub(joint.position, parent.position)
        else:
            joint.offset = joint.position[:]
            
        """
        # Calculate direction
        direction = vnorm(joint.offset)
        axis = vnorm(vcross([0.0, 0.0, 1.0], direction))
        angle = acos(vdot([0.0, 0.0, 1.0], direction))
        joint.direction = axisAngleToQuaternion(axis, angle)
        
        # Calculate rotation
        if parent:
            v1 = vmul(vnorm(parent.offset), -1.0)
            v2 = vnorm(joint.offset)
            axis = vnorm(vcross(v1, v2))
            angle = acos(vdot(v1, v2))
            joint.rotation = axisAngleToQuaternion(axis, angle)   
        """
        # Update counters and set index
        joint.index = self.joints
        self.joints += 1
        if not joint.children:
            self.endEffectors += 1

        # Calculate child offsets
        for child in joint.children:
            self.__calcJointOffsets(mesh, child, joint)

