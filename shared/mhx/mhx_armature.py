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

MHX armature
"""

import math
import numpy as np
import mh2proxy
import exportutils

import armature as amtpkg
from .flags import *
from armature.rigdefs import CArmature

from . import posebone
from . import mhx_drivers
from . import mhx_constraints
from . import rig_joints_25
from . import rig_body_25
from . import rig_shoulder_25
from . import rig_arm_25
from . import rig_finger_25
from . import rig_leg_25
from . import rig_toe_25
from . import rig_face_25
from . import rig_panel_25
from . import rig_skirt_25
from . import rigify_rig


#-------------------------------------------------------------------------------        
#   Setup custom shapes
#-------------------------------------------------------------------------------        

def setupCircle(fp, name, r):
    """
    Write circle object to the MHX file. Circles are used as custom shapes.
    
    fp:
        *File*: Output file pointer. 
    name:
        *string*: Object name.
    r:
        *float*: Radius.
    """

    fp.write("\n"+
        "Mesh %s %s \n" % (name, name) +
        "  Verts\n")
    for n in range(16):
        v = n*pi/8
        y = 0.5 + 0.02*sin(4*v)
        fp.write("    v %.3f %.3f %.3f ;\n" % (r*math.cos(v), y, r*math.sin(v)))
    fp.write(
        "  end Verts\n" +
        "  Edges\n")
    for n in range(15):
        fp.write("    e %d %d ;\n" % (n, n+1))
    fp.write(
        "    e 15 0 ;\n" +
        "  end Edges\n"+
        "end Mesh\n")
        
    fp.write(
        "Object %s MESH %s\n" % (name, name) +
        "  layers Array 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1  ;\n"+
        "  parent Refer Object CustomShapes ;\n"+
        "end Object\n")


def setupCube(fp, name, r, offs):
    """
    Write cube object to the MHX file. Cubes are used as custom shapes.
    
    fp:
        *File*: Output file pointer. 
    name:
        *string*: Object name.
    r:
        *float* or *float triple*: Side(s) of cube.
    offs:
        *float* or *float triple*: Y offset or offsets from origin.
    """
    
    try:
        (rx,ry,rz) = r
    except:
        (rx,ry,rz) = (r,r,r)
    try:
        (dx,dy,dz) = offs
    except:
        (dx,dy,dz) = (0,offs,0)

    fp.write("\n"+
        "Mesh %s %s \n" % (name, name) +
        "  Verts\n")
    for x in [-rx,rx]:
        for y in [-ry,ry]:
            for z in [-rz,rz]:
                fp.write("    v %.2f %.2f %.2f ;\n" % (x+dx,y+dy,z+dz))
    fp.write(
        "  end Verts\n" +
        "  Faces\n" +
        "    f 0 1 3 2 ;\n" +
        "    f 4 6 7 5 ;\n" +
        "    f 0 2 6 4 ;\n" +
        "    f 1 5 7 3 ;\n" +
        "    f 1 0 4 5 ;\n" +
        "    f 2 3 7 6 ;\n" +
        "  end Faces\n" +
        "end Mesh\n")

    fp.write(
        "Object %s MESH %s\n" % (name, name) +
        "  layers Array 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1  ;\n" +
        "  parent Refer Object CustomShapes ;\n" +
        "end Object\n")


def setupCustomShapes(fp):
    """
    Write simple custom shapes to the MHX file. Additional custom shapes are defined in 
    mhx files in mhx/templates.
    
    fp:
        *File*: Output file pointer. 
    """
    
    setupCircle(fp, "MHCircle01", 0.1)
    setupCircle(fp, "MHCircle025", 0.25)
    setupCircle(fp, "MHCircle05", 0.5)
    setupCircle(fp, "MHCircle10", 1.0)
    setupCircle(fp, "MHCircle15", 1.5)
    setupCircle(fp, "MHCircle20", 2.0)
    setupCube(fp, "MHCube01", 0.1, 0)
    setupCube(fp, "MHCube025", 0.25, 0)
    setupCube(fp, "MHCube05", 0.5, 0)
    setupCube(fp, "MHEndCube01", 0.1, 1)
    setupCube(fp, "MHChest", (0.7,0.25,0.5), (0,0.5,0.35))
    setupCube(fp, "MHRoot", (1.25,0.5,1.0), 1)
    return

#-------------------------------------------------------------------------------        
#   Armature used for export
#-------------------------------------------------------------------------------        

class ExportArmature(CArmature):

    def __init__(self, name, human, config):    
        CArmature. __init__(self, name, human, config)
        self.customShapeFiles = []
        self.customShapes = {}
        self.poseInfo = {}
        self.gizmos = None
        self.boneLayers = "00000001"

        self.boneGroups = []
        self.recalcRoll = []              
        self.vertexGroupFiles = []
        self.gizmoFiles = []
        self.headName = 'Head'
        self.objectProps = [("MhxRig", '"%s"' % config.rigtype)]
        self.armatureProps = []
        self.customProps = []


    def setup(self):
        if self.rigtype in ["mhx", "rigify"]:
            self.setupJoints()       
            self.moveOriginToFloor()
            self.dynamicLocations()
            for (bone, head, tail) in self.headsTails:
                self.rigHeads[bone] = self.findLocation(head)
                self.rigTails[bone] = self.findLocation(tail)
        else:
            self.joints += rig_joints_25.DeformJoints + rig_joints_25.FloorJoints
            self.setupJoints()
            self.moveOriginToFloor()
            amtpkg.rigdefs.CArmature.setup(self)
        
        if self.config.clothesRig:
            for proxy in self.proxies.values():
                if proxy.rig:
                    coord = []
                    for refVert in proxy.refVerts:
                        coord.append(refVert.getCoord())
                    (locations, boneList, weights) = exportutils.rig.readRigFile(proxy.rig, amt.mesh, coord=coord) 
                    proxy.weights = self.prefixWeights(weights, proxy.name)
                    appendRigBones(boneList, proxy.name, L_CLO, body, amt)
        


    def setupJoints (self):
        """
        Evaluate symbolic expressions for joint locations and store them in self.locations.
        Joint locations are specified symbolically in the *Joints list in the beginning of the
        rig_*.py files (e.g. ArmJoints in rig_arm.py). 
        """
        
        for (key, typ, data) in self.joints:
            if typ == 'j':
                loc = mh2proxy.calcJointPos(self.mesh, data)
                self.locations[key] = loc
                self.locations[data] = loc
            elif typ == 'v':
                v = int(data)
                self.locations[key] = self.mesh.coord[v]
            elif typ == 'x':
                self.locations[key] = np.array((float(data[0]), float(data[2]), -float(data[1])))
            elif typ == 'vo':
                v = int(data[0])
                offset = np.array((float(data[1]), float(data[3]), -float(data[2])))
                self.locations[key] = self.mesh.coord[v] + offset
            elif typ == 'vl':
                ((k1, v1), (k2, v2)) = data
                loc1 = self.mesh.coord[int(v1)]
                loc2 = self.mesh.coord[int(v2)]
                self.locations[key] = k1*loc1 + k2*loc2
            elif typ == 'f':
                (raw, head, tail, offs) = data
                rloc = self.locations[raw]
                hloc = self.locations[head]
                tloc = self.locations[tail]
                vec = tloc - hloc
                vraw = rloc - hloc
                x = np.dot(vec, vraw)/np.dot(vec,vec)
                self.locations[key] = hloc + x*vec + np.array(offs)
            elif typ == 'b':
                self.locations[key] = self.locations[data]
            elif typ == 'p':
                x = self.locations[data[0]]
                y = self.locations[data[1]]
                z = self.locations[data[2]]
                self.locations[key] = np.array((x[0],y[1],z[2]))
            elif typ == 'vz':
                v = int(data[0])
                z = self.mesh.coord[v][2]
                loc = self.locations[data[1]]
                self.locations[key] = np.array((loc[0],loc[1],z))
            elif typ == 'X':
                r = self.locations[data[0]]
                (x,y,z) = data[1]
                r1 = np.array([float(x), float(y), float(z)])
                self.locations[key] = np.cross(r, r1)
            elif typ == 'l':
                ((k1, joint1), (k2, joint2)) = data
                self.locations[key] = k1*self.locations[joint1] + k2*self.locations[joint2]
            elif typ == 'o':
                (joint, offsSym) = data
                if type(offsSym) == str:
                    offs = self.locations[offsSym]
                else:
                    offs = np.array(offsSym)
                self.locations[key] = self.locations[joint] + offs
            else:
                raise NameError("Unknown %s" % typ)
        return
    
    
    def moveOriginToFloor(self):
        if self.config.feetOnGround:
            self.origin = self.locations['floor']
            for key in self.locations.keys():
                self.locations[key] = self.locations[key] - self.origin
        else:
            self.origin = np.array([0,0,0], float)
        return
    
        
    def setupHeadsTails(self):
        self.rigHeads = {}
        self.rigTails = {}
        scale = self.config.scale
        for (bone, head, tail) in self.headsTails:
            self.rigHeads[bone] = findLocation(self, head)
            self.rigTails[bone] = findLocation(self, tail)
        
    
    def findLocation(self, joint):
        try:
            (bone, offs) = joint
            return self.locations[bone] + offs
        except:
            return self.locations[joint]


    def setupCustomShapes(self, fp):
        if self.gizmos:
            fp.write(self.gizmos)
            setupCustomShapes(fp)
        else:        
            for (name, data) in self.customShapes.items():
                (typ, r) = data
                if typ == "-circ":
                    setupCircle(fp, name, 0.1*r)
                elif typ == "-box":
                    setupCube(fp, name, 0.1*r, (0,0,0))
                else:
                    halt


    def writeEditBones(self, fp):        
        for data in self.boneDefs:
            (bone, roll, parent, flags, layers, bbone) = data
            conn = (flags & F_CON != 0)
            deform = (flags & F_DEF != 0)
            restr = (flags & F_RES != 0)
            wire = (flags & F_WIR != 0)
            lloc = (flags & F_NOLOC == 0)
            lock = (flags & F_LOCK != 0)
            cyc = (flags & F_NOCYC == 0)
        
            scale = self.config.scale
    
            fp.write("\n  Bone %s %s\n" % (bone, True))
            (x, y, z) = scale*self.rigHeads[bone]
            fp.write("    head  %.6g %.6g %.6g  ;\n" % (x,-z,y))
            (x, y, z) = scale*self.rigTails[bone]
            fp.write("    tail %.6g %.6g %.6g  ;\n" % (x,-z,y))
            if type(parent) == tuple:
                (soft, hard) = parent
                if hard:
                    fp.write(
                        "#if toggle&T_HardParents\n" +
                        "    parent Refer Bone %s ;\n" % hard +
                        "#endif\n")
                if soft:
                    fp.write(
                        "#if toggle&T_HardParents==0\n" +
                        "    parent Refer Bone %s ;\n" % soft +
                        "#endif\n")
            elif parent:
                fp.write("    parent Refer Bone %s ; \n" % (parent))
            fp.write(
                "    roll %.6g ; \n" % (roll)+
                "    use_connect %s ; \n" % (conn) +
                "    use_deform %s ; \n" % (deform) +
                "    show_wire %s ; \n" % (wire))
    
            if 1 and (flags & F_HID):
                fp.write("    hide True ; \n")
    
            if bbone:
                (bin, bout, bseg) = bbone
                fp.write(
                    "    bbone_in %d ; \n" % (bin) +
                    "    bbone_out %d ; \n" % (bout) +
                    "    bbone_segments %d ; \n" % (bseg))
    
            if flags & F_NOROT:
                fp.write("    use_inherit_rotation False ; \n")
            if flags & F_SCALE:
                fp.write("    use_inherit_scale True ; \n")
            else:
                fp.write("    use_inherit_scale False ; \n")
            fp.write("    layers Array ")
    
            bit = 1
            for n in range(32):
                if layers & bit:
                    fp.write("1 ")
                else:
                    fp.write("0 ")
                bit = bit << 1
    
            fp.write(" ; \n" +
                "    use_local_location %s ; \n" % lloc +
                "    lock %s ; \n" % lock +
                "    use_envelope_multiply False ; \n"+
                "    hide_select %s ; \n" % (restr) +
                "  end Bone \n")


    def writeBoneGroups(self, fp):    
        if not fp:
            return
        for (name, color) in self.boneGroups:
            fp.write(
                "    BoneGroup %s\n" % name +
                "      name '%s' ;\n" % name +
                "      color_set '%s' ;\n" % color +
                "    end BoneGroup\n")
        return


    def writeControlPoses(self, fp, config):
        for (bone, cinfo) in self.poseInfo.items():
            cs = None
            constraints = []
            for (key, value) in cinfo:
                if key == "CS":
                    cs = value
                elif key == "IK":
                    goal = value[0]
                    n = int(value[1])
                    inf = float(value[2])
                    pt = value[3]
                    if pt:
                        log.debug("%s %s %s %s", goal, n, inf, pt)
                        subtar = pt[0]
                        poleAngle = float(pt[1])
                        pt = (poleAngle, subtar)
                    constraints =  [('IK', 0, inf, ['IK', goal, n, pt, (True,False,True)])]
            posebone.addPoseBone(fp, self, bone, cs, None, (0,0,0), (0,0,0), (1,1,1), (1,1,1), 0, constraints)       


    def writeProperties(self, fp):
        for (key, val) in self.objectProps:
            fp.write("  Property %s %s ;\n" % (key, val))
            
        for (key, val, string, min, max) in self.customProps:
            self.defProp(fp, "FLOAT", key, val, string, min, max)
    
        if self.config.expressions:
            fp.write("#if toggle&T_Shapekeys\n")
            for skey in exportutils.shapekeys.ExpressionUnits:
                self.defProp(fp, "FLOAT", "Mhs%s"%skey, 0.0, skey, -1.0, 2.0)
                #fp.write("  DefProp Float Mhs%s 0.0 %s min=-1.0,max=2.0 ;\n" % (skey, skey))
            fp.write("#endif\n")   


    def defProp(self, fp, type, key, val, string, min=0, max=1):            
        #fp.write("  DefProp %s %s %s %s min=%s,max=%s ;\n" % (type, key, val, string, min, max))
        if type == "BOOLEAN":
            fp.write(
                '  Property %s %s %s ;\n' % (key, val, string) +
                '  PropKeys %s "type":\'%s\', "min":%d,"max":%d, ;\n' % (key, type, min, max))
        elif type == "FLOAT":
            fp.write(
                '  Property %s %.2f %s ;\n' % (key, val, string) +
                '  PropKeys %s "min":%.2f,"max":%.2f, ;\n' % (key, min, max))
        else:
            halt
    

    def writeArmature(self, fp, version):
        fp.write("""
