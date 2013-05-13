#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
**Project Name:**      MakeHuman

**Product Home Page:** http://www.makehuman.org/

**Code Home Page:**    http://code.google.com/p/makehuman/

**Authors:**           Marc Flerackers, Jonas Hauquier

**Copyright(c):**      MakeHuman Team 2001-2013

**Licensing:**         AGPL3 (see also http://www.makehuman.org/node/318)

**Coding Standards:**  See http://www.makehuman.org/node/165

Abstract
--------

Reusable BVH skeleton renderer extracted from bvh posing plugin
"""

import module3d, gui3d
import aljabr

import primitive_drawing


def drawBVHSkeleton(skeleton, human):
    bvhMesh = module3d.Object3D('bvhskeleton')
    bvhMesh.uvValues = []
    bvhMesh.indexBuffer = []

    _drawBVHJoint(skeleton.root, bvhMesh)

    bvhMesh.setCameraProjection(0)
    bvhMesh.setShadeless(0)
    bvhMesh.setSolid(0)
    bvhMesh.calcNormals()
    bvhMesh.updateIndexBuffer()

    bvhObject = gui3d.Object(aljabr.vadd(human.getPosition(), [0.0, 0.0, 0.0]), bvhMesh)
    bvhObject.setRotation(human.getRotation())

    return bvhObject


def _drawBVHJoint(joint, mesh):
    if joint.parent:
        position = joint.getPosition()
        parentPosition = joint.parent.getPosition()
        joint.p = primitive_drawing.addPrism(mesh, parentPosition, position, 'bone-' + joint.parent.name)
    
    for child in joint.children:
        _drawBVHJoint(child, mesh)


def updateSkeletonDrawing(skeleton, mesh):
    '''Works on bvh_importer.BVHSkeleton'''
    _updateJointDrawing(skeleton.root, mesh, 0)
    mesh.calcNormals()
    mesh.update()


def _updateJointDrawing(joint, mesh, index):
    if joint.parent:
        position = joint.getPosition()
        parentPosition = joint.parent.getPosition()
        primitive_drawing.updatePrism(mesh, parentPosition, position, index, joint.p)
        index += 6 # Each prism consists of 6 verts (assuming fixed joint order)
        
    for child in joint.children:
        index = _updateJointDrawing(child, mesh, index)
            
    return index
