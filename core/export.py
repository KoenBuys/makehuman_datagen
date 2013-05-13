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

TODO
"""

import os
import gui
import gui3d
import log


class Exporter(object):
    def __init__(self):
        self.group = "mesh"

    def build(self, options, taskview):
        self.taskview       = taskview
        self.useTexFolder   = options.addWidget(gui.CheckBox("Separate texture folder", True))
        self.eyebrows       = options.addWidget(gui.CheckBox("Eyebrows", True))
        self.lashes         = options.addWidget(gui.CheckBox("Eyelashes", True))
        self.helpers        = options.addWidget(gui.CheckBox("Helper geometry", False))
        #self.hidden         = options.addWidget(gui.CheckBox("Keep hidden faces", True))
        #self.smooth         = options.addWidget(gui.CheckBox("Subdivide", False))
        #self.scales         = self.addScales(options)

    def export(self, human, filename):
        raise NotImplementedError()

    def getRigType(self):
        if not hasattr(gui3d.app.selectedHuman, "getSkeleton"):
            return None
        skel = gui3d.app.selectedHuman.getSkeleton()
        if skel:
            return skel.name
        else:
            return None

    def onShow(self, exportTaskView):
        """
        This method is called when this exporter is selected and shown in the 
        export GUI.
        """
        pass

    def onHide(self, exportTaskView):
        """
        This method is called when this exporter is hidden from the export GUI.
        """
        pass
