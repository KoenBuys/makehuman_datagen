#!/usr/bin/python
# -*- coding: utf-8 -*-

""" 
Skeleton structure.

**Project Name:**      MakeHuman

**Product Home Page:** http://www.makehuman.org/

**Code Home Page:**    http://code.google.com/p/makehuman/

**Authors:**           Thomas Larsson, Jonas Hauquier

**Copyright(c):**      MakeHuman Team 2001-2012

**Licensing:**         GPL3 (see also http://sites.google.com/site/makehumandocs/licensing)

**Coding Standards:**  See http://sites.google.com/site/makehumandocs/developers-guide

Abstract
--------

Tools for retargeting BVH files to the MHX rig without the need of Blender

"""

import mhx_globals as the   # TODO can also be from . import globvar as the
import os
import math
from math import pi, atan
import aljabr

# From MH later than alpha 7
#from warp import numpy
#if numpy:
#    import transformations as tm


Deg2Rad = math.pi/180
D = 180/math.pi


sourcesInited = False

reverseMapping = None


def simpleRetarget(sourceRig, targetRig, boneMapping):
    for (srcBone, (tgtBone, rollAngle)) in boneMapping.items():
        #if tgtBone != "UpLeg_L" and tgtBone != "Hip_L":
        #    continue
        if not tgtBone:
            continue
        #rollAngle = the.srcArmature[srcBone][1]
        srcJoint = sourceRig.getJoint(srcBone)
        tgtJoint = targetRig.getJoint(tgtBone)
        if not tgtJoint:
            continue
        #print "For mapping %s => %s got joints %s and %s" % (srcBone, tgtBone, srcJoint, tgtJoint)
        # Easiest retarget possible
        tgtJoint.frames = srcJoint.frames

        '''
        parent = srcJoint.parent
        while parent and (parent.name not in boneMapping.keys() or
         not boneMapping[parent.name][0]):
            print "remapping %s" % parent.name
            for (idx, tgtFrame) in enumerate(tgtJoint.frames):
                srcPFrame = parent.frames[idx]
                # TODO we assume rotation order is identical for all joints in src rig
                # TODO currently we only apply rotation, not translation
                tgtFrame[0][0] = tgtFrame[0][0] + srcPFrame[0][0]
                tgtFrame[0][1] = tgtFrame[0][1] + srcPFrame[0][1]
                tgtFrame[0][2] = tgtFrame[0][2] + srcPFrame[0][2]
                print "adding (%s, %s, %s)" % (srcPFrame[0][0], srcPFrame[0][1], srcPFrame[0][2])
            parent = parent.parent
        '''


# In the blender script, a mapping srcRig <> MHX rig <> trgRig is used
# Here we only use the MHX rig as target

def renameAndRescaleBVH(srcRig, tgtRig):
    '''Prepare source rig in a state where it is comparable
    with the target rig to allow retargeting.'''
    ##target.getTargetArmature(trgRig, scn)     This is the MHX rig
    findSrcArmature(srcRig)     # Detect format of source rig
    renameBones(srcRig, scn)
    #utils.setInterpolation(srcRig)  # TODO this is using a blender-specific implementation
    rescaleRig(context.scene, tgtRig, srcRig)


def initSources():       
    the.sourceArmatures = {}
    path = os.path.join(os.path.dirname(__file__), "../tools/blender26x/mh_mocap_tool/source_rigs")
    for fname in os.listdir(path):
        file = os.path.join(path, fname)
        (name, ext) = os.path.splitext(fname)
        if ext == ".src" and os.path.isfile(file):
            (name, armature) = readSrcArmature(file, name)
            the.sourceArmatures[name] = armature
    the.srcArmatureEnums = []
    keys = list(the.sourceArmatures.keys())
    keys.sort()
    for key in keys:
        the.srcArmatureEnums.append((key,key,key))

    # Reference:    # TODO remove
    '''
    bpy.types.Scene.McpSourceRig = EnumProperty(
        items = the.srcArmatureEnums,
        name = "Source rig",
        default = 'MB')
    scn.McpSourceRig = 'MB'
    print("Defined McpSourceRig")
    '''
    return    


