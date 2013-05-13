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

TODO
"""

import gui
from export import Exporter
from exportutils.config import Config

class ObjConfig(Config):

    def __init__(self, exporter):
        Config.__init__(self)
        self.selectedOptions(exporter)
        self.useRelPaths = True
        self.useNormals = exporter.useNormals.selected
    
    
class ExporterOBJ(Exporter):
    def __init__(self):
        Exporter.__init__(self)
        self.name = "Wavefront obj"
        self.filter = "Wavefront (*.obj)"

    def build(self, options, taskview):
        Exporter.build(self, options, taskview)
        self.useNormals = options.addWidget(gui.CheckBox("Normals", False))

    def export(self, human, filename):
        from . import mh2obj

        mh2obj.exportObj(human, filename("obj"), ObjConfig(self))

def load(app):
    app.addExporter(ExporterOBJ())

def unload(app):
    pass
