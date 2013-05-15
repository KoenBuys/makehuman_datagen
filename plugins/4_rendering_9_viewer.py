#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
**Project Name:**      MakeHuman

**Product Home Page:** http://www.makehuman.org/

**Code Home Page:**    http://code.google.com/p/makehuman/

**Authors:**           Glynn Clements

**Copyright(c):**      MakeHuman Team 2001-2013

**Licensing:**         AGPL3 (see also http://www.makehuman.org/node/318)

**Coding Standards:**  See http://www.makehuman.org/node/165

Abstract
--------

Image viewer plugin .
Useful for showing the rendering results.
It can also be used to view other MH related image files,
like textures, bump maps etc.
"""

import os
import shutil

import gui
import gui3d
import mh
import log

class ViewerTaskView(gui3d.TaskView):
    def __init__(self, category):
        super(ViewerTaskView, self).__init__(category, 'Viewer')
        self.image = self.addTopWidget(gui.ImageView())
        self.path = None

        tools = self.addLeftWidget(gui.GroupBox('Tools'))
        self.refrBtn = tools.addWidget(gui.Button('Refresh'))
        self.saveBtn = tools.addWidget(gui.Button('Save As...'))

        @self.saveBtn.mhEvent
        def onClicked(event):
            if not self.path:
                return
            filename = mh.getSaveFileName(os.path.splitext(self.path)[0],
                                          'PNG Image (*.png);;JPEG Image (*.jpg);;All files (*.*)')
            if filename:
                self.image.save(filename)

        @self.refrBtn.mhEvent
        def onClicked(event):
            if not self.path:
                return
            self.image.setImage(self.path)
                
    def setImage(self, path):
        self.path = path
        self.image.setImage(path)

def load(app):
    category = app.getCategory('Rendering')
    taskview = ViewerTaskView(category)
    taskview.sortOrder = 20.0
    category.addTask(taskview)

def unload(app):
    pass