def readSrcArmature(file, name):
    '''Read source armature definition from .src file.'''
    print("Reading source file", file)
    fp = open(file, "r")
    status = 0    
    armature = {}
    for line in fp:
        words = line.split()
        if len(words) > 0:
            key = words[0].lower()
            if key[0] == "#":
                continue
            elif key == "name:":
                name = words[1]
            elif key == "armature:":
                status = 1
            elif len(words) < 3:
                print("Ignored illegal line", line)
            elif status == 1:
                for n in range(1,len(words)-2):
                    key += "_" + words[n]                    
                armature[canonicalSrcName(key)] = (nameOrNone(words[-2]), float(words[-1]))
    fp.close()                
    return (name, armature)


def nameOrNone(string):
    if string == "None":
        return None
    else:
        return string           


def findSrcArmature(rig):
    # TODO pretty useless function...
    global sourcesInited

    if not sourcesInited:
        initSources()
        sourcesInited = True

    (the.srcArmature, name) = guessSrcArmature(rig)
    # manual way: the.srcArmature = the.sourceArmatures[name]
    print("Using matching armature %s." % name)
    return


def guessSrcArmature(rig):
    '''Guess the corresponding source rig definition for a rig,
    based on the number of matching bone names. A matching
    source definition should contain all bones of the rig.
    Matching only uses bone names, and doesn't compare eg.
    rest poses.'''
    bestMisses = 1000
    misses = {}
    bones = rig.getBones()
    # Try all possible source rig definitions
    for name in the.sourceArmatures.keys():
        amt = the.sourceArmatures[name]
        nMisses = 0
        # Count the number of matching bones on source rig
        for bone in bones:
            try:
                amt[canonicalSrcName(bone.name)]
            except:
                nMisses += 1
        misses[name] = nMisses
        if nMisses < bestMisses:
            best = amt
            bestName = name
            bestMisses = nMisses
    # The best rig has no missing bones
    if bestMisses == 0:
        print "Perfect match found for source armature."
    # If there are missing bones
    else:
        #print "Bones:"
        #for bone in bones:
        #    print("'%s'" % bone.name)
        print "Misses:"
        for (name, n) in misses.items():
            print(name, n)
        #raise Exception('Did not find matching armature. nMisses = %d of %d bones total' % (bestMisses, len(bones)))
        print 'Best found source armature is %s (matched %d of %d bones total)' % (bestName, len(bones)-bestMisses, len(bones))
        if bestMisses > 0:
            print "WARINING: not all bones were matched!"
        
    return (best, bestName)


def canonicalSrcName(string):
    return string.lower().replace(' ','_').replace('-','_')


def getTargetFromSource(srcName):
    '''Get target bone for source bone with specified name,
    using the currently defined src mapping.'''
    lname = canonicalSrcName(srcName)
    try:
        return the.srcArmature[lname]     
    except KeyError:
        pass
    raise MocapError("No target bone corresponding to source bone %s (%s)" % (srcName, lname))


def getMapping(bvhRig):
    mapping = {}
    notFound = []
    for bone in bvhRig.getBones():
        try:
            tgtBone = getTargetFromSource(bone.name)
            mapping[canonicalSrcName(bone.name)] = tgtBone
        except:
            notFound.append(canonicalSrcName(bone.name))
            pass
    if len(notFound) > 0:
        print "WARNING: no mappings available for BVH rig bones "+ str(notFound)
    return mapping


def renameBones(srcRig):
    '''Canonalize names of bvh source rig.'''
    srcRig.canonalizeNames()

    '''
    srcBones = []
    trgBones = {}

    # (blender) copy bones of source rig to srcBones
    ebones = srcRig.data.edit_bones
    for bone in ebones:
        srcBones.append( CEditBone(bone) )

    # animation bones
    setbones = []
    adata = srcRig.animation_data
    for srcBone in srcBones:
        srcName = srcBone.name
        (trgName, twist) = getTargetFromSource(srcName)
        eb = ebones[srcName]
        if trgName:
            eb.name = trgName
            trgBones[trgName] = CEditBone(eb)
            setbones.append((eb, trgName))
        else:
            eb.name = '_' + srcName

    # renaming
    for (eb, name) in setbones:
        eb.name = name
    '''
    return


