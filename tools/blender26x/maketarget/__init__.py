# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

# Project Name:        MakeHuman
# Product Home Page:   http://www.makehuman.org/
# Code Home Page:      http://code.google.com/p/makehuman/
# Authors:             Thomas Larsson
# Script copyright (C) MakeHuman Team 2001-2013
# Coding Standards:    See http://www.makehuman.org/node/165

bl_info = {
    "name": "Make Target",
    "author": "Thomas Larsson",
    "version": "1.10",
    "blender": (2, 6, 4),
    "location": "View3D > Properties > Make Target",
    "description": "Make MakeHuman Target",
    "warning": "",
    'wiki_url': "http://www.makehuman.org/node/223",
    "category": "MakeHuman"}

if "bpy" in locals():
    print("Reloading maketarget")
    import imp    
    imp.reload(mh_utils)
    imp.reload(utils)
    imp.reload(mt)
    imp.reload(maketarget)
    imp.reload(convert)
    imp.reload(pose)
    imp.reload(export_mh_obj)
else:
    print("Loading maketarget")
    import bpy
    import os
    from bpy.props import *
    from bpy_extras.io_utils import ImportHelper, ExportHelper

    import mh_utils
    from mh_utils import utils
    from . import mt
    from . import maketarget
    from . import convert
    from . import pose
    from . import export_mh_obj
     
Thomas = False

#----------------------------------------------------------
#   class ConvertTargetPanel(bpy.types.Panel):
#----------------------------------------------------------

class ConvertTargetPanel(bpy.types.Panel):
    bl_label = "Convert Target %s" % bl_info["version"]
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_options = {'DEFAULT_CLOSED'}
    
    def draw(self, context):
        layout = self.layout
        scn = context.scene
        
        layout.operator("mh.set_target_dir")
        layout.prop(scn, "MhTargetDir", text="")

        layout.separator()
        layout.label("Target Conversion")
        layout.operator("mh.set_source_target")
        layout.prop(scn, "MhSourceTarget", text="")
        layout.operator("mh.convert_target")
        
        return

        #layout.separator()
        #layout.label("Clothes Conversion")
        #layout.operator("mh.set_source_mhclo")
        #layout.prop(scn, "MhSourceMhclo", text="")
        #layout.operator("mh.convert_mhclo")

        layout.separator()
        layout.label("Vertex Group Conversion")
        layout.operator("mh.set_source_vgroup")
        layout.prop(scn, "MhSourceVGroup", text="")
        layout.operator("mh.convert_vgroup")
        layout.operator("mh.convert_vgroup_dir")

#----------------------------------------------------------
#   class MakeTargetPanel(bpy.types.Panel):
#----------------------------------------------------------

class MakeTargetPanel(bpy.types.Panel):
    bl_label = "Make Target  Version %s" % bl_info["version"]
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    
    def draw(self, context):
        layout = self.layout
        ob = context.object
        if ob:
            rig = ob.parent
        else:
            rig = None
        scn = context.scene
        if not utils.drawConfirm(layout, scn):
            return

        if Thomas:
            layout.label("Pruning")
            row = layout.row()
            row.prop(ob, "MhPruneEnabled")
            row.prop(ob, "MhPruneWholeDir")
            row.prop(ob, "MhPruneRecursively")
            layout.operator("mh.prune_target_file")

        if not utils.isBaseOrTarget(ob):
            layout.operator("mh.import_base_obj")
            layout.operator("mh.import_base_mhclo")
            layout.operator("mh.make_base_obj")

        elif utils.isBase(ob):
            layout.label("Load Target")
            layout.operator("mh.new_target")
            layout.operator("mh.load_target")            
            layout.operator("mh.load_target_from_mesh")                        

        elif utils.isTarget(ob):
            if not ob.data.shape_keys:
                layout.label("Warning: Internal inconsistency")
                layout.operator("mh.fix_inconsistency")
                return
            layout.separator()
            box = layout.box()
            n = 0
            for skey in ob.data.shape_keys.key_blocks:
                if n == 0:
                    n += 1
                    continue
                row = box.row()
                if n == ob.active_shape_key_index:
                    icon='LAMP'
                else:
                    icon='X'
                row.label("", icon=icon)
                row.prop(skey, "value", text=skey.name)
                n += 1

            layout.label("Load Target")
            layout.operator("mh.new_target", text="New Secondary Target")
            layout.operator("mh.load_target", text="Load Secondary From File")            
            layout.operator("mh.load_target_from_mesh", text="Load Secondary From Mesh")    
            ext = os.path.splitext(ob.MhFilePath)[1]
            if ext == ".mhclo":
                layout.operator("mh.fit_target")

            layout.label("Discard And Apply Target")
            layout.operator("mh.discard_target")
            layout.operator("mh.discard_all_targets")
            layout.operator("mh.apply_targets")

            layout.label("Symmetry")
            row = layout.row()            
            row.operator("mh.symmetrize_target", text="Left->Right").action = "Left"
            row.operator("mh.symmetrize_target", text="Right->Left").action = "Right"
            if Thomas:
                row.operator("mh.symmetrize_target", text="Mirror").action = "Mirror"

            layout.label("Save Target")            
            layout.prop(ob, "SelectedOnly")
            layout.prop(ob, "MhZeroOtherTargets")
            if ob["FilePath"]:
                layout.operator("mh.save_target")           
            layout.operator("mh.saveas_target")       

            if not ob.MhDeleteHelpers:
                layout.label("Skirt Editing")
                layout.operator("mh.snap_waist")
                layout.operator("mh.straighten_skirt")            
                if ob.MhIrrelevantDeleted:
                    layout.separator()
                    layout.label("Only %s Affected" % ob.MhAffectOnly)
                else:
                    layout.label("Affect Only:")
                    layout.prop(ob, "MhAffectOnly", expand=True)
                    #layout.operator("mh.delete_irrelevant")  
                

        if rig and rig.type == 'ARMATURE':
            layout.separator()
            layout.label("Export/Import MHP")
            layout.operator("mh.saveas_mhp")
            layout.operator("mh.load_mhp")

            layout.separator()
            layout.label("Export/Import BVH")
            layout.prop(scn, "MhExportRotateMode")
            layout.operator("mh.saveas_bvh")
            layout.operator("mh.load_bvh")

            layout.separator()
            layout.label("Convert between rig weights")
            layout.prop(scn, "MhSourceRig")
            layout.prop(scn, "MhTargetRig")
            layout.prop(scn, "MhPoseTargetDir")            
            layout.operator("mh.convert_rig")

