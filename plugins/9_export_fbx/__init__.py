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


class FbxConfig(Config):

    def __init__(self, exporter):
        Config.__init__(self)
        self.selectedOptions(exporter)
        
        self.useRelPaths     = False
        self.rigtype = exporter.getRigType()
        # FBX export does not support exporting without rig
        # If no rig selected (from library): default to soft1 rig
        if not self.rigtype:
            self.rigtype = "soft1"
        self.expressions     = exporter.expressions.selected
        self.useCustomShapes = exporter.useCustomShapes.selected
        
        
    def __repr__(self):
        return("<FbxOptions %s s %s e %s h %s>" % (
            self.rigtype, self.useTexFolder, self.expressions, self.helpers))


class ExporterFBX(Exporter):
    def __init__(self):
        Exporter.__init__(self)
        self.name = "Filmbox (fbx)"
        self.filter = "Filmbox (*.fbx)"

    def build(self, options, taskview):
        Exporter.build(self, options, taskview)
        self.expressions     = options.addWidget(gui.CheckBox("Expressions", False))
        self.useCustomShapes = options.addWidget(gui.CheckBox("Custom shapes", False))

    def export(self, human, filename):
        from . import mh2fbx

        mh2fbx.exportFbx(human, filename("fbx"), FbxConfig(self))

def load(app):
    app.addExporter(ExporterFBX())

def unload(app):
    pass
