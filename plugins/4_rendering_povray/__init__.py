#!/usr/bin/python
# -*- coding: utf-8 -*-

""" 
**Project Name:**      MakeHuman

**Product Home Page:** http://www.makehuman.org/

**Code Home Page:**    http://code.google.com/p/makehuman/

**Authors:**           Marc Flerackers

**Copyright(c):**      MakeHuman Team 2001-2013

**Licensing:**         AGPL3 (see also http://www.makehuman.org/node/318)

**Coding Standards:**  See http://www.makehuman.org/node/165

Abstract
--------

TODO
"""

import sys
import os

# We need this for rendering
from . import mh2povray

# We need this for gui controls
import gui3d
import gui

class PovrayTaskView(gui3d.TaskView):

    def __init__(self, category):
        gui3d.TaskView.__init__(self, category, 'Povray')
        
        # for path to PovRay binaries file
        binary = ''

        bintype = []
        pathBox = self.addLeftWidget(gui.GroupBox('Povray  bin  path'))
        # this part load old settings values for next session; str(povray_bin)
        povray_bin = gui3d.app.settings.get('povray_bin', '')
        self.path= pathBox.addWidget(gui.TextEdit(str(povray_bin)), 0, 0, 1, 2)
        self.browse = pathBox.addWidget(gui.BrowseButton('dir'), 1, 0, 1, 1)
        self.browse.setPath(povray_bin)
        if sys.platform == 'win32':
            self.browse.setFilter('Executable programs (*.exe);;All files (*.*)')
        
        #
        if os.name == 'nt':
            #
            if os.environ['PROCESSOR_ARCHITECTURE'] == 'x86':
                self.win32sse2Button = pathBox.addWidget(gui.CheckBox('Use SSE2 bin', True))
        #
        @self.path.mhEvent
        def onChange(value):
            gui3d.app.settings['povray_bin'] = 'Enter your path' if not value else str(value)

        @self.browse.mhEvent
        def onClicked(path):
            if os.path.isdir(path):
                gui3d.app.settings['povray_bin'] = path
                self.path.setText(path)
        #------------------------------------------------------------------------------------
        filter = []
        # Options box
        optionsBox = self.addLeftWidget(gui.GroupBox('Options'))
        self.doSubdivide = optionsBox.addWidget(gui.CheckBox('Subdivide mesh', True))
        self.usebump = optionsBox.addWidget(gui.CheckBox('Use bump maps', True))
        self.useSSS = optionsBox.addWidget(gui.CheckBox('Use S.S. Scattering', True))
        self.SSSA = optionsBox.addWidget(gui.Slider(value=0.5, label="SSS Amount"))

        settingsBox = self.addLeftWidget(gui.GroupBox('Settings'))
        settingsBox.addWidget(gui.TextView("Resolution"))
        self.resBox = settingsBox.addWidget(gui.TextEdit(
            "x".join([str(self.resWidth), str(self.resHeight)])))
        self.AA = settingsBox.addWidget(gui.Slider(value=0.5, label="AntiAliasing"))

        materialsBox = self.addRightWidget(gui.GroupBox('Materials'))
        self.skinoil = materialsBox.addWidget(gui.Slider(value=0.5, label="Skin oil"))
        self.moist = materialsBox.addWidget(gui.Slider(value=0.7, label="Moisturization"))
        self.tension = materialsBox.addWidget(gui.Slider(value=0.7, label="Skin tension"))
        self.grain = materialsBox.addWidget(gui.Slider(value=0.5, label="Skin graininess"))
        self.hairShine = materialsBox.addWidget(gui.CheckBox('Hair shine', False))
        self.hairSpec = materialsBox.addWidget(gui.Slider(value=0.45, label="Shine strength"))
        self.hairRough = materialsBox.addWidget(gui.Slider(value=0.4, label="Shine coverage"))
        self.hairHard = materialsBox.addWidget(gui.Slider(value=0.5, label="Hair hardness"))

        # box
        #optionsBox = self.addLeftWidget(gui.GroupBox('Options'))
        
        #Buttons
        # Simplified the gui a bit for the average user. Uncomment to clutter it up with developer - useful stuff.
        #source=[]
        #self.iniButton = optionsBox.addWidget(gui.RadioButton(source, 'Use ini settings'))
        #self.guiButton = optionsBox.addWidget(gui.RadioButton(source, 'Use gui settings', selected = True))
        #format=[]
        #self.arrayButton = optionsBox.addWidget(gui.RadioButton(format, 'Array  format'))
        #self.mesh2Button = optionsBox.addWidget(gui.RadioButton(format, 'Mesh2 format', selected = True))
        #action=[]
        #self.exportButton = optionsBox.addWidget(gui.RadioButton(action , 'Export only', selected = True))
        #self.exportandrenderButton = optionsBox.addWidget(gui.RadioButton(action , 'Export and render'))
        self.renderButton = optionsBox.addWidget(gui.Button('Render'))
        
        @self.resBox.mhEvent
        def onChange(value):
            try:
                value = value.replace(" ", "")
                res = [int(x) for x in value.split("x")]
                self.resWidth = res[0]
                self.resHeight = res[1]
            except: # The user hasn't typed the value correctly yet.
                pass

        #        
        @self.renderButton.mhEvent
        def onClicked(event):            
            reload(mh2povray)  # Avoid having to close and reopen MH for every coding change (can be removed once testing is complete)
            # it is necessary to put this code here, so that it is executed with the 'renderButton.event'
            if os.name == 'nt':
                #
                if os.environ['PROCESSOR_ARCHITECTURE'] == "x86":
                    binary = 'win32'
                    if self.win32sse2Button.selected:
                        binary = 'win32sse2'
                else:
                    binary = 'win64'
            # for Ubuntu.. atm
            if sys.platform == 'linux2':
                binary = 'linux'
            #
            mh2povray.povrayExport({'source':'gui',         # 'ini' if self.iniButton.selected else 'gui',
                                    'format':'mesh2',       # 'array' if self.arrayButton.selected else 'mesh2',
                                    'action':'render',      # 'export' if self.exportButton.selected else 'render',
                                    'scene': gui3d.app.getCategory('Rendering').getTaskByName('Scene').scene,
                                    'subdivide':True if self.doSubdivide.selected else False,
                                    'AA': 0.5-0.49*self.AA.getValue(),
                                    'bintype': binary,
                                    'SSS': True if self.useSSS.selected else False,
                                    'SSSA': self.SSSA.getValue(), # blur strength
                                    'skinoil': 0.001 *(10**(4*self.skinoil.getValue())), # exponential slider
                                    'moist': self.moist.getValue(), # percentage
                                    'rough':0.001 *(10**(2*(1-self.tension.getValue()))), # exponential slider
                                    'wrinkles': 0.5*self.grain.getValue(),
                                    'usebump': True if self.usebump.selected else False,
                                    'hairShine':True if self.hairShine.selected else False,
                                    'hairSpec': self.hairSpec.getValue(),
                                    'hairRough': (0.7*self.hairRough.getValue())**2,
                                    'hairHard': 0.01*10**(4*self.hairHard.getValue())}) # exponential slider 

    @property
    def resWidth(self):
        return gui3d.app.settings.get('rendering_width', 800)

    @property
    def resHeight(self):
        return gui3d.app.settings.get('rendering_height', 600)

    @resWidth.setter
    def resWidth(self, value = None):
        gui3d.app.settings['rendering_width'] = 0 if not value else int(value)

    @resHeight.setter
    def resHeight(self, value = None):
        gui3d.app.settings['rendering_height'] = 0 if not value else int(value)

    def onShow(self, event):
        self.renderButton.setFocus()
        gui3d.TaskView.onShow(self, event)


def load(app):
    category = app.getCategory('Rendering')
    taskview = PovrayTaskView(category)
    taskview.sortOrder = 2.0
    category.addTask(taskview)

def unload(app):
    pass
