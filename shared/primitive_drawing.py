#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
**Project Name:**      MakeHuman

**Product Home Page:** http://www.makehuman.org/

**Code Home Page:**    http://code.google.com/p/makehuman/

**Authors:**           Marc Flerackers, Jonas Hauquier

**Copyright(c):**      MakeHuman Team 2001-2012

**Licensing:**         GPL3 (see also http://sites.google.com/site/makehumandocs/licensing)

**Coding Standards:**  See http://sites.google.com/site/makehumandocs/developers-guide

Abstract
--------

Reusable primitive drawing extracted from bvh posing plugin
"""


import aljabr
from math import pi


def addPrism(mesh, o=[0.0, 0.0, 0.0], e=[0.0, 1.0, 0.0], name='prism'):
    fg = mesh.createFaceGroup(name)

    dir = aljabr.vsub(e, o) # direction vector from o to e
    if dir == [0.0, 0.0, 0.0]:
        dir = [0.0, 1.0, 0.0]
    len = aljabr.vlen(dir) # distance from o to e
    if len == 0:
        len = 1
    scale = 0.5 # the thickness is 10% of the length
    i = aljabr.vadd(o, aljabr.vmul(dir, 0.25)) # the thickest part is 25% from o
    n = aljabr.vmul(dir, 1.0 / len) # the normalized direction
    q = aljabr.axisAngleToQuaternion(n, pi / 2.0) # a quaternion to rotate the point p1 to obtain the other points
    p = p1 = aljabr.randomPointFromNormal(n) # a random point in the plane defined by 0,0,0 and n
    p1 = aljabr.vmul(aljabr.vnorm(p1), scale) # the point scaled to the thickness
    p2 = aljabr.quaternionVectorTransform(q, p1) # the other points
    p3 = aljabr.quaternionVectorTransform(q, p2)
    p4 = aljabr.quaternionVectorTransform(q, p3)
    
    p1 = aljabr.vadd(i, p1) # translate by i since we were working in the origin
    p2 = aljabr.vadd(i, p2)
    p3 = aljabr.vadd(i, p3)
    p4 = aljabr.vadd(i, p4)

    # The 6 vertices
    v = []
    v.append(mesh.createVertex(o))      # 0             0
    v.append(mesh.createVertex(p1))     # 1            /|\
    v.append(mesh.createVertex(p2))     # 2           /.2.\
    v.append(mesh.createVertex(p3))     # 3          1` | `3
    v.append(mesh.createVertex(p4))     # 4          \`.4.`/ 
    v.append(mesh.createVertex(e))      # 5           \ | /
                                        #              \|/
                                        #               5
    
    # The 8 faces
    fg.createFace((v[0], v[1], v[4], v[0]))
    fg.createFace((v[0], v[4], v[3], v[0]))
    fg.createFace((v[0], v[3], v[2], v[0]))
    fg.createFace((v[0], v[2], v[1], v[0]))
    fg.createFace((v[5], v[4], v[1], v[5]))
    fg.createFace((v[5], v[1], v[2], v[5]))
    fg.createFace((v[5], v[2], v[3], v[5]))
    fg.createFace((v[5], v[3], v[4], v[5]))
    
    return p


def updatePrism(mesh, o, e, index, p):
    dir = aljabr.vsub(e, o) # direction vector from o to e
    if dir == [0.0, 0.0, 0.0]:
        dir = [0.0, 1.0, 0.0]
    len = aljabr.vlen(dir) # distance from o to e
    if len == 0:
        len = 1
    scale = 0.5 # the thickness is 10% of the length
    i = aljabr.vadd(o, aljabr.vmul(dir, 0.25)) # the thickest part is 25% from o
    n = aljabr.vmul(dir, 1.0 / len) # the normalized direction
    q = aljabr.axisAngleToQuaternion(n, pi / 2.0) # a quaternion to rotate the point p1 to obtain the other points
    p1 = p # a random point in the plane defined by 0,0,0 and n
    p1 = aljabr.vmul(aljabr.vnorm(p1), scale) # the point scaled to the thickness
    p2 = aljabr.quaternionVectorTransform(q, p1) # the other points
    p3 = aljabr.quaternionVectorTransform(q, p2)
    p4 = aljabr.quaternionVectorTransform(q, p3)
    
    p1 = aljabr.vadd(i, p1) # translate by i since we were working in the origin
    p2 = aljabr.vadd(i, p2)
    p3 = aljabr.vadd(i, p3)
    p4 = aljabr.vadd(i, p4)

    # The 6 vertices
    mesh.verts[index].co = o
    mesh.verts[index+1].co = p1
    mesh.verts[index+2].co = p2
    mesh.verts[index+3].co = p3
    mesh.verts[index+4].co = p4
    mesh.verts[index+5].co = e


def addCube(mesh, position=[0.0, 0.0, 0.0], scale=1.0, name='cube'):
    fg = mesh.createFaceGroup(name)

    # The 8 vertices
    v = []
    v.append(mesh.createVertex(aljabr.vadd(position, [-scale, -scale, -scale]))) # 0         /0-----1\
    v.append(mesh.createVertex(aljabr.vadd(position, [scale, -scale, -scale])))  # 1        / |     | \
    v.append(mesh.createVertex(aljabr.vadd(position, [scale, scale, -scale])))   # 2       |4---------5|
    v.append(mesh.createVertex(aljabr.vadd(position, [-scale, scale, -scale])))  # 3       |  |     |  |
    v.append(mesh.createVertex(aljabr.vadd(position, [-scale, -scale, scale])))  # 4       |  3-----2  |  
    v.append(mesh.createVertex(aljabr.vadd(position, [scale, -scale, scale])))   # 5       | /       \ |
    v.append(mesh.createVertex(aljabr.vadd(position, [scale, scale, scale])))    # 6       |/         \|
    v.append(mesh.createVertex(aljabr.vadd(position, [-scale, scale, scale])))   # 7       |7---------6|
    
    # The 6 faces
    fg.createFace((v[4], v[5], v[6], v[7])) # front
    fg.createFace((v[1], v[0], v[3], v[2])) # back
    fg.createFace((v[0], v[4], v[7], v[3])) # left
    fg.createFace((v[5], v[1], v[2], v[6])) # right
    fg.createFace((v[0], v[1], v[5], v[4])) # top
    fg.createFace((v[7], v[6], v[2], v[3])) # bottom
