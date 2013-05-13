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

Definitions of scene objects and the scene class.
.mhscene file structure.
"""

import events3d
import pickle

mhscene_version = 3

class SceneObject(object):
    def __init__(self, scene = None, attributes = {}):
        object.__init__(self)
        self._attributes = attributes.keys()
        for attr in attributes.keys():
            setattr(self, "_" + attr, attributes[attr])
        self._scene = scene

    def __getattr__(self, attr):
        if attr in self._attributes:
            return SceneObject.__getattr__(self, "_" + attr)
        elif hasattr(self, attr):
            return getattr(self, attr)
        else:
            raise AttributeError('"%s" type scene objects do not have any "%s" attribute.' % (type(self), attr))

    def __setattr__(self, attr, value):
        if hasattr(self, "_attributes") and attr in self._attributes:
            if (SceneObject.__getattr__(self, "_" + attr) != value):
                SceneObject.__setattr__(self, "_" + attr, value)
                self.changed()
            else:
                self.changed(False)
        else:
            object.__setattr__(self, attr, value)
                
    def changed(self, modified = True):
        if (self._scene is not None):
            self._scene.changed(modified)
       
    def getAttributes(self):
        return self._attributes

    
class Light(SceneObject):
    def __init__(self, scene = None):
        SceneObject.__init__(
            self, scene,
            attributes =
            {'position': (-10.99, 20.0, 20.0),
             'focus': (0.0, 0.0, 0.0),
             'color': (1.0, 1.0, 1.0),
             'fov': 180.0,
             'attenuation': 0.0,
             'areaLights': 1,
             'areaLightSize': 4.0})


class Environment(SceneObject):
    def __init__(self, scene = None):
        SceneObject.__init__(
            self, scene,
            attributes =
            {'ambience': (0.1, 0.1, 0.1),
             'skybox': None})


class Scene(events3d.EventHandler):
    def __init__(self, path = None):
        if path is None:
            self.lights = [Light(self)]
            self.environment = Environment(self)
            
            self.unsaved = False
            self.path = None
        else:
            self.load(path)

    def changed(self, modified = True):
        self.unsaved = modified
        self.callEvent('onChanged', self)

    def load(self, path):   # Load scene from a .mhscene file.        
        hfile = open(self.path, 'rb')
        filever = pickle.load(hfile)
        if (filever < 3):   # Minimum supported version
            hfile.close()
            return
        self.unsaved = False
        self.path = path
        
        self.environment = pickle.load(hfile)
        nlig = pickle.load(hfile)
        self.lights = []
        for i in range(nlig):
            self.lights.append(pickle.load(hfile))
        hfile.close()

    def save(self, path = None):    # Save scene to a .mhscene file.
        if path is not None:
            self.path = path
        self.unsaved = False
        hfile = open(self.path, 'wb')
        pickle.dump(mhscene_version, hfile)
        
        pickle.dump(self.environment, hfile)
        pickle.dump(len(self.lights), hfile)
        for light in self.lights:
            pickle.dump(light, hfile)
        hfile.close()

    def close(self):
        self.__init__()

    def addLight(self):
        self.changed()
        newlight = Light(self)
        self.lights.append(newlight)

    def removeLight(self, light):
        self.changed()
        self.lights.remove(light)