# ----------------------------- ARMATURE --------------------- # 

NoScale False ;
""")

        fp.write("Armature %s %s   Normal \n" % (self.name, self.name))
        self.writeEditBones(fp)

        fp.write("""        
  show_axes False ;
  show_bone_custom_shapes True ;
  show_group_colors True ;
  show_names False ;
  draw_type 'STICK' ;
  layers Array 1 1 1 1 1 1 1 1  1 1 1 1 1 1 1 1  1 1 1 1 1 1 1 1  1 1 1 1 1 1 1 1  ;
""")

        if self.config.rigtype == "mhx":
            fp.write("  RecalcRoll %s ;\n" % self.recalcRoll)
  
        fp.write("""
  layers_protected Array 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0  ;
  pose_position 'POSE' ;
  use_mirror_x False ;

end Armature
""")

        fp.write(
            "Object %s ARMATURE %s\n"  % (self.name, self.name) +
            "  Property MhxVersion %d ;\n" % version)

        fp.write("""
  layers Array 0 1 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0  ;
  up_axis 'Z' ;
  show_x_ray True ;
  draw_type 'WIRE' ;
  Property MhxScale theScale ;
  Property MhxVisemeSet 'BodyLanguage' ;

  Property _RNA_UI {} ;
""")

        self.writeProperties(fp)
        self.writeHideProp(fp, self.name)
        for proxy in self.proxies.values():
            self.writeHideProp(fp, proxy.name)
        if self.config.useCustomShapes: 
            exportutils.custom.listCustomFiles(self.config)                    
        for path,name in self.config.customShapeFiles:
            self.defProp(fp, "FLOAT", name, 0, name[3:], -1.0, 2.0)
            #fp.write("  DefProp Float %s 0 %s  min=-1.0,max=2.0 ;\n" % (name, name[3:]))
  
        fp.write("""
