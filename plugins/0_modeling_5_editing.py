
import math
import os
import numpy as np
import events3d
import gui3d
import mh
import gui
import log
import module3d
import algos3d
import matrix

class EditTarget(algos3d.Target):
    _count = 0
    _path = None

    @classmethod
    def getName(cls):
        if cls._path is None:
            cls._path = os.path.join(mh.getPath(''), "edits")
            if not os.path.isdir(cls._path):
                os.mkdir(cls._path)

        while True:
            name = os.path.join(cls._path, "edit%04d" % cls._count)
            if not os.path.exists(name + ".index.npy"):
                return name
            cls._count += 1

    def __init__(self, obj, verts, coords):
        self.name = self.getName()
        self.morphFactor = -1
        self.verts = verts.copy()
        self.data = coords.copy()
        self.faces = obj.getFacesForVertices(self.verts)

class EditAction(gui3d.Action):
    def __init__(self, human, targets, value, update=True):
        super(EditAction, self).__init__('Change detail')
        self.human = human
        self.targets = [(target, value, human.getDetail(target))
                        for target in targets]
        self.update = update

    def do(self):
        for target, new, old in self.targets:
            self.human.setDetail(target, new)
        self.human.applyAllTargets(gui3d.app.progress, update=self.update)
        return True

    def undo(self):
        for target, new, old in self.targets:
            self.human.setDetail(target, old)
        self.human.applyAllTargets()
        return True

class ValueConverter(object):
    def dataToDisplay(self, value):
        return 2 ** value

    def displayToData(self, value):
        return math.log(value, 2)