def getSrcBone(name):
    global reverseMapping
    if not reverseMapping:
        # TODO it's not a good idea to cache this mapping this way, what if a different BVH gets loaded afterwards?
        reverseMapping = {}
        for (k,v) in the.srcArmature.items():
            if v[0] and v[0] != "None":
                reverseMapping[ v[0] ] = k
                #print "adding %s => %s" % (v[0], k)

    return reverseMapping[name]


def rescaleRig(trgRig, srcRig):
    '''Rescale source rig to size of target rig using the
    length of the left upper leg bone as a reference.'''
    trgScale = trgRig.getJoint('UpLeg_L').length      # TODO should be getBone ...
    try:
        boneName = getSrcBone('UpLeg_L')
    except Exception as e:
        print "ERROR: every source rig should have a left upper-leg bone!"
        raise e
    print 'Comparing MHX bone "UpLeg_L" with BVH bone "%s" to calculate scale.' % boneName
    srcScale = srcRig.getJoint(boneName).length
    scale = trgScale/srcScale
    print("Rescaled with factor %f" % (scale))
    
    # Scale bones
    srcRig.scale(scale)

    # Scale animations
    # TODO
    '''
    adata = srcRig.animation_data
    if adata is None:
        return
    for fcu in adata.action.fcurves:
        words = fcu.data_path.split('.')
        if words[-1] == 'location':
            for kp in fcu.keyframe_points:
                kp.co[1] *= scale
    '''
    return scale


class CAnimation:
    '''Stores an animation track on a src and target rig'''
    def __init__(self, srcRig, trgRig):
        self.srcRig = srcRig
        self.trgRig = trgRig
        self.boneDatas = {}
        self.boneDataList = []
        return


class CBoneData:
    '''Stores a src and target bone and their transformation'''
    def __init__(self, srcBone, trgBone):
        self.name = srcBone.name
        self.parent = None        
        self.srcMatrices = {}        
        self.srcPoseBone = srcBone        
        self.trgPoseBone = trgBone
        self.trgRestMat = None
        self.trgRestInv = None
        self.trgBakeMat = None
        self.trgBakeInv = None
        self.trgOffset = None
        self.rotOffset = None
        self.rotOffsInv = None
        self.rollMat = None
        self.rollInv = None
        return


def activeFrames(ob):
    active = {}
    if ob.animation_data is None:
        return []
    action = ob.animation_data.action
    if action is None:
        return []
    # get a list of the time positions of all keyframe points in all fcurves (Blender)
    for fcu in action.fcurves:
        for kp in fcu.keyframe_points:
            active[kp.co[0]] = True
    
    # sort them on timestamp
    frames = list(active.keys())
    frames.sort()
    return frames


# TODO make sure retarget between two generic_skeletons works as generically as
# possible, requiring only two rigs and a bone mapping
def retargetMhxRig(srcRig, trgRig, boneMapping):
    # TODO also add IK rigging (idea: blend IK and FK, do IK for all bones touching the ground)
    anim = CAnimation(srcRig, trgRig)
    ##(boneAssoc, parAssoc, rolls) = target.getTargetArmature(trgRig, scn)
    setupFkBones(srcRig, trgRig, boneMapping, parAssoc, anim)
    # ordered list with all timestamps on which frames are available
    frames = activeFrames(srcRig)

    try:
        # scn.frame_current
        current_frame = frames[0]
    except:
        raise Exception("No frames found.")
    
    # set attributes of target rig
    #oldData = changeTargetData(trgRig, anim)

    #clearPose()

    # Work in blocks of 100 frames
    frameBlock = frames[0:100]
    index = 0
    first = True

    while frameBlock:
        collectSrcMats(anim, frameBlock, scn)
        retargetMatrices(anim, frameBlock, first)
        index += 100
        first = False
        frameBlock = frames[index:index+100]

    #frame_current = frames[0]

    #utils.setInterpolation(trgRig)
    #act = trgRig.animation_data.action
    #act.name = trgRig.name[:4] + srcRig.name[2:]
    #act.use_fake_user = True
    print("Retargeted %s --> %s" % (srcRig, trgRig))
    return


