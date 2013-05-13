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

import os.path
import gui3d
import mh
import mh2proxy
import filechooser as fc
import log

class ProxyAction(gui3d.Action):
    def __init__(self, name, human, library, before, after):
        super(ProxyAction, self).__init__(name)
        self.human = human
        self.library = library
        self.before = before
        self.after = after

    def do(self):
        self.library.setProxy(self.human, self.after)
        return True

    def undo(self):
        self.library.setProxy(self.human, self.before)
        return True


class ProxyFileSort(fc.FileSort):
    
    def __init__(self):
        super(ProxyFileSort, self).__init__()
        self.meta = {}
    
    def fields(self):
        return list(super(ProxyFileSort, self).fields()) + ["faces"]
        
    def sortFaces(self, filenames):
        self.updateMeta(filenames)
        decorated = [(self.meta[filename]['faces'], i, filename) for i, filename in enumerate(filenames)]
        decorated.sort()
        return [filename for gender, i, filename in decorated]
        
    def updateMeta(self, filenames):
        for filename in filenames:
            if filename in self.meta:
                if self.meta[filename]['modified'] < os.path.getmtime(filename):
                    self.meta[filename] = self.getMeta(filename)
            else:
                self.meta[filename] = self.getMeta(filename)
                
    def getMeta(self, filename):
        meta = {}
        meta['modified'] = os.path.getmtime(filename)
        faces = 0
        try:
            f = open(filename.replace('.proxy', '.obj'))
            for line in f:
                lineData = line.split()
                if lineData and lineData[0] == 'f':
                    faces += 1
            f.close()
        except:
            pass
        meta['faces'] = faces

        return meta

class ProxyTaskView(gui3d.TaskView):
    
    def __init__(self, category):
        
        gui3d.TaskView.__init__(self, category, 'Proxies')
        self.installDir = 'data/proxymeshes'
        self.userDir = os.path.join(mh.getPath(''), 'data', 'proxymeshes')
        if not os.path.exists(self.userDir):
            os.makedirs(self.userDir)
        self.paths = [self.userDir , self.installDir]
        #self.filechooser = self.addTopWidget(fc.FileChooser(self.paths, 'proxy', 'thumb', 'data/proxymeshes/notfound.thumb', sort=ProxyFileSort()))
        #self.filechooser = self.addRightWidget(fc.ListFileChooser(self.paths, 'proxy', 'Proxy', sort=ProxyFileSort()))
        self.filechooser = self.addRightWidget(fc.IconListFileChooser(self.paths, 'proxy', 'thumb', 'data/proxymeshes/notfound.thumb', 'Proxy'))
        self.filechooser.setIconSize(50,50)
        self.addLeftWidget(self.filechooser.createSortBox())

        @self.filechooser.mhEvent
        def onFileSelected(filename):
            human = gui3d.app.selectedHuman
            if human.proxy:
                oldFile = human.proxy.file
            else:
                oldFile = "clear.proxy"
            gui3d.app.do(ProxyAction("Change proxy",
                human,
                self,
                oldFile,
                filename))
        
    def setProxy(self, human, filename):
        self.filechooser.selectItem(filename)

        if os.path.basename(filename) == "clear.proxy":
            human.setProxy(None)
            return

        proxy = mh2proxy.readProxyFile(human.getSeedMesh(), filename)        
        proxy.type = 'Proxy'
        human.setProxy(proxy)
        human.updateProxyMesh()

    def onShow(self, event):
        # When the task gets shown, set the focus to the file chooser
        gui3d.TaskView.onShow(self, event)
        self.filechooser.setFocus()

    def onHide(self, event):
        gui3d.TaskView.onHide(self, event)

    def onHumanChanging(self, event):
        
        human = event.human
        if event.change == 'reset':
            log.message('deleting proxy')
            human.setProxy(None)
            self.filechooser.deselectAll()
            
    def onHumanChanged(self, event):
        
        human = event.human

    def loadHandler(self, human, values):
        
        self.setProxy(human, values[1])
        
    def saveHandler(self, human, file):
        
        if human.proxy:
            file.write('proxy %s\n' % human.proxy.file)

# This method is called when the plugin is loaded into makehuman
# The app reference is passed so that a plugin can attach a new category, task, or other GUI elements


def load(app):
    category = app.getCategory('Geometries')
    taskview = ProxyTaskView(category)
    taskview.sortOrder = 3
    category.addTask(taskview)

    app.addLoadHandler('proxy', taskview.loadHandler)
    app.addSaveHandler(taskview.saveHandler)

# This method is called when the plugin is unloaded from makehuman
# At the moment this is not used, but in the future it will remove the added GUI elements


def unload(app):
    pass