#----------------------------------------------------------
#   class MakeTargetBatchPanel(bpy.types.Panel):
#----------------------------------------------------------

class MakeTargetBatchPanel(bpy.types.Panel):
    bl_label = "Batch make targets"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_options = {'DEFAULT_CLOSED'}
    
    @classmethod
    def poll(self, context):
        return context.scene.MhUnlock and maketarget.isInited(context.scene)
        
    def draw(self, context):
        if utils.isBase(context.object):
            layout = self.layout
            scn = context.scene
            #for fname in maketarget.TargetSubPaths:
            #    layout.prop(scn, "Mh%s" % fname)
            layout.prop(scn, "MhTargetPath")
            layout.operator("mh.batch_fix")
            layout.operator("mh.batch_render", text="Batch Render").opengl = False
            layout.operator("mh.batch_render", text="Batch OpenGL Render").opengl = True
  
#----------------------------------------------------------
#   class ExportObj(bpy.types.Operator, ExportHelper):
#----------------------------------------------------------

class ExportObj(bpy.types.Operator, ExportHelper):
    '''Export to OBJ file format (.obj)''' 
    bl_idname = "mh.export_obj"
    bl_description = 'Export to OBJ file format (.obj)'
    bl_label = "Export MH OBJ"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"

    filename_ext = ".obj"
    filter_glob = StringProperty(default="*.obj", options={'HIDDEN'})
    filepath = StringProperty(name="File Path", description="File path for the exported OBJ file", maxlen= 1024, default= "")
    
    groupsAsMaterials = BoolProperty(name="Groups as materials", default=False)
 
    def execute(self, context):        
        export_mh_obj.exportObjFile(self.properties.filepath, self.groupsAsMaterials, context)
        return {'FINISHED'}
 
    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}
 
#----------------------------------------------------------
#   Settings buttons
#----------------------------------------------------------

class OBJECT_OT_FactorySettingsButton(bpy.types.Operator):
    bl_idname = "mh.factory_settings"
    bl_label = "Restore Factory Settings"

    def execute(self, context):
        mh_utils.settings.restoreFactorySettings(context)
        return{'FINISHED'}    


class OBJECT_OT_SaveSettingsButton(bpy.types.Operator):
    bl_idname = "mh.save_settings"
    bl_label = "Save Settings"

    def execute(self, context):
        mh_utils.settings.saveDefaultSettings(context)
        return{'FINISHED'}    


class OBJECT_OT_ReadSettingsButton(bpy.types.Operator):
    bl_idname = "mh.read_settings"
    bl_label = "Read Settings"

    def execute(self, context):
        mh_utils.settings.readDefaultSettings(context)
        return{'FINISHED'}    

#----------------------------------------------------------
#   Register
#----------------------------------------------------------

def menu_func(self, context):
    self.layout.operator(ExportObj.bl_idname, text="MakeHuman OBJ (.obj)...")
 
def register():
    mh_utils.init()
    maketarget.init()
    convert.init()
    pose.init()
    try:
        maketarget.initBatch(bpy.context.scene)
    except:
        pass
    bpy.utils.register_module(__name__)
    bpy.types.INFO_MT_file_export.append(menu_func)
  
def unregister():
    bpy.utils.unregister_module(__name__)
    bpy.types.INFO_MT_file_export.remove(menu_func)
 
if __name__ == "__main__":
    register()