def retargetMatrices(anim, frames, first, doFK, doIK, scn):
    for frame in frames:
        if frame % 100 == 0:
            print("Retarget", int(frame))
        for boneData in anim.boneDataList:
            retargetFkBone(boneData, frame)
    return


def retargetFkBone(boneData, frame):
    srcBone = boneData.srcPoseBone
    trgBone = boneData.trgPoseBone
    name = srcBone.name
    srcMatrix = boneData.srcMatrices[frame]
    srcRot = srcMatrix  #* srcData.rig.matrix_world
    bakeMat = srcMatrix

    # Set translation offset
    parent = boneData.parent
    if parent:
        #print(name, parent.name)
        parMat = parent.srcMatrices[frame]
        parInv = parMat.inverted()
        loc = parMat * boneData.trgOffset
        setTranslation(bakeMat, loc)
        bakeMat = parInv * bakeMat

        if parent.rollMat:
            #roll = utils.getRollMat(parent.rollMat)
            #print("ParRoll", name, parent.name, roll*D)
            bakeRot = parent.rollInv * bakeMat
            setRotation(bakeMat, bakeRot)
        elif parent.rotOffsInv:
            bakeRot = parent.rotOffsInv * bakeMat
            setRotation(bakeMat, bakeRot)

        parRest = parent.trgRestMat
        bakeMat = parRest * bakeMat
    else:
        parMat = None
        parRotInv = None
        
    # Set rotation offset        
    if boneData.rotOffset:
        rot = boneData.rotOffset
        if parent and parent.rotOffsInv:
            rot = rot * parent.rotOffsInv        
        bakeRot = bakeMat * rot
        setRotation(bakeMat, bakeRot)
    else:
        rot = None
        
    trgMat = boneData.trgRestInv * bakeMat

    if boneData.rollMat:
        #roll = utils.getRollMat(boneData.rollMat)
        #print("SelfRoll", name, roll*D)
        trgRot = trgMat * boneData.rollMat
        setRotation(trgMat, trgRot)
        #utils.printMat4(" Trg2", trgMat, "  ")
        #halt

    trgBone.matrix_basis = trgMat
    if 0 and trgBone.name == "Hip_L":
        print(name)
        utils.printMat4(" PM", parMat, "  ")
        utils.printMat4(" PR", parent.rotOffsInv, "  ")
        utils.printMat4(" RO", boneData.rotOffset, "  ")
        utils.printMat4(" BR", bakeRot, "  ")
        utils.printMat4(" BM", bakeMat, "  ")
        utils.printMat4(" Trg", trgMat, "  ")
        #halt
    
    if trgBone.name in IgnoreBones:
        trgBone.rotation_quaternion = (1,0,0,0)
    
    utils.insertRotationKeyFrame(trgBone, frame)
    if not boneData.parent:
        trgBone.keyframe_insert("location", frame=frame, group=trgBone.name)
    return        



## Definitions of MHX rig bones that need special treatment ##
KeepRotationOffset = ["Root", "Pelvis", "Hips", "Hip_L", "Hip_R"]
ClavBones = ["Clavicle_L", "Clavicle_R"]
SpineBones = ["Spine1", "Spine2", "Spine3", "Neck", "Head"]
#FootBones = []
#IgnoreBones = []
FootBones = ["Foot_L", "Foot_R", "Toe_L", "Toe_R"]
IgnoreBones = ["Toe_L", "Toe_R"]


## Retarget options
USE_SPINE_OFFSET = False
USE_CLAVICLE_OFFSET = False