class EditingTaskView(gui3d.TaskView):

    def __init__(self, category):
        gui3d.TaskView.__init__(self, category, 'Proportional editing', label='Edit')

        self.radius = 1.0
        self.start = None
        self.center = None
        self.axis = None
        self.depth = None
        self.original = None
        self.normals = None
        self.weights = None
        self.verts = None
        self.faces = None
        self.smoothed = None

        self.converter = ValueConverter()
        value = self.converter.displayToData(self.radius)
        self.radiusSlider = self.addLeftWidget(gui.Slider(value, min=-5.0, max=3.0, label="Radius",
                                                          valueConverter=self.converter))
        self.clear = self.addLeftWidget(gui.Button("Clear"))
        self.modeBox = self.addLeftWidget(gui.GroupBox("Mode"))
        modes = []
        self.grab = self.modeBox.addWidget(gui.RadioButton(modes, "Grab", selected=True))
        self.norm = self.modeBox.addWidget(gui.RadioButton(modes, "Normal"))
        self.scalex = self.modeBox.addWidget(gui.RadioButton(modes, "Scale X"))
        self.scaley = self.modeBox.addWidget(gui.RadioButton(modes, "Scale Y"))
        self.scalez = self.modeBox.addWidget(gui.RadioButton(modes, "Scale Z"))
        self.rotate = self.modeBox.addWidget(gui.RadioButton(modes, "Rotate"))
        self.smooth = self.modeBox.addWidget(gui.RadioButton(modes, "Smooth"))

        self.buildCircle()
        self.updateRadius()

        self.circle = self.addObject(gui3d.Object([0, 0, 0], self.circleMesh))

        @self.clear.mhEvent
        def onClicked(dummy):
            human = gui3d.app.selectedHuman
            targets = []
            for name in human.targetsDetailStack.keys():
                if isinstance(algos3d.getTarget(human, name), EditTarget):
                    targets.append(name)
            gui3d.app.do(EditAction(human, targets, 0.0))

        @self.radiusSlider.mhEvent
        def onChanging(value):
            self.radius = self.converter.dataToDisplay(value)
            self.updateRadius()

        @self.radiusSlider.mhEvent
        def onChange(value):
            self.radius = self.converter.dataToDisplay(value)
            self.updateRadius()

    def buildCircle(self):
        self.circleMesh = module3d.Object3D('circle', 2)
        fg = self.circleMesh.createFaceGroup('circle')

        self.circleMesh.setCoords(np.zeros((180, 3), dtype=np.float32))
        self.circleMesh.setUVs(np.zeros((1, 2), dtype=np.float32))
        ix = np.arange(180)
        faces = np.vstack((ix, np.roll(ix,-1))).transpose()
        self.circleMesh.setFaces(faces)

        self.circleMesh.setCameraProjection(0)
        self.circleMesh.setShadeless(True)
        self.circleMesh.setDepthless(True)
        self.circleMesh.setColor([0, 255, 255, 255])
        self.circleMesh.setPickable(0)
        self.circleMesh.updateIndexBuffer()
        self.circleMesh.priority = 50

    def updateRadius(self):
        angle = np.arange(0,360,2) * np.pi / 180
        coord = np.vstack((np.cos(angle), np.sin(angle), np.zeros_like(angle))).transpose()
        coord *= self.radius
        self.circleMesh.changeCoords(coord)
        self.circleMesh.update()

    def updatePosition(self, x, y):
        pos = gui3d.app.modelCamera.convertToWorld2D(x, y)
        self.circle.setPosition(pos)

    def onMouseDown(self, event):
        if gui3d.app.getSelectedFaceGroupAndObject() is None:
            return
        if event.button != mh.Buttons.LEFT:
            return

        human = gui3d.app.selectedHuman

        x, y, z = gui3d.app.modelCamera.convertToWorld2D(event.x, event.y, human.mesh)
        center = np.array([x, y, z])
        _, _, depth = gui3d.app.modelCamera.convertToScreen(x, y, z, human.mesh)
        x1, y1, z1 = gui3d.app.modelCamera.convertToWorld3D(event.x, event.y, depth + 0.1, human.mesh)
        axis = np.array([x1-x, y1-y, z1-z])
        log.debug("axis: %s", axis)

        distance2 = np.sum((human.meshData.coord - center[None,:]) ** 2, axis=-1)
        verts = np.argwhere(distance2 < (self.radius ** 2))
        if not len(verts):
            return

        self.start = (event.x, event.y)
        self.center = center
        self.axis = axis
        self.depth = depth
        self.verts = verts[:,0]
        self.weights = self.falloff(np.sqrt(distance2[self.verts]) / self.radius)
        self.original = human.meshData.coord[self.verts]
        self.normals = human.meshData.vnorm[self.verts]
        self.faces = human.meshData.getFacesForVertices(self.verts)

    @staticmethod
    def falloff(x):
        return (2 * x - 3) * x ** 2 + 1

    def onMouseMoved(self, event):
        self.updatePosition(event.x, event.y)
        human = gui3d.app.selectedHuman
        picked = gui3d.app.getSelectedFaceGroupAndObject()
        if picked is None:
            self.circle.hide()
        else:
            self.circle.show()

    def scale(self, vector, factor):
        vector = np.array(vector, dtype=np.float32)
        ones = 1 - vector
        scale = 2 ** (factor * self.weights[:,None])
        return self.center + (ones + vector * scale) * (self.original - self.center)

    def makeSmoothed(self):
        mesh = gui3d.app.selectedHuman.meshData
        fvert = mesh.fvert[self.faces,:]
        edges = np.dstack((fvert, np.roll(fvert, -1, -1)))
        mid = np.sum(mesh.coord[edges], axis=2) / 2
        mid = np.concatenate((mid[:,:,None,:], mid[:,:,None,:]), axis=2).reshape((-1,3))
        evert = edges.reshape((-1))
        ix = np.argsort(evert)
        evert = evert[ix]
        mid = mid[ix]
        ix, start = np.unique(evert, return_index=True)
        end = np.hstack((start[1:], len(evert)))
        count = end - start
        tvert = {}
        for i, s, n in zip(ix, start, count):
            tvert[i] = np.sum(mid[s:s+n,:], axis=0) / n
        verts = np.empty((len(self.verts), 3), dtype=np.float32)
        for i, v in enumerate(self.verts):
            verts[i] = tvert[v]
        return verts

    def onMouseDragged(self, event):
        self.updatePosition(event.x, event.y)

        if self.start is None or self.center is None or self.depth is None:
            return

        human = gui3d.app.selectedHuman

        dist = (event.x - self.start[0]) / 100.0

        if self.norm.selected:
            coord = self.original + dist * self.weights[:,None] * self.normals
        elif self.scalex.selected:
            coord = self.scale([1, 0, 0], dist)
        elif self.scaley.selected:
            coord = self.scale([0, 1, 0], dist)
        elif self.scalez.selected:
            coord = self.scale([0, 0, 1], dist)
        elif self.rotate.selected:
            mat = matrix.rotate(-dist * 90, self.axis)
            mat = np.asarray(mat)[:3,:3]
            coor = self.original - self.center
            coor = np.dot(mat, coor.T).T
            coor += self.center
            delta = coor - self.original
            coord = self.original + self.weights[:,None] * delta
        elif self.smooth.selected:
            if self.smoothed is None:
                self.smoothed = self.makeSmoothed()
            dist = min(1.0, max(0.0, dist))
            coord = self.original + self.weights[:,None] * dist * (self.smoothed - self.original)
        else:
            x, y, z = gui3d.app.modelCamera.convertToWorld3D(event.x, event.y, self.depth, human.mesh)
            pos = np.array([x, y, z])
            delta = pos - self.center
            coord = self.original + delta[None,:] * self.weights[:,None]

        human.meshData.changeCoords(coord, self.verts)
        human.meshData.calcNormals(True, True, self.verts, self.faces)
        human.meshData.update()
        mh.redraw()

    def onMouseUp(self, event):
        if self.start is None or self.center is None or self.depth is None:
            return

        human = gui3d.app.selectedHuman
        morph = EditTarget(human.meshData, self.verts,
                           human.meshData.coord[self.verts] - self.original)
        algos3d.targetBuffer[morph.name] = morph
        morph._save_binary(morph.name)
        gui3d.app.do(EditAction(human, [morph.name], 1.0))

        self.start = None
        self.center = None
        self.axis = None
        self.depth = None
        self.original = None
        self.normals = None
        self.weights = None
        self.verts = None
        self.faces = None
        self.smoothed = None

    def onMouseWheel(self, event):
        value = self.radiusSlider.getValue()
        value += 0.1 * event.wheelDelta
        self.radiusSlider.setValue(value)
        value = self.radiusSlider.getValue()
        self.radiusSlider.callEvent('onChanging', value)

def load(app):
    category = app.getCategory('Modelling')
    taskview = category.addTask(EditingTaskView(category))

def unload(app):
    pass
