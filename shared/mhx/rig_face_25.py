#!/usr/bin/python
# -*- coding: utf-8 -*-

""" 
**Project Name:**      MakeHuman

**Product Home Page:** http://www.makehuman.org/

**Code Home Page:**    http://code.google.com/p/makehuman/

**Authors:**           Thomas Larsson

**Copyright(c):**      MakeHuman Team 2001-2013

**Licensing:**         AGPL3 (see also http://www.makehuman.org/node/318)

**Coding Standards:**  See http://www.makehuman.org/node/165

Abstract
--------

Face bone definitions 
"""


from .flags import *
from . import posebone
from posebone import addPoseBone

FaceJoints = [
    ('head-end',        'l', ((2.0, 'head'), (-1.0, 'neck'))),
    ('r-mouth',         'v', 2490),
    ('l-mouth',         'v', 8907),

    ('eyes',            'l', ((0.5, 'l-eye'), (0.5,'r-eye'))),
    ('gaze',            'o', ('eyes', (0,0,5))),
]

eyeOffs = (0,0,0.3)

FaceHeadsTails = [
    ('Jaw',                  'mouth', 'jaw'),
    ('TongueBase',           'tongue-1', 'tongue-2'),
    ('TongueMid',            'tongue-2', 'tongue-3'),
    ('TongueTip',            'tongue-3', 'tongue-4'),

    ('Eye_R',                'l-eye', ('l-eye', eyeOffs)),
    ('EyeParent_R',          'l-eye', ('l-eye', eyeOffs)),
    ('DfmUpLid_R',           'l-eye', 'l-upperlid'),
    ('DfmLoLid_R',           'l-eye', 'l-lowerlid'),
    
    ('Eye_L',                'r-eye', ('r-eye', eyeOffs)),
    ('EyeParent_L',          'r-eye', ('r-eye', eyeOffs)),
    ('DfmUpLid_L',           'r-eye', 'r-upperlid'),
    ('DfmLoLid_L',           'r-eye', 'r-lowerlid'),

    ('Eyes',                 'eyes', ('eyes', (0,0,1))),
    ('Gaze',                 'gaze', ('gaze', (0,0,1))),
    ('GazeParent',           'neck2', 'head-end'),
]


FaceArmature = [
    ('Jaw',              0, 'Head', F_DEF, L_HEAD, NoBB),
    ('TongueBase',       0, 'Jaw', F_DEF, L_HEAD, NoBB),
    ('TongueMid',        0, 'TongueBase', F_DEF, L_HEAD, NoBB),
    ('TongueTip',        0, 'TongueMid', F_DEF, L_HEAD, NoBB),
    ('GazeParent',       0, 'MasterFloor', 0, L_HELP, NoBB),
    ('Gaze',             pi, 'GazeParent', 0, L_HEAD, NoBB),
    ('Eyes',             0, 'Head', 0, L_HELP, NoBB),
    ('EyeParent_R',      0, 'Head', 0, L_HELP, NoBB),
    ('EyeParent_L',      0, 'Head', 0, L_HELP, NoBB),
    ('Eye_R',            0, 'EyeParent_R', F_DEF, L_HEAD+L_DEF, NoBB),
    ('Eye_L',            0, 'EyeParent_L', F_DEF, L_HEAD+L_DEF, NoBB),
    ('DfmUpLid_R',       0.279253, 'Head', F_DEF, L_DEF, NoBB),
    ('DfmLoLid_R',       0, 'Head', F_DEF, L_DEF, NoBB),
    ('DfmUpLid_L',       -0.279253, 'Head', F_DEF, L_DEF, NoBB),
    ('DfmLoLid_L',       0, 'Head', F_DEF, L_DEF, NoBB),
]


#
#    FaceControlPoses(fp, amt):
#