def setupFkBones(srcRig, trgRig, boneMapping, anim):
    keepOffsets = KeepRotationOffset + FootBones
    keepOffsInverts = []
    if USE_SPINE_OFFSET:
        keepOffsets += SpineBones
        keepOffsInverts += SpineBones
    if USE_CLAVICLE_OFFSET:
        keepOffsets += ClavBones
        keepOffsInverts += ClavBones

    # Simplified mapping: src to MHX
    for (srcName, trgName) in boneMapping:
        try:
            srcBone = srcRig.getJoint(srcName)
            trgBone = trgRig.getJoint(trgName)
        except:
            print("  -", trgName, srcName)
            continue
        # Create direct mapping between bones
        boneData = CBoneData(srcBone, trgBone)
        anim.boneDatas[trgName] = boneData   
        anim.boneDataList.append(boneData)

        # Assign rest pose matrix (position relative to root)
        boneData.trgRestMat = trgBone.rest_mat
        boneData.trgRestInv = aljabr.invTransform(trgBone.rest_mat)
        boneData.trgBakeMat = boneData.trgRestMat
        # Inherit rotation from parent bone
        if trgBone.parent:  #trgBone.bone.use_inherit_rotation:
            try:
                boneData.parent = anim.boneDatas[trgBone.parent.name]
                parRest = boneData.parent.trgRestMat
                parRestInv = boneData.parent.trgRestInv
                offs = sub(trgBone.position, trgBone.parent.tail)
                # calculate offset in global coordinates (relative to root) 
                boneData.trgOffset = aljabr.mmul( aljabr.mmul(parRestInv, aljabr.getTranslation(offs)), parRest)
                boneData.trgBakeMat = aljabr.mmul(parRestInv, boneData.trgRestMat)
                #print(trgName, trgBone.parent.name)
            except:
                pass


        trgRoll = getRoll(trgBone)  # TODO will be 0
        srcRoll = getSourceRoll(srcName) * Deg2Rad
        diff = srcRoll - trgRoll

        # Determine whether offset between src and target has to be kept for this bone
        if srcName in keepOffsets:
            # rotation offset transformtaion between src and target bone rest        
            offs = aljabr.mmul(trgBone.rest_mat, aljabr.invTransform(srcBone.rest_mat))
            boneData.rotOffset = aljabr.mmul( aljabr.mmul(boneData.trgRestInv, offs), boneData.trgRestMat )
            if trgName in keepOffsInverts:
                boneData.rotOffsInv = aljabr.invTransform(boneData.rotOffset)
        # If not keepOffsets and rotation is above threshold, make rot matrix
        elif abs(diff) > 0.02:
            #boneData.rollMat = Matrix.Rotation(diff, 4, 'Y')
            boneData.rollMat = aljabr.makeRotMatrix(diff, [0,1,0])
            boneData.rollMat = aljabr.rotMatrix2Matrix4(boneData.rollMat)
            boneData.rollInv = aljabr.invTransform(boneData.rollMat)

        boneData.trgBakeInv = aljabr.invTransform(boneData.trgBakeMat)
    return


def getRoll(bone):
    return getRollFromMat(bone.rest_mat)


def getRollFromMat(mat):
    # TODO verify correctness
    #quat = mat.to_3x3().to_quaternion()
    quat = quaternion_from_matrix(mat)
    if abs(quat[0]) < 1e-4: # quat.w
        roll = pi
    else:
        roll = -2*atan(quat[2]/quat[0])   # quat.y/quat.w
    return roll


def getSourceRoll(srcName):
    (bone, roll) = the.srcArmature[srcName]
    return roll


def collectSrcMats(anim, frames):
    '''Retrieve transformation matrices for all bones of source mesh 
    for each keyframe. anim is a CAnimation object, frames. Used for
    FK rigging'''
    try:            
        for frame in frames:
            #scn.frame_set(frame)
            if frame % 100 == 0:
                # Simple progress indicator
                print("Collect", int(frame))
            for boneData in anim.boneDataList:
                ## TODO!!
                #boneData.srcMatrices[frame] = boneData.srcPoseBone.matrix.copy()
                pass
    finally:
        #unhideObjects(objects)
        pass
    return   