end Object
""")


    def writeHideProp(self, fp, name):                
        self.defProp(fp, "BOOLEAN", "Mhh%s"%name, False, "Control_%s_visibility"%name)
        #fp.write("  DefProp Bool Mhh%s False Control_%s_visibility ;\n" % (name, name))
        return

    def dynamicLocations(self):
        pass
        

#-------------------------------------------------------------------------------        
#   MHX armature
#-------------------------------------------------------------------------------        

class MhxArmature(ExportArmature):

    def __init__(self, name, human, config):    
        import gizmos_mhx, gizmos_panel, gizmos_general
    
        ExportArmature. __init__(self, name, human, config)
        self.rigtype = 'mhx'
        self.boneLayers = "0068056b"

        self.boneGroups = [
            ('Master', 'THEME13'),
            ('Spine', 'THEME05'),
            ('FK_L', 'THEME09'),
            ('FK_R', 'THEME02'),
            ('IK_L', 'THEME03'),
            ('IK_R', 'THEME04'),
        ]
        self.recalcRoll = "['Foot_L','Toe_L','Foot_R','Toe_R','DfmFoot_L','DfmToe_L','DfmFoot_R','DfmToe_R']"
        self.gizmos = (gizmos_mhx.asString() + gizmos_panel.asString() + gizmos_general.asString())

        self.objectProps = [("MhxRig", '"MHX"')]
        self.armatureProps = []
        self.headName = 'Head'
        self.preservevolume = False
        
        self.vertexGroupFiles = ["head", "bones", "palm", "tight"]
        if config.skirtRig == "own":
            self.vertexGroupFiles.append("skirt-rigged")    
        elif config.skirtRig == "inh":
            self.vertexGroupFiles.append("skirt")    

        if config.maleRig:
            self.vertexGroupFiles.append( "male" )
                                                        
        self.joints = (
            rig_joints_25.DeformJoints +
            rig_body_25.BodyJoints +
            rig_joints_25.FloorJoints +
            rig_arm_25.ArmJoints +
            rig_shoulder_25.ShoulderJoints +
            rig_finger_25.FingerJoints +
            rig_leg_25.LegJoints +
            #rig_toe_25.ToeJoints +
            rig_face_25.FaceJoints
        )            
        
        self.headsTails = (
            rig_body_25.BodyHeadsTails +
            rig_shoulder_25.ShoulderHeadsTails +
            rig_arm_25.ArmHeadsTails +
            rig_finger_25.FingerHeadsTails +
            rig_leg_25.LegHeadsTails +
            #rig_toe_25.ToeHeadsTails +
            rig_face_25.FaceHeadsTails
        )

        self.boneDefs = list(rig_body_25.BodyArmature1)
        if config.advancedSpine:
            self.boneDefs += rig_body_25.BodyArmature2Advanced
        else:
            self.boneDefs += rig_body_25.BodyArmature2Simple
        self.boneDefs += rig_body_25.BodyArmature3
        if config.advancedSpine:
            self.boneDefs += rig_body_25.BodyArmature4Advanced
        else:
            self.boneDefs += rig_body_25.BodyArmature4Simple
        self.boneDefs += rig_body_25.BodyArmature5

        self.boneDefs += (
            rig_shoulder_25.ShoulderArmature1 +
            rig_shoulder_25.ShoulderArmature2 +
            rig_arm_25.ArmArmature +            
            rig_finger_25.FingerArmature +
            rig_leg_25.LegArmature +
            #rig_toe_25.ToeArmature +
            rig_face_25.FaceArmature
        )
        
        if config.skirtRig == "own":
            self.joints += rig_skirt_25.SkirtJoints
            self.headsTails += rig_skirt_25.SkirtHeadsTails
            self.boneDefs += rig_skirt_25.SkirtArmature        

        if config.maleRig:
            self.boneDefs += rig_body_25.MaleArmature        

        if self.config.facepanel:            
            self.joints += rig_panel_25.PanelJoints
            self.headsTails += rig_panel_25.PanelHeadsTails
            self.boneDefs += rig_panel_25.PanelArmature

        if False and config.custom:
            (custJoints, custHeadsTails, custArmature, self.customProps) = exportutils.custom.setupCustomRig(config)
            self.joints += custJoints
            self.headsTails += custHeadsTails
            self.boneDefs += custArmature
        

    def dynamicLocations(self):
        rig_body_25.BodyDynamicLocations()
        

    def setupCustomShapes(self, fp):
        ExportArmature.setupCustomShapes(self, fp)
        if self.config.facepanel:
            import gizmos_panel
            setupCube(fp, "MHCube025", 0.25, 0)
            setupCube(fp, "MHCube05", 0.5, 0)
            self.gizmos = gizmos_panel.asString()
            fp.write(self.gizmos)
        

    def writeControlPoses(self, fp, config):
        self.writeBoneGroups(fp)
        rig_body_25.BodyControlPoses(fp, self, config)
        rig_shoulder_25.ShoulderControlPoses(fp, self)
        rig_arm_25.ArmControlPoses(fp, self)
        rig_finger_25.FingerControlPoses(fp, self)
        rig_leg_25.LegControlPoses(fp, self)
        #rig_toe_25.ToeControlPoses(fp, self)
        rig_face_25.FaceControlPoses(fp, self)
        if self.config.maleRig:
            rig_body_25.MaleControlPoses(fp, self)
        if self.config.skirtRig == "own":
            rig_skirt_25.SkirtControlPoses(fp, self)            
        if self.config.facepanel:
            rig_panel_25.PanelControlPoses(fp, self)
        ExportArmature.writeControlPoses(self, fp, config)


    def writeDrivers(self, fp):
        driverList = (
            mhx_drivers.writePropDrivers(fp, self, rig_arm_25.ArmPropDrivers, "", "Mha") +
            mhx_drivers.writePropDrivers(fp, self, rig_arm_25.ArmPropLRDrivers, "_L", "Mha") +
            mhx_drivers.writePropDrivers(fp, self, rig_arm_25.ArmPropLRDrivers, "_R", "Mha") +
            mhx_drivers.writePropDrivers(fp, self, rig_arm_25.SoftArmPropLRDrivers, "_L", "Mha") +
            mhx_drivers.writePropDrivers(fp, self, rig_arm_25.SoftArmPropLRDrivers, "_R", "Mha") +
            #writeScriptedBoneDrivers(fp, rig_leg_25.LegBoneDrivers) +
            mhx_drivers.writePropDrivers(fp, self, rig_leg_25.LegPropDrivers, "", "Mha") +
            mhx_drivers.writePropDrivers(fp, self, rig_leg_25.LegPropLRDrivers, "_L", "Mha") +
            mhx_drivers.writePropDrivers(fp, self, rig_leg_25.LegPropLRDrivers, "_R", "Mha") +
            mhx_drivers.writePropDrivers(fp, self, rig_leg_25.SoftLegPropLRDrivers, "_L", "Mha") +
            mhx_drivers.writePropDrivers(fp, self, rig_leg_25.SoftLegPropLRDrivers, "_R", "Mha") +
            mhx_drivers.writePropDrivers(fp, self, rig_body_25.BodyPropDrivers, "", "Mha")
        )
        if self.config.advancedSpine:
            driverList += mhx_drivers.writePropDrivers(fp, self, rig_body_25.BodyPropDriversAdvanced, "", "Mha") 
        driverList += (
            mhx_drivers.writePropDrivers(fp, self, rig_face_25.FacePropDrivers, "", "Mha") +
            mhx_drivers.writePropDrivers(fp, self, rig_face_25.SoftFacePropDrivers, "", "Mha")
        )
        fingDrivers = rig_finger_25.getFingerPropDrivers()
        driverList += (
            mhx_drivers.writePropDrivers(fp, self, fingDrivers, "_L", "Mha") +
            mhx_drivers.writePropDrivers(fp, self, fingDrivers, "_R", "Mha") +
            #rig_panel_25.FingerControlDrivers(fp)
            mhx_drivers.writeMuscleDrivers(fp, rig_shoulder_25.ShoulderDeformDrivers, self.name) +
            mhx_drivers.writeMuscleDrivers(fp, rig_arm_25.ArmDeformDrivers, self.name) +
            mhx_drivers.writeMuscleDrivers(fp, rig_leg_25.LegDeformDrivers, self.name)
        )
        faceDrivers = rig_face_25.FaceDeformDrivers(fp, self)
        driverList += mhx_drivers.writeDrivers(fp, True, faceDrivers)
        return driverList
    

    def writeActions(self, fp):
        #rig_arm_25.ArmWriteActions(fp)
        #rig_leg_25.LegWriteActions(fp)
        #rig_finger_25.FingerWriteActions(fp)
        return

        
    def writeProperties(self, fp):
        ExportArmature.writeProperties(self, fp)

        fp.write("""
  Property MhaArmIk_L 0.0 Left_arm_FK/IK ;
  PropKeys MhaArmIk_L "min":0.0,"max":1.0, ;

  Property MhaArmHinge_L False Left_arm_hinge ;
  PropKeys MhaArmHinge_L "type":'BOOLEAN',"min":0,"max":1, ;

  Property MhaElbowPlant_L False Left_elbow_plant ;
  PropKeys MhaElbowPlant_L "type":'BOOLEAN',"min":0,"max":1, ;

  Property MhaHandFollowsWrist_L True Left_hand_follows_wrist ;
  PropKeys MhaHandFollowsWrist_L "type":'BOOLEAN',"min":0,"max":1, ;

  Property MhaLegIk_L 0.0 Left_leg_FK/IK ;
  PropKeys MhaLegIk_L "min":0.0,"max":1.0, ;
  
  Property MhaLegIkToAnkle_L False Left_leg_IK_to_ankle ;
  PropKeys MhaLegIkToAnkle_L "type":'BOOLEAN',"min":0,"max":1, ;

  # Property MhaKneeFollowsFoot_L True Left_knee_follows_foot ;
  # PropKeys MhaKneeFollowsFoot_L "type":'BOOLEAN',"min":0,"max":1, ;

  # Property MhaKneeFollowsHip_L False Left_knee_follows_hip ;
  # PropKeys MhaKneeFollowsHip_L "type":'BOOLEAN',"min":0,"max":1, ;

  # Property MhaElbowFollowsWrist_L False Left_elbow_follows_wrist ;
  # PropKeys MhaElbowFollowsWrist_L "type":'BOOLEAN',"min":0,"max":1, ;

  # Property MhaElbowFollowsShoulder_L True Left_elbow_follows_shoulder ;
  # PropKeys MhaElbowFollowsShoulder_L "type":'BOOLEAN',"min":0,"max":1, ;

  Property MhaFingerControl_L True Left_fingers_controlled ;
  PropKeys MhaFingerControl_L "type":'BOOLEAN',"min":0,"max":1, ;

  Property MhaArmIk_R 0.0 Right_arm_FK/IK ;
  PropKeys MhaArmIk_R "min":0.0,"max":1.0, ;

  Property MhaArmHinge_R False Right_arm_hinge ;
  PropKeys MhaArmHinge_R "type":'BOOLEAN',"min":0,"max":1, ;

  Property MhaElbowPlant_R False Right_elbow_plant ;
  PropKeys MhaElbowPlant_R "type":'BOOLEAN',"min":0,"max":1, ;

  Property MhaLegIk_R 0.0 Right_leg_FK/IK ;
  PropKeys MhaLegIk_R "min":0.0,"max":1.0, ;

  Property MhaHandFollowsWrist_R True Right_hand_follows_wrist ;
  PropKeys MhaHandFollowsWrist_R "type":'BOOLEAN',"min":0,"max":1, ;

  Property MhaLegIkToAnkle_R False Right_leg_IK_to_ankle ;
  PropKeys MhaLegIkToAnkle_R "type":'BOOLEAN',"min":0,"max":1, ;

  # Property MhaKneeFollowsFoot_R True Right_knee_follows_foot ;
  # PropKeys MhaKneeFollowsFoot_R "type":'BOOLEAN',"min":0,"max":1, ;

  # Property MhaKneeFollowsHip_R False Right_knee_follows_hip ;
  # PropKeys MhaKneeFollowsHip_R "type":'BOOLEAN',"min":0,"max":1, ;

  # Property MhaElbowFollowsWrist_R False Right_elbow_follows_wrist ;
  # PropKeys MhaElbowFollowsWrist_R "type":'BOOLEAN',"min":0,"max":1, ;

  # Property MhaElbowFollowsShoulder_R True Right_elbow_follows_shoulder ;
  # PropKeys MhaElbowFollowsShoulder_R "type":'BOOLEAN',"min":0,"max":1, ;

  Property MhaGazeFollowsHead 1.0 Gaze_follows_world_or_head ;
  PropKeys MhaGazeFollowsHead "type":'BOOLEAN',"min":0.0,"max":1.0, ;

  Property MhaFingerControl_R True Right_fingers_controlled ;
  PropKeys MhaFingerControl_R "type":'BOOLEAN',"min":0,"max":1, ;
  
  Property MhaArmStretch_L 0.1 Left_arm_stretch_amount ;
  PropKeys MhaArmStretch_L "min":0.0,"max":1.0, ;

  Property MhaLegStretch_L 0.1 Left_leg_stretch_amount ;
  PropKeys MhaLegStretch_L "min":0.0,"max":1.0, ;

  Property MhaArmStretch_R 0.1 Right_arm_stretch_amount ;
  PropKeys MhaArmStretch_R "min":0.0,"max":1.0, ;

  Property MhaLegStretch_R 0.1 Right_leg_stretch_amount ;
  PropKeys MhaLegStretch_R "min":0.0,"max":1.0, ;

  Property MhaRotationLimits 0.8 Influence_of_rotation_limit_constraints ;
  PropKeys MhaRotationLimits "min":0.0,"max":1.0, ;

  Property MhaFreePubis 0.5 Pubis_moves_freely ;
  PropKeys MhaFreePubis "min":0.0,"max":1.0, ;

  Property MhaBreathe 0.0 Breathe ;
  PropKeys MhaBreathe "min":-0.5,"max":2.0, ;
