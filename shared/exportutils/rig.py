#!/usr/bin/python
# -*- coding: utf-8 -*-

""" 
**Project Name:**     MakeHuman

**Product Home Page:** http://www.makehuman.org/

**Code Home Page:** http://code.google.com/p/makehuman/

**Authors:**           Thomas Larsson

**Copyright(c):**     MakeHuman Team 2001-2013

**Licensing:**       AGPL3 (see also http://www.makehuman.org/node/318)

**Coding Standards:**  See http://www.makehuman.org/node/165

Abstract
--------
Read rig file

TODO
"""

import numpy as np
import os
import mh2proxy
import log


#
#   setupRigJoint (words, obj, coord, locations):
#
def setupRigJoint (words, obj, coord, locations):
    key = words[0]
    typ = words[1]
    if typ == 'joint':
        locations[key] = mh2proxy.calcJointPos(obj, words[2])
    elif typ == 'vertex':
        vn = int(words[2])
        locations[key] = obj.coord[vn]
    elif typ == 'position':
        x = locations[int(words[2])]
        y = locations[int(words[3])]
        z = locations[int(words[4])]
        locations[key] = np.array((x[0],y[1],z[2]))
    elif typ == 'line':
        k1 = float(words[2])
        vn1 = int(words[3])
        k2 = float(words[4])
        vn2 = int(words[5])
        locations[key] = k1*locations[vn1] + k2*locations[vn2]
    elif typ == 'offset':
        vn = int(words[2])
    	x = float(words[3])
    	y = float(words[4])
    	z = float(words[5])
        locations[key] = locations[vn] + np.array((x,y,z))
    elif typ == 'voffset':
        vn = int(words[2])
    	x = float(words[3])
    	y = float(words[4])
    	z = float(words[5])
        try:
            loc = obj.coord[vn]
        except:
            loc = coord[vn]         
        locations[key] = loc + np.array((x,y,z))
    elif typ == 'front':
        raw = locations[words[2]]
        head = locations[words[3]]
        tail = locations[words[4]]
        offs = map(float, words[5].strip().lstrip('[').rstrip(']').split(','))
        offs = np.array(offs)
        vec =  tail - head
        vraw = raw - head
        x = np.dot(vec,vraw) / np.dot(vec, vec)
        locations[key] = head + x*vec + offs
    else:
        raise NameError("Unknown %s" % typ)

#
#   readRigFile(filename, obj, coord=None, locations={}):
#

def readRigFile(filename, obj, coord=None, locations={}):
    if type(filename) == tuple:
        (folder, fname) = filename
        filename = os.path.join(folder, fname)
    path = os.path.realpath(os.path.expanduser(filename))
    try:
        fp = open(path, "rU")
    except:
        log.error("*** Cannot open %s" % path)
        return

    doLocations = 1
    doBones = 2
    doWeights = 3
    status = 0

    armature = []
    weights = {}

    if not coord:
        coord = obj.coord
    for line in fp: 
        words = line.split()
        if len(words) == 0:
            pass
        elif words[0] == '#':
            if words[1] == 'locations':
                status = doLocations
            elif words[1] == 'bones':
                status = doBones
            elif words[1] == 'weights':
                status = doWeights
                wts = []
                weights[words[2]] = wts
        elif status == doWeights:
            wts.append((int(words[0]), float(words[1])))
        elif status == doLocations:
            setupRigJoint (words, obj, coord, locations)
        elif status == doBones:
            bone = words[0]
            head = locations[words[1]]
            tail = locations[words[2]]
            roll = float(words[3])
            parent = words[4]
            options = {}
            for word in words[5:]:
                try:
                    float(word)
                    values.append(word)
                    continue
                except:
                    pass
                if word[0] == '-':
                    values = []
                    options[word] = values
                else:
                    values.append(word)
            armature.append((bone, head, tail, roll, parent, options))
        else:
            raise NameError("Unknown status %d" % status)

    fp.close()
    return (locations, armature, weights)

