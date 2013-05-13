#!/usr/bin/python
# -*- coding: utf-8 -*-

""" 
**Project Name:**      MakeHuman

**Product Home Page:** http://www.makehuman.org/

**Code Home Page:**    http://code.google.com/p/makehuman/

**Authors:**           Thanasis Papoutsidakis

**Copyright(c):**      MakeHuman Team 2001-2013

**Licensing:**         AGPL3 (see also http://www.makehuman.org/node/318)

**Coding Standards:**  See http://www.makehuman.org/node/165

Abstract
--------

Scene editor plugin.

This editor can create, load, edit and save .mhscene files,
and has tools to alter the scene's characteristics,
like lights and ambience, that are defined in the scene class.

"""

import mh
import gui
import gui3d

import os
import scene


class SceneItem(object):
    def __init__(self, sceneview):
        # Call this last
        self.sceneview = sceneview
        self.widget = gui.GroupBox()
        self.makeProps()

    def makeProps(self):
        pass

    def showProps(self):
        self.sceneview.propsBox.showWidget(self.widget)
        self.sceneview.activeItem = self

    def update(self):
        pass

    def __del__(self):
        self.widget.destroy()

            
class SceneItemAdder(SceneItem):
    # Virtual scene item for adding scene items.
    def __init__(self, sceneview):
        SceneItem.__init__(self, sceneview)

    def makeProps(self):
        SceneItem.makeProps(self)
        self.lightbtn = self.widget.addWidget(gui.Button('Add light'))

        @self.lightbtn.mhEvent
        def onClicked(event):
            self.sceneview.scene.addLight()
            self.sceneview.readScene()


class EnvironmentSceneItem(SceneItem):
    def __init__(self, sceneview):
        SceneItem.__init__(self, sceneview)

    def makeProps(self):
        SceneItem.makeProps(self)

        self.widget.addWidget(gui.TextView("Ambience"))
        self.colbox = self.widget.addWidget(gui.TextEdit(
            ", ".join([str(x) for x in self.sceneview.scene.environment.ambience])))

        @self.colbox.mhEvent
        def onChange(value):
            try:
                value = value.replace(" ", "")
                self.sceneview.scene.environment.ambience = tuple([float(x) for x in value.split(",")])
            except:
                pass
            
     
class LightSceneItem(SceneItem):
    def __init__(self, sceneview, light, lid):
        self.lightid = lid
        self.light = light
        SceneItem.__init__(self, sceneview)

    def makeProps(self):
        SceneItem.makeProps(self)
        
        self.widget.addWidget(gui.TextView("Position"))
        self.posbox = self.widget.addWidget(gui.TextEdit(
            ", ".join([str(x) for x in self.light.position])))
        
        self.widget.addWidget(gui.TextView("Focus"))
        self.focbox = self.widget.addWidget(gui.TextEdit(
            ", ".join([str(x) for x in self.light.focus])))
        
        self.widget.addWidget(gui.TextView("Color"))
        self.colbox = self.widget.addWidget(gui.TextEdit(
            ", ".join([str(x) for x in self.light.color])))
        
        self.widget.addWidget(gui.TextView("Spot angle"))
        self.fov = self.widget.addWidget(gui.TextEdit(str(self.light.fov)))

        self.widget.addWidget(gui.TextView("Attenuation"))
        self.att = self.widget.addWidget(gui.TextEdit(str(self.light.attenuation)))

        self.soft = self.widget.addWidget(gui.CheckBox("Soft light", self.light.areaLights > 1))
        self.widget.addWidget(gui.TextView("Softness"))
        self.size = self.widget.addWidget(gui.TextEdit(str(self.light.areaLightSize)))

        self.widget.addWidget(gui.TextView("Samples"))
        self.samples = self.widget.addWidget(gui.TextEdit(str(self.light.areaLights)))

        self.removebtn = self.widget.addWidget(
            gui.Button('Remove light ' + str(self.lightid)))

        @self.posbox.mhEvent
        def onChange(value):
            try:
                value = value.replace(" ", "")
                self.light.position = tuple([float(x) for x in value.split(",")])
            except: # The user hasn't typed the value correctly yet.
                pass

        @self.focbox.mhEvent
        def onChange(value):
            try:
                value = value.replace(" ", "")
                self.light.focus = tuple([float(x) for x in value.split(",")])
            except:
                pass

        @self.colbox.mhEvent
        def onChange(value):
            try:
                value = value.replace(" ", "")
                self.light.color = tuple([float(x) for x in value.split(",")])
            except:
                pass

        @self.fov.mhEvent
        def onChange(value):
            try:
                value = value.replace(" ", "")
                self.light.fov = float(value)
            except:
                pass

        @self.att.mhEvent
        def onChange(value):
            try:
                value = value.replace(" ", "")
                self.light.attenuation = float(value)
            except:
                pass

        @self.soft.mhEvent
        def onClicked(event):
            try:
                if self.soft.checkState() and self.light.areaLights <= 1:
                    self.light.areaLights = 2
                    self.samples.setText(str(2))
                elif self.soft.checkState() == 0 and self.light.areaLights > 1:
                    self.light.areaLights = 1
                    self.samples.setText(str(1))
            except:
                pass

        @self.size.mhEvent
        def onChange(value):
            try:
                value = value.replace(" ", "")
                self.light.attenuation = float(value)
            except:
                pass

        @self.samples.mhEvent
        def onChange(value):
            try:
                value = value.replace(" ", "")
                alights = int(value)
                self.light.areaLights = alights
                if alights>1:
                    self.soft.setCheckState(2)
                else:
                    self.soft.setCheckState(0)
            except:
                pass
            
        @self.removebtn.mhEvent
        def onClicked(event):
            self.sceneview.scene.removeLight(self.light)
            self.sceneview.readScene()