""")

        if self.config.advancedSpine:
        
            fp.write("""
  Property MhaSpineInvert False Spine_from_shoulders_to_pelvis ;
  PropKeys MhaSpineInvert "type":'BOOLEAN',"min":0,"max":1, ;
  
  Property MhaSpineIk False Spine_FK/IK ;
  PropKeys MhaSpineIk "type":'BOOLEAN',"min":0,"max":1, ;
  
  Property MhaSpineStretch 0.2 Spine_stretch_amount ;
  PropKeys MhaSpineStretch "min":0.0,"max":1.0, ;    
""")        

#-------------------------------------------------------------------------------        
#   Rigify armature
#-------------------------------------------------------------------------------        

class RigifyArmature(ExportArmature):

    def __init__(self, name, human, config):   
        import gizmos_panel, gizmos_rigify
        
        ExportArmature. __init__(self, name, human, config)
        self.rigtype = 'rigify'
        self.boneLayers = "80005555"

        self.vertexGroupFiles = ["head", "rigify"]
        self.gizmos = (gizmos_panel.asString() + gizmos_rigify.asString())
        self.headName = 'head'
        self.preservevolume = True
        faceArmature = swapParentNames(rig_face_25.FaceArmature, 
                           {'Head' : 'head', 'MasterFloor' : None} )
            
        self.joints = (
            rig_joints_25.DeformJoints +
            rig_body_25.BodyJoints +
            rig_joints_25.FloorJoints +
            rigify_rig.RigifyJoints +
            rig_face_25.FaceJoints
        )
        
        self.headsTails = (
            rigify_rig.RigifyHeadsTails +
            rig_face_25.FaceHeadsTails
        )

        self.boneDefs = (
            rigify_rig.RigifyArmature +
            faceArmature
        )

        self.objectProps = rigify_rig.RigifyObjectProps + [("MhxRig", '"Rigify"')]
        self.armatureProps = rigify_rig.RigifyArmatureProps
        

    def writeDrivers(self, fp):
        rig_face_25.FaceDeformDrivers(fp, self)        
        mhx_drivers.writePropDrivers(fp, self, rig_face_25.FacePropDrivers, "", "Mha")
        mhx_drivers.writePropDrivers(fp, self, rig_face_25.SoftFacePropDrivers, "", "Mha")
        return []


    def writeControlPoses(self, fp, config):
        rigify_rig.RigifyWritePoses(fp, self)
        rig_face_25.FaceControlPoses(fp, self)
        ExportArmature.writeControlPoses(self, fp, config)


def swapParentNames(bones, changes):
    nbones = []
    for bone in bones:
        (name, roll, par, flags, level, bb) = bone
        try:
            nbones.append( (name, roll, changes[par], flags, level, bb) )
        except KeyError:
            nbones.append(bone)
    return nbones





