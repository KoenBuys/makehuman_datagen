#!/usr/bin/python
# -*- coding: utf-8 -*-

""" 
**Project Name:**      MakeHuman

**Product Home Page:** http://www.makehuman.org/

**Code Home Page:**    http://code.google.com/p/makehuman/

**Authors:**           Manuel Bastioni, Marc Flerackers

**Copyright(c):**      MakeHuman Team 2001-2013

**Licensing:**         AGPL3 (see also http://www.makehuman.org/node/318)

**Coding Standards:**  See http://www.makehuman.org/node/165

Abstract
--------

TODO
"""

import os
import gui3d
import gui
import log
import shader
import numpy as np

class ShaderTaskView(gui3d.TaskView):
    def __init__(self, category):
        gui3d.TaskView.__init__(self, category, 'Shaders')

        shaderBox = self.addLeftWidget(gui.GroupBox('Shader'))
        self.shaderList = shaderBox.addWidget(gui.ListView())
        self.shaderList.setSizePolicy(gui.SizePolicy.Ignored, gui.SizePolicy.Preferred)

        if not shader.Shader.supported():
            log.notice('Shaders not supported')
            self.shaderList.setEnabled(False)

        self.paramBox = self.addRightWidget(gui.GroupBox('Parameters'))

        @self.shaderList.mhEvent
        def onActivate(item):
            self.setShader(item.getUserData())

    def listShaders(self, dir = 'data/shaders/glsl'):
        shaders = set()
        for name in os.listdir(dir):
            path = os.path.join(dir, name)
            if not os.path.isfile(path):
                continue
            if not name.endswith('_shader.txt'):
                continue
            name, type = name[:-11].rsplit('_',1)
            if type not in ['vertex', 'geometry', 'fragment']:
                continue
            shaders.add(name)

        self.shaderList.clear()
        self.shaderList.addItem('[None]', data = '')
        for name in sorted(shaders):
            self.shaderList.addItem(name, data = os.path.join(dir, name))

    def setShader(self, path):
        gui3d.app.selectedHuman.mesh.setShader(path)

        for child in self.paramBox.children[:]:
            self.paramBox.removeWidget(child)

        if not path:
            return

        sh = shader.getShader(path)
        uniforms = sh.getUniforms()
        for index, uniform in enumerate(uniforms):
            if uniform.name.startswith('gl_'):
                continue
            self.paramBox.addWidget(UniformValue(uniform), index)

    def onShow(self, arg):
        super(ShaderTaskView, self).onShow(arg)
        self.listShaders()
        if not shader.Shader.supported():
            gui3d.app.statusPersist('Shaders not supported by OpenGL')

    def onHide(self, arg):
        gui3d.app.statusPersist('')
        super(ShaderTaskView, self).onHide(arg)

class UniformValue(gui.GroupBox):
    def __init__(self, uniform):
        super(UniformValue, self).__init__(uniform.name)
        self.uniform = uniform
        self.widgets = None
        self.create()

    def create(self):
        values = np.atleast_2d(self.uniform.values)
        rows, cols = values.shape
        self.widgets = []
        for row in xrange(rows):
            widgets = []
            for col in xrange(cols):
                child = self.createWidget(values[row,col], row)
                self.addWidget(child, row, col)
                widgets.append(child)
            self.widgets.append(widgets)

    def createWidget(self, value, row):
        type = self.uniform.pytype
        if type == int:
            return IntValue(self, value)
        if type == float:
            return FloatValue(self, value)
        if type == str:
            return TextureValue(self, value)
        if type == bool:
            return BooleanValue(self, value)
        return TextView('???')

    def onActivate(self, arg=None):
        values = [[widget.value
                   for widget in widgets]
                  for widgets in self.widgets]
        if len(self.uniform.dims) == 1:
            values = values[0]
            if self.uniform.dims == (1,) and self.uniform.pytype == str:
                values = values[0]
                if not os.path.isfile(values):
                    return
        gui3d.app.selectedHuman.mesh.setShaderParameter(self.uniform.name, values)

class NumberValue(gui.TextEdit):
    def __init__(self, parent, value):
        super(NumberValue, self).__init__(str(value), self._validator)
        self.parent = parent

    def onActivate(self, arg=None):
        self.parent.callEvent('onActivate', self.value)

class IntValue(NumberValue):
    _validator = gui.intValidator

    @property
    def value(self):
        return int(self.text)

class FloatValue(NumberValue):
    _validator = gui.floatValidator

    @property
    def value(self):
        return float(self.text)

class BooleanValue(gui.CheckBox):
    def __init__(self, parent, value):
        super(BooleanValue, self).__init__()
        self.parent = parent
        self.setSelected(value)

    def onClicked(self, arg=None):
        self.parent.callEvent('onActivate', self.value)

    @property
    def value(self):
        return self.selected

class TextureValue(gui.BrowseButton):
    def __init__(self, parent, value):
        super(TextureValue, self).__init__()
        self.parent = parent

    def onClicked(self, arg=None):
        self.parent.callEvent('onActivate', self.value)

    @property
    def value(self):
        return self._path

def load(app):
    category = app.getCategory('Settings')
    taskview = category.addTask(ShaderTaskView(category))

def unload(app):
    pass