def FaceControlPoses(fp, amt):
    addPoseBone(fp, amt, 'Jaw', 'MHJaw', None, (1,1,1), (0,1,0), (1,1,1), (1,1,1), 0,
         [('LimitRot', C_OW_LOCAL, 1, ['LimitRot', (-5*D,45*D, 0,0, -20*D,20*D), (1,1,1)])])

    addPoseBone(fp, amt, 'TongueBase', None, None, (1,1,1), (0,1,0), (1,0,1), (1,1,1), 0, [])

    addPoseBone(fp, amt, 'TongueMid', None, None, (1,1,1), (0,1,0), (1,0,1), (1,1,1), 0, [])

    addPoseBone(fp, amt, 'TongueTip', None, None, (1,1,1), (0,1,0), (1,0,1), (1,1,1), 0, [])

    addPoseBone(fp, amt, 'Gaze', 'MHGaze', None, (0,0,0), (1,1,1), (0,1,1), (1,1,1), 0, [])

    addPoseBone(fp, amt, 'GazeParent', None, None, (0,0,0), (1,1,1), (1,1,1), (1,1,1), 0,
         [('CopyTrans', 0, 1, ['Head', 'Head', 0])])

    addPoseBone(fp, amt, 'DfmUpLid_R', None, None, (1,1,1), (0,1,1), (1,1,1), (1,1,1), 0, [])

    addPoseBone(fp, amt, 'DfmLoLid_R', None, None, (1,1,1), (0,1,1), (1,1,1), (1,1,1), 0, [])

    addPoseBone(fp, amt, 'DfmUpLid_L', None, None, (1,1,1), (0,1,1), (1,1,1), (1,1,1), 0, [])

    addPoseBone(fp, amt, 'DfmLoLid_L', None, None, (1,1,1), (0,1,1), (1,1,1), (1,1,1), 0, [])

    addPoseBone(fp, amt, 'Eyes', None, None, (1,1,1), (0,0,0), (1,1,1), (1,1,1), 0,
        [('IK', 0, 1, ['IK', 'Gaze', 1, None, (True, False,False), 1.0])])

    addPoseBone(fp, amt, 'Eye_R', 'MHCircle025', None, (1,1,1), (0,0,0), (1,1,1), (1,1,1), 0, [])

    addPoseBone(fp, amt, 'Eye_L', 'MHCircle025', None, (1,1,1), (0,0,0), (1,1,1), (1,1,1), 0, [])

    addPoseBone(fp, amt, 'EyeParent_L', None, None, (1,1,1), (0,0,0), (1,1,1), (1,1,1), 0, 
        [('CopyRot', C_LOCAL, 1, ['Eyes', 'Eyes', (1,1,1), (0,0,0), True])])

    addPoseBone(fp, amt, 'EyeParent_R', None, None, (1,1,1), (0,0,0), (1,1,1), (1,1,1), 0, 
        [('CopyRot', C_LOCAL, 1, ['Eyes', 'Eyes', (1,1,1), (0,0,0), True])])

    return

#
#    FaceDeformDrivers(fp, amt):
#

def FaceDeformDrivers(fp, amt):
    lidBones = [
    ('DfmUpLid_L', 'PUpLid_L', (0, 40*D)),
    ('DfmLoLid_L', 'PLoLid_L', (0, 20*D)),
    ('DfmUpLid_R', 'PUpLid_R', (0, 40*D)),
    ('DfmLoLid_R', 'PLoLid_R', (0, 20*D)),
    ]

    drivers = []
    for (driven, driver, coeff) in lidBones:
        drivers.append(    (driven, 'ROTQ', 'AVERAGE', None, 1, coeff,
         [("var", 'TRANSFORMS', [('OBJECT', amt.name, driver, 'LOC_Z', C_LOC)])]) )
    return drivers

#
#   FacePropDrivers
#   (Bone, Name, Props, Expr)
#

FacePropDrivers = []

SoftFacePropDrivers = [
    ('GazeParent', 'Head', ['GazeFollowsHead'], 'x1'),
]