class SceneEditorTaskView(gui3d.TaskView):

    def __init__(self, category):
        gui3d.TaskView.__init__(self, category, 'Scene Editor')
        sceneBox = self.addLeftWidget(gui.GroupBox('Scene'))
        self.fnlbl = sceneBox.addWidget(gui.TextView('<New scene>'))
        self.saveButton = sceneBox.addWidget(gui.Button('Save'), 1, 0)
        self.loadButton = sceneBox.addWidget(gui.Button('Load ...'), 1, 1)
        self.saveAsButton = sceneBox.addWidget(gui.Button('Save As...'), 2, 0)
        self.closeButton = sceneBox.addWidget(gui.Button('Close'), 2, 1)

        itemBox = self.addLeftWidget(gui.GroupBox('Items'))
        self.itemList = itemBox.addWidget(gui.ListView())
        self.itemList.setSizePolicy(gui.SizePolicy.Ignored, gui.SizePolicy.Preferred)

        self.propsBox = gui.StackedBox()
        self.addRightWidget(self.propsBox)

        self.addButton = itemBox.addWidget(gui.Button('Add...'))
        self.adder = SceneItemAdder(self)
        self.propsBox.addWidget(self.adder.widget)

        self.items = {}
        self.activeItem = None
        self.scene = scene.Scene()
        self.readScene()

        def doLoad():
            filename = mh.getOpenFileName(mh.getPath("scenes"), 'MakeHuman scene (*.mhscene);;All files (*.*)')
            if filename:
                self.scene.load(filename)
                self.readScene()

        @self.scene.mhEvent
        def onChanged(scene):
            self.updateFileTitle()

        @self.loadButton.mhEvent
        def onClicked(event):
            if self.scene.unsaved:
                gui3d.app.prompt('Confirmation',
                                 'Your scene is unsaved. Are you sure you want to close it?',
                                 'Close','Cancel',doLoad())
            else:
                doLoad()

        @self.saveButton.mhEvent
        def onClicked(event):
            if self.scene.path is None:
                self.saveAsButton.callEvent('onClicked', None)
            else:
                self.scene.save()
            self.updateFileTitle()

        @self.closeButton.mhEvent
        def onClicked(event):
            if self.scene.unsaved:
                gui3d.app.prompt('Confirmation',
                                 'Your scene is unsaved. Are you sure you want to close it?',
                                 'Close','Cancel',self.scene.close())
            else:
                self.scene.close()
            self.readScene()

        @self.saveAsButton.mhEvent
        def onClicked(event):
            filename = mh.getSaveFileName(mh.getPath("scenes"), 'MakeHuman scene (*.mhscene);;All files (*.*)')
            if filename:
                self.scene.save(filename)
            self.updateFileTitle()
                
        @self.itemList.mhEvent
        def onClicked(event):
            self.items[self.itemList.getSelectedItem()].showProps()

        @self.addButton.mhEvent
        def onClicked(event):
            self.adder.showProps()
            
    def readScene(self):
        self.adder.showProps()
        self.items.clear()
        self.items = {'Environment': EnvironmentSceneItem(self)}
        i = 0
        for light in self.scene.lights:
            i += 1
            self.items['Light ' + str(i)] = LightSceneItem(self, light, i)
        for item in self.items.values():
            self.propsBox.addWidget(item.widget)
        self.itemList.setData(self.items.keys()[::-1])
        self.updateFileTitle()

    def updateFileTitle(self):
        if self.scene.path is None:
            lbltxt = '<New scene>'
        else:
            lbltxt = os.path.basename(self.scene.path)
        if self.scene.unsaved:
            lbltxt += '*'
        self.fnlbl.setText(lbltxt)

        
def load(app):
    category = app.getCategory('Utilities')
    taskview = category.addTask(SceneEditorTaskView(category))

def unload(app):
    pass
