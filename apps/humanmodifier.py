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

__docformat__ = 'restructuredtext'

import algos3d
import gui3d
import events3d
import operator
import math
import re
import numpy as np
import gui
import log
import targets

# Gender
# -
# female	1.0	0.5	1.0
# male		0.0	0.5	1.0

# Age
# -
# child		1.0	0.0	0.0
# young		0.0	1.0	0.0
# old		0.0	0.0	1.0

# Weight
# -
# light		1.0	0.0	0.0
# averageWeight	0.0	1.0	0.0
# heavy		0.0	0.0	1.0

# Muscle
# -
# flaccid	1.0	0.0	0.0
# averageTone	0.0	1.0	0.0
# muscle	0.0	0.0	1.0

# Height
# -
# dwarf		1.0	0.0	0.0
# giant		0.0	0.0	1.0

# BreastFirmness
# -
# firmness0	1.0	0.5	1.0
# firmness1	0.0	0.5	1.0

# BreastSize
# -
# cup1		1.0	0.0	0.0
# cup2		0.0	0.0	1.0

# African

# Asian

# Caucasian

class DetailAction(gui3d.Action):
    def __init__(self, human, before, after, update=True):
        super(DetailAction, self).__init__('Change detail')
        self.human = human
        self.before = before
        self.after = after
        self.update = update

    def do(self):
        for (target, value) in self.after.iteritems():
            self.human.setDetail(target, value)
        self.human.applyAllTargets(gui3d.app.progress, update=self.update)
        return True

    def undo(self):
        for (target, value) in self.before.iteritems():
            self.human.setDetail(target, value)
        self.human.applyAllTargets()
        return True

class ModifierAction(gui3d.Action):
    def __init__(self, human, modifier, before, after, postAction):
        super(ModifierAction, self).__init__('Change modifier')
        self.human = human
        self.modifier = modifier
        self.before = before
        self.after = after
        self.postAction = postAction

    def do(self):
        self.modifier.setValue(self.human, self.after)
        self.human.applyAllTargets(gui3d.app.progress)
        self.postAction()
        return True

    def undo(self):
        self.modifier.setValue(self.human, self.before)
        self.human.applyAllTargets(gui3d.app.progress)
        self.postAction()
        return True
        
class ModifierSlider(gui.Slider):
    
    def __init__(self, value=0.0, min=0.0, max=1.0, label=None, modifier=None, valueConverter=None,
                 warpResetNeeded=True, image=None):
        super(ModifierSlider, self).__init__(value, min, max, label, valueConverter=valueConverter, image=image)
        self.modifier = modifier
        self.value = None
        self.warpResetNeeded = warpResetNeeded
        self.changing = None
        
    def onChanging(self, value):
        if self.changing is not None:
            self.changing = value
            return
        self.changing = value
        gui3d.app.callAsync(self._onChanging)
        
    def _onChanging(self):
        value = self.changing
        self.changing = None
        if gui3d.app.settings.get('realtimeUpdates', True):
            human = gui3d.app.selectedHuman
            if self.value is None:
                self.value = self.modifier.getValue(human)
                if human.isSubdivided():
                    if human.isProxied():
                        human.getProxyMesh().setVisibility(1)
                    else:
                        human.getSeedMesh().setVisibility(1)
                    human.getSubdivisionMesh(False).setVisibility(0)
            self.modifier.updateValue(human, value, gui3d.app.settings.get('realtimeNormalUpdates', True))
            human.updateProxyMesh()
            human.warpsNeedReset = self.warpResetNeeded
            
    def onChange(self, value):
        
        human = gui3d.app.selectedHuman
        if self.value is None:
            self.value = self.modifier.getValue(human)
        if self.value != value:
            gui3d.app.do(ModifierAction(human, self.modifier, self.value, value, self.update))
        if human.isSubdivided():
            if human.isProxied():
                human.getProxyMesh().setVisibility(0)
            else:
                human.getSeedMesh().setVisibility(0)
            human.getSubdivisionMesh(False).setVisibility(1)
        self.value = None
        human.warpsNeedReset = self.warpResetNeeded
        
    def update(self):
        
        human = gui3d.app.selectedHuman
        self.setValue(self.modifier.getValue(human))

class GenericSlider(ModifierSlider):
    @staticmethod
    def findImage(name):
        if name is None:
            return None
        name = name.lower()
        return targets.getTargets().images.get(name, name)

    def __init__(self, min, max, modifier, label, image, view):
        image = self.findImage(image)
        super(GenericSlider, self).__init__(min=min, max=max, label=label, modifier=modifier, image=image)
        self.view = getattr(gui3d.app, view)

    def onFocus(self, event):
        super(GenericSlider, self).onFocus(event)
        if gui3d.app.settings.get('cameraAutoZoom', True):
            self.view()

class MacroSlider(GenericSlider):
    def __init__(self, modifier, label, image, view):
        super(MacroSlider, self).__init__(min=0.0, max=1.0, modifier=modifier, label=label, image=image, view=view)

class UniversalSlider(GenericSlider):
    def __init__(self, modifier, label, image, view):
        min = -1.0 if modifier.left is not None else 0.0
        super(UniversalSlider, self).__init__(min, 1.0, modifier, label, image, view)

