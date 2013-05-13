#!/usr/bin/python
# -*- coding: utf-8 -*-

""" 
**Project Name:**      MakeHuman

**Product Home Page:** http://www.makehuman.org/

**Code Home Page:**    http://code.google.com/p/makehuman/

**Authors:**           Marc Flerackers

**Copyright(c):**      MakeHuman Team 2001-2013

**Licensing:**         AGPL3 (see also http://www.makehuman.org/node/318)

**Coding Standards:**  See http://www.makehuman.org/node/165

Abstract
--------

TODO
"""

import gui3d

def exportSkel(filename):

    human = gui3d.app.selectedHuman
    if not human.getSkeleton():
        gui3d.app.prompt('Error', 'You did not select a skeleton from the library.', 'OK')
        return

    f = open(filename, 'w')
    
    for bone in human.getSkeleton().getBones():
        writeBone(f, bone)
    
    f.close()

def writeBone(f, bone):

    if bone.parent:
        parentIndex = bone.parent.index
    else:
        parentIndex = -1

    position = bone.getRestHeadPos()
    f.write('%d %f %f %f %d\n' % (bone.index, position[0], position[1], position[2], parentIndex))