class BaseModifier(object):

    def __init__(self):
        self.verts = None
        self.faces = None
        self.eventType = 'modifier'
        
    def setValue(self, human, value):
    
        value = self.clampValue(value)
        factors = self.getFactors(human, value)
        human.warpNeedReset = True
        
        for target in self.targets:
            human.setDetail(target[0], value * reduce(operator.mul, [factors[factor] for factor in target[1]]))
            
    def getValue(self, human):
        
        return sum([human.getDetail(target[0]) for target in self.targets])

    def buildLists(self):
        human = gui3d.app.selectedHuman
        # Collect vertex and face indices if we didn't yet
        if self.verts is None and self.faces is None:
            # Collect verts
            vmask = np.zeros(human.meshData.getVertexCount(), dtype=bool)
            for target in self.targets:
                t = algos3d.getTarget(human.meshData, target[0])
                vmask[t.verts] = True
            self.verts = np.argwhere(vmask)[...,0]
            del vmask

            # collect faces
            self.faces = human.meshData.getFacesForVertices(self.verts)

    def updateValue(self, human, value, updateNormals=1):
        if self.verts is None and self.faces is None:
            self.buildLists()

        # Update detail state
        old_detail = [human.getDetail(target[0]) for target in self.targets]
        self.setValue(human, value)
        new_detail = [human.getDetail(target[0]) for target in self.targets]

        # Apply changes
        for target, old, new in zip(self.targets, old_detail, new_detail):
            if new == old:
                continue
            algos3d.loadTranslationTarget(human.meshData, target[0], new - old, None, 0, 0)
        
        # Update vertices
        if updateNormals:
            human.meshData.calcNormals(1, 1, self.verts, self.faces)
        human.meshData.update(self.verts, updateNormals)
        human.warpNeedReset = True
        human.callEvent('onChanging', events3d.HumanEvent(human, self.eventType))

class Modifier(BaseModifier):

    def __init__(self, left, right):
        super(Modifier, self).__init__()
        self.left = left
        self.right = right
        self.targets = [[self.left], [self.right]]

    def setValue(self, human, value, update=1):
        
        value = max(-1.0, min(1.0, value))

        left = -value if value < 0.0 else 0.0
        right = value if value > 0.0 else 0.0
        
        human.setDetail(self.left, left)
        human.setDetail(self.right, right)

    def getValue(self, human):
        
        value = human.getDetail(self.left)
        if value:
            return -value
        value = human.getDetail(self.right)
        if value:
            return value
        else:
            return 0.0

class SimpleModifier(BaseModifier):
    # overrides

    def __init__(self, template):
        super(SimpleModifier, self).__init__()
        self.template = template
        self.targets = self.expandTemplate([(self.template, [])])

    def expandTemplate(self, targets):
        
        targets = [(target[0], target[1] + ['dummy']) for target in targets]
        
        return targets
    
    def getFactors(self, human, value):
        
        factors = {
            'dummy': 1.0
        }
        
        return factors
    
    def clampValue(self, value):
        return max(0.0, min(1.0, value))

class GenericModifier(BaseModifier):
    @staticmethod
    def findTargets(path):
        if path is None:
            return []
        path = tuple(path.split('-'))
        result = []
        if path not in targets.getTargets().groups:
            log.debug('missing target %s', path)
        for target in targets.getTargets().groups.get(path, []):
            keys = [var
                    for var in target.data.itervalues()
                    if var is not None]
            keys.append('-'.join(target.key))
            result.append((target.path, keys))
        return result

    def clampValue(self, value):
        value = min(1.0, value)
        if self.left is not None:
            value = max(-1.0, value)
        else:
            value = max( 0.0, value)
        return value

    def setValue(self, human, value):
        value = self.clampValue(value)
        factors = self.getFactors(human, value)

        for tpath, tfactors in self.targets:
            human.setDetail(tpath, reduce((lambda x, y: x * y), [factors[factor] for factor in tfactors]))

    @staticmethod
    def parseTarget(target):
        return target[0].split('/')[-1].split('.')[0].split('-')

    def getValue(self, human):
        right = sum([human.getDetail(target[0]) for target in self.r_targets])
        if right:
            return right
        else:
            return -sum([human.getDetail(target[0]) for target in self.l_targets])

    _variables = [
        'female', 'male',
        'child', 'young', 'old',
        'flaccid', 'averageTone', 'muscle',
        'light', 'averageWeight', 'heavy',
        'dwarf', 'giant',
        'cup1', 'cup2',
        'firmness0', 'firmness1',
        'caucasian', 'african', 'asian'
        ]

    def getFactors(self, human, value):
        return dict((name, getattr(human, name + 'Val'))
                    for name in self._variables)

class UniversalModifier(GenericModifier):
    def __init__(self, left, right, center=None):
        super(UniversalModifier, self).__init__()

        self.left = left
        self.right = right
        self.center = center

        self.l_targets = self.findTargets(left)
        self.r_targets = self.findTargets(right)
        self.c_targets = self.findTargets(center)

        self.targets = self.l_targets + self.r_targets + self.c_targets

    def getFactors(self, human, value):
        factors = super(UniversalModifier, self).getFactors(human, value)

        if self.left is not None:
            factors[self.left] = -min(value, 0.0)
        if self.center is not None:
            factors[self.center] = 1.0 - abs(value)
        factors[self.right] = max(0.0, value)

        return factors

class MacroModifier(GenericModifier):
    def __init__(self, base, name, variable):
        super(MacroModifier, self).__init__()

        self.name = '-'.join(atom
                             for atom in (base, name)
                             if atom is not None)
        self.variable = variable
        self.setter = 'set' + self.variable
        self.getter = 'get' + self.variable

        self.targets = self.findTargets(self.name)
        # log.debug('macro modifier %s.%s(%s): %s', base, name, variable, self.targets)

    def getValue(self, human):
        return getattr(human, self.getter)()

    def setValue(self, human, value):
        value = self.clampValue(value)
        getattr(human, self.setter)(value)
        super(MacroModifier, self).setValue(human, value)

    def clampValue(self, value):
        return max(0.0, min(1.0, value))

    def getFactors(self, human, value):
        factors = super(MacroModifier, self).getFactors(human, value)
        factors[self.name] = 1.0
        return factors

    def buildLists(self):
        pass
