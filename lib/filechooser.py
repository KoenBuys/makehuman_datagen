#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
Qt filechooser widget.

**Project Name:**      MakeHuman

**Product Home Page:** http://www.makehuman.org/

**Code Home Page:**    http://code.google.com/p/makehuman/

**Authors:**           Glynn Clements, Jonas Hauquier

**Copyright(c):**      MakeHuman Team 2001-2013

**Licensing:**         AGPL3 (see also http://www.makehuman.org/node/318)

**Coding Standards:**  See http://www.makehuman.org/node/165

Abstract
--------

A Qt based filechooser widget.
"""

import os

from PyQt4 import QtCore, QtGui

import qtgui as gui
import mh
import log

class ThumbnailCache(object):
    aspect_mode = QtCore.Qt.KeepAspectRatioByExpanding
    scale_mode = QtCore.Qt.SmoothTransformation

    def __init__(self, size):
        self.cache = {}
        self.size = size

    def __getitem__(self, name):
        nstat = os.stat(name)
        if name in self.cache:
            stat, pixmap = self.cache[name]
            if stat.st_size == nstat.st_size and stat.st_mtime == nstat.st_mtime:
                return pixmap
            else:
                del self.cache[name]
        pixmap = self.loadImage(name)
        self.cache[name] = (nstat, pixmap)
        return pixmap

    def loadImage(self, path):
        pixmap = QtGui.QPixmap(path)
        width, height = self.size
        pixmap = pixmap.scaled(width, height, self.aspect_mode, self.scale_mode)
        pwidth = pixmap.width()
        pheight = pixmap.height()
        if pwidth > width or pheight > height:
            x0 = max(0, (pwidth - width) / 2)
            y0 = max(0, (pheight - height) / 2)
            pixmap = pixmap.copy(x0, y0, width, height)
        return pixmap

class FileChooserRectangle(gui.Button):
    _size = (128, 128)
    _imageCache = ThumbnailCache(_size)

    def __init__(self, owner, file, label, imagePath):
        super(FileChooserRectangle, self).__init__()
        gui.Widget.__init__(self)
        self.owner = owner
        self.file = file

        self.layout = QtGui.QGridLayout(self)
        self.layout.setSizeConstraint(QtGui.QLayout.SetMinimumSize)

        image = self._imageCache[imagePath]
        self.preview = QtGui.QLabel()
        self.preview.setPixmap(image)
        self.layout.addWidget(self.preview, 0, 0)
        self.layout.setRowStretch(0, 1)
        self.layout.setColumnMinimumWidth(0, self._size[0])
        self.layout.setRowMinimumHeight(0, self._size[1])

        self.label = QtGui.QLabel()
        self.label.setText(label)
        self.label.setMinimumWidth(1)
        self.layout.addWidget(self.label, 1, 0)
        self.layout.setRowStretch(1, 0)

    def onClicked(self, event):
        self.owner.selection = self.file
        self.owner.callEvent('onFileSelected', self.file)

class FlowLayout(QtGui.QLayout):
    def __init__(self, parent = None):
        super(FlowLayout, self).__init__(parent)
        self._children = []

    def addItem(self, item):
        self._children.append(item)

    def count(self):
        return len(self._children)

    def itemAt(self, index):
        if index < 0 or index >= self.count():
            return None
        return self._children[index]

    def takeAt(self, index):
        child = self.itemAt(index)
        if child is not None:
            del self._children[index]
        return child

    def hasHeightForWidth(self):
        return True

    def _doLayout(self, width, real=False):
        x = 0
        y = 0
        rowHeight = 0
        for child in self._children:
            size = child.sizeHint()
            w = size.width()
            h = size.height()
            if x + w > width:
                x = 0
                y += rowHeight
                rowHeight = 0
            rowHeight = max(rowHeight, h)
            if real:
                child.setGeometry(QtCore.QRect(x, y, w, h))
            x += w
        return y + rowHeight

    def heightForWidth(self, width):
        return self._doLayout(width, False)

    def sizeHint(self):
        width = 0
        height = 0
        for child in self._children:
            size = child.sizeHint()
            w = size.width()
            h = size.height()
            width += w
            height = max(height, h)
        return QtCore.QSize(width, height)

    def setGeometry(self, rect):
        self._doLayout(rect.width(), True)

    def expandingDirections(self):
        return QtCore.Qt.Vertical

    def minimumSize(self):
        if not self._children:
            return QtCore.QSize(0, 0)
        return self._children[0].sizeHint()

class FileSort(object):
    """
    The default file sorting class. Can sort files on name, creation and modification date and size.
    """
    def __init__(self):
        pass
        
    def fields(self):
        """
        Returns the names of the fields on which this FileSort can sort. For each field it is assumed that the method called sortField exists.
        
        :return: The names of the fields on which this FileSort can sort.
        :rtype: list or tuple
        """
        return ("name", "created", "modified", "size")

    def sort(self, by, filenames):
        method = getattr(self, "sort%s" % by.capitalize())
        return method(filenames)
        
    def sortName(self, filenames):
        return sorted(filenames)
    def sortModified(self, filenames):
        decorated = [(os.path.getmtime(filename), i, filename) for i, filename in enumerate(filenames)]
        decorated.sort()
        return [filename for modified, i, filename in decorated]
        
    def sortCreated(self, filenames):
        decorated = [(os.path.getctime(filename), i, filename) for i, filename in enumerate(filenames)]
        decorated.sort()
        return [filename for created, i, filename in decorated]
    
    def sortSize(self, filenames):
        decorated = [(os.path.getsize(filename), i, filename) for i, filename in enumerate(filenames)]
        decorated.sort()
        return [filename for size, i, filename in decorated]

class FileSortRadioButton(gui.RadioButton):
    def __init__(self, chooser, group, selected, field):
        gui.RadioButton.__init__(self, group, "By %s" % field, selected)
        self.field = field
        self.chooser = chooser
        
    def onClicked(self, event):
        self.chooser.sortBy = self.field
        self.chooser.refresh()

class TagFilter(gui.GroupBox):
    def __init__(self):
        super(TagFilter, self).__init__('Tag filter')
        self.tags = set()
        self.selectedTags = set()
        self.tagToggles = []
        
    def setTags(self, tags):
        self.clearAll()
        for tag in tags:
            self.addTag(tag)

    # TODO case insensitive tags
    def addTag(self, tag):
        if tag in self.tags:
            return

        self.tags.add(tag)
        toggle = self.addWidget(gui.ToggleButton(tag))
        toggle.tag = tag

        @toggle.mhEvent
        def onClicked(event):
            self.setTagState(toggle.tag, toggle.selected)

    def addTags(self, tags):
        for tag in tags:
            self.addTag(tag)

    def setTagState(self, tag, enabled):
        if tag not in self.tags:
            return

        if enabled:
            self.selectedTags.add(tag)
        else:
            self.selectedTags.remove(tag)

        self.callEvent('onTagsChanged', self.selectedTags)

    def clearAll(self):
        for tggl in self.tagToggles:
            tggl.hide()
            tggl.destroy()
        self.tagToggles = []
        self.selectedTags.clear()
        self.tags.clear()

    def getSelectedTags(self):
        return self.selectedTags

    def getTags(self):
        return self.tags

    def filterActive(self):
        return len(self.getSelectedTags()) > 0

    def filter(self, items):
        if not self.filterActive():
            for item in items:
                item.setHidden(False)
            return

        for item in items:
            #if len(self.selectedTags.intersection(file.tags)) > 0:  # OR
            if len(self.selectedTags.intersection(item.tags)) == len(self.selectedTags):  # AND
                item.setHidden(False)
            else:
                item.setHidden(True)

class FileHandler(object):
    def __init__(self):
        self.fileChooser = None

    def refresh(self, files):
        for file in files:
            label = os.path.basename(file)
            if isinstance(self.fileChooser.extension, str):
                label = os.path.splitext(label)[0]
            self.fileChooser.addItem(file, label, self.fileChooser.getPreview(file))

    def getSelection(self, item):
        return item.file

    def matchesItem(self, listItem, item):
        return listItem.file == item

    def matchesItems(self, listItem, items):
        return listItem.file in items

    def setFileChooser(self, fileChooser):
        self.fileChooser = fileChooser

class MhcloFileLoader(FileHandler):

    def __init__(self):
        super(MhcloFileLoader, self).__init__()
        self.__tagsCache = {}

    def refresh(self, files):
        """
        Load tags from mhclo file.
        """
        import exportutils.config
        for file in files:
            label = os.path.basename(file)
            if self.fileChooser.multiSelect and label == "clear.mhclo":
                continue
            if isinstance(self.fileChooser.extension, str):
                label = os.path.splitext(label)[0]
            if not file in self.__tagsCache:
                tags = exportutils.config.scanFileForTags(file)
                self.__tagsCache[file] = tags
            else:
                tags = self.__tagsCache[file]
            self.fileChooser.addItem(file, label, self.fileChooser.getPreview(file), tags)

class FileChooserBase(QtGui.QWidget, gui.Widget):

    def __init__(self, path, extension, sort = FileSort()):
        super(FileChooserBase, self).__init__()
        gui.Widget.__init__(self)

        self.setPaths(path)
        self.extension = extension
        self.previewExtensions = None
        self.notFoundImage = None

        self.sort = sort
        self.sortBy = self.sort.fields()[0]
        self.sortgroup = []

        self.setFileLoadHandler(FileHandler())
        self.tagFilter = None

    def createSortBox(self):
        sortBox = gui.GroupBox('Sort')

        self.refreshButton = sortBox.addWidget(gui.Button('Refresh'))
        for i, field in enumerate(self.sort.fields()):
            sortBox.addWidget(FileSortRadioButton(self, self.sortgroup, i == 0, field))

        @self.refreshButton.mhEvent
        def onClicked(value):
            self.refresh()

        return sortBox

    def createTagFilter(self):
        self.tagFilter = TagFilter()
        @self.tagFilter.mhEvent
        def onTagsChanged(selectedTags):
            self.applyTagFilter()

        return self.tagFilter

    def setPaths(self, value):
        self.paths = value if isinstance(value, list) else [value]

    def setPreviewExtensions(self, value):
        if not value:
            self.previewExtensions = None
        elif isinstance(value, list):
            self.previewExtensions = value
        else:
            self.previewExtensions = [value]

    def _updateScrollBar(self):
        pass

    def eventFilter(self, object, event):
        if event.type() == QtCore.QEvent.Resize:
            mh.callAsync(self._updateScrollBar)
        return False
        
    def getPreview(self, filename):
        preview = filename
        
        if self.previewExtensions:
            #log.debug('%s, %s', self.extension, self.previewExtensions)
            preview = filename.replace('.' + self.extension, '.' + self.previewExtensions[0])
            i = 1
            while not os.path.exists(preview) and i < len(self.previewExtensions):
                preview = filename.replace('.' + self.extension, '.' + self.previewExtensions[i])
                i = i + 1
        else:
            preview = filename
            
        if not os.path.exists(preview) and self.notFoundImage:
            # preview = os.path.join(self.path, self.notFoundImage)
            # TL: full filepath needed, so we don't look into user dir.
            preview = self.notFoundImage

        return preview

    def search(self):
        if isinstance(self.extension, str):
            extensions = [self.extension]
        else:
            extensions = self.extension

        for path in self.paths:
            for root, dirs, files in os.walk(path):
                for f in files:
                    ext = os.path.splitext(f)[1][1:].lower()
                    if ext in self.extension:
                        if f.lower().endswith('.' + ext):
                            yield os.path.join(root, f)

    def clearList(self):
        for i in xrange(self.children.count()):
            child = self.children.itemAt(0)
            self.children.removeItem(child)
            child.widget().hide()
            child.widget().destroy()

    def refresh(self, keepSelections=True):
        self.clearList()

        files = self.sort.sort(self.sortBy, list(self.search()))
        self.loadHandler.refresh(files)

        self.applyTagFilter()

        mh.redraw()
        self.callEvent('onRefresh', self)

    def applyTagFilter(self):
        if not self.tagFilter:
            return
        self.tagFilter.filter(self.children.getItems())
        self.children.updateGeometry()

    def _getListItem(self, item):
        for listItem in self.children.getItems():
            if self.loadHandler.matchesItem(listItem, item):
                return listItem
        return None

    def addTags(self, item, tags):
        listItem = self._getListItem(item)
        if listItem:
            listItem.tags = listItem.tags.union(tags)

    def setTags(self, item, tags):
        listItem = self._getListItem(item)
        if listItem:
            listItem.tags = tags
        
    def getAllTags(self):
        tags = set()
        for listItem in self.children.getItems():
            tags = tags.union(listItem.tags)
        return tags

    def setFileLoadHandler(self, loadHandler):
        loadHandler.setFileChooser(self)
        self.loadHandler = loadHandler

    def addItem(self, file, label, preview, tags = []):
        if self.tagFilter:
            self.tagFilter.addTags(tags)
        return None

    def onShow(self, event):
        self.refresh()

class FileChooser(FileChooserBase):
    """
    A FileChooser widget. This widget can be used to let the user choose an existing file.
    
    :param path: The path from which the recursive search is started.
    :type path: str
    :param extension: The extension(s) of the files to display.
    :type extension: str or list
    :param previewExtension: The extension of the preview for the files. None if the file itself is to be used.
    :type previewExtension: str or None
    :param notFoundImage: The full filepath of the image to be used in case the preview is not found.
    :type notFoundImage: str or None
    :param sort: A file sorting instance which will be used to provide sorting of the found files.
    :type sort: FileSort
    """
    
    def __init__(self, path, extension, previewExtensions='bmp', notFoundImage=None, sort=FileSort()):
        self.location = gui.TextView('')
        super(FileChooser, self).__init__(path, extension, sort)

        self.setPreviewExtensions(previewExtensions)

        self.selection = ''
        self.childY = {}
        self.notFoundImage = notFoundImage

        self.layout = QtGui.QGridLayout(self)

        self.sortBox = self.createSortBox()
        self.layout.addWidget(self.sortBox, 0, 0)
        self.layout.setRowStretch(0, 0)
        self.layout.setColumnStretch(0, 0)

        self.layout.addWidget(QtGui.QWidget(), 1, 0)

        self.files_sc = QtGui.QScrollArea()
        self.files_sc.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.files_sc.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        self.layout.addWidget(self.files_sc, 0, 1, 2, -1)
        self.layout.setRowStretch(1, 1)
        self.layout.setColumnStretch(1, 1)

        self.files = QtGui.QWidget()
        self.files_sc.installEventFilter(self)
        self.files_sc.setWidget(self.files)
        self.files_sc.setWidgetResizable(True)
        self.children = FlowLayout(self.files)
        self.children.setSizeConstraint(QtGui.QLayout.SetMinimumSize)

        self.layout.addWidget(self.location, 2, 0, 1, -1)
        self.layout.setRowStretch(2, 0)

    def addItem(self, file, label, preview, tags=[]):
        item = FileChooserRectangle(self, file, label, preview)
        item.tags = tags
        self.children.addWidget(item)
        super(FileChooser, self).addItem(file, label, preview, tags)
        return item

    def setPaths(self, value):
        super(FileChooser, self).setPaths(value)
        locationLbl = "  |  ".join(self.paths)
        self.location.setText(os.path.abspath(locationLbl))

# TODO IconListFileChooser (with FileChooserRectangles as items)
# TODO allow setting a clear or none item at the top

class ListFileChooser(FileChooserBase):

    def __init__(self, path, extension, name="File chooser" , multiSelect=False, verticalScrolling=False, sort=FileSort()):
        super(ListFileChooser, self).__init__(path, extension, sort)
        self.listItems = []
        self.multiSelect = multiSelect

        self.layout = QtGui.QGridLayout(self)
        self.mainBox = gui.GroupBox(name)
        self.children = gui.ListView()
        self.layout.addWidget(self.mainBox)
        self.mainBox.addWidget(self.children)

        self.layout.setSpacing(0)
        self.layout.setContentsMargins(0,0,0,0)

        self.children.setSizePolicy(QtGui.QSizePolicy.Ignored, QtGui.QSizePolicy.MinimumExpanding)
        self.children.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

        self.children.setVerticalScrollingEnabled(verticalScrolling)

        # Remove frame and background color from list widget (native theme)
        self.children.setFrameShape(QtGui.QFrame.NoFrame)
        palette = QtGui.QPalette()
        palette.setColor(QtGui.QPalette.Base, QtGui.QColor(255,255,255,0))
        self.children.setPalette(palette)

        @self.children.mhEvent
        def onClicked(item):
            if self.multiSelect:
                self.callEvent('onFileHighlighted', self.loadHandler.getSelection(item))
            else:
                self.callEvent('onFileSelected', self.loadHandler.getSelection(item))

        @self.children.mhEvent
        def onItemChecked(item):
            self.callEvent('onFileSelected', self.loadHandler.getSelection(item))

        @self.children.mhEvent
        def onItemUnchecked(item):
            self.callEvent('onFileDeselected', self.loadHandler.getSelection(item))

        @self.children.mhEvent
        def onClearSelection(value):
            self.callEvent('onDeselectAll', None)

    def setVerticalScrollingEnabled(self, enabled):
            self.children.setVerticalScrollingEnabled(enabled)

    def createSortBox(self):
        self.sortBox = super(ListFileChooser, self).createSortBox()
        if self.multiSelect:
            deselectAllBtn = self.sortBox.addWidget(gui.Button('Deselect all'))
            @deselectAllBtn.mhEvent
            def onClicked(value):
                self.deselectAll()
        return self.sortBox

    def addItem(self, file, label, preview, tags=[]):
        item = gui.ListItem(label)
        if self.multiSelect:
            item.enableCheckbox()
        item.file = file
        item.preview = preview
        item.tags = tags
        super(ListFileChooser, self).addItem(file, label, preview, tags)
        return self.children.addItemObject(item)

    def getHighlightedItem(self):
        items = self.children.selectedItems()
        if len(items) > 0:
            return self.loadHandler.getSelection(items[0])
        else:
            return None

    def getSelectedItem(self):
        return self.getHighlightedItem()

    def getSelectedItems(self):
        if self.multiSelect:
            return [self.loadHandler.getSelection(item) for item in self.children.getItems() if item.isChecked()]
        else:
            return [self.getHighlightedItem()]

    def selectItem(self, item):
        if self.multiSelect:
            selections = self.getSelectedItems()
            if item not in selections:
                selections.append(item)
                self.setSelections(selections)
        else:
            self.setSelection(item)

    def deselectItem(self, item):
        selections = self.getSelectedItems()
        if item in selections:
            if self.multiSelect:
                selections.remove(item)
                self.setSelections(selections)
            else:
                self.deselectAll()

    def setSelection(self, item):
        if self.multiSelect:
            return

        self.deselectAll()

        for listItem in self.children.getItems():
            if self.loadHandler.matchesItem(listItem, item):
                self.children.setCurrentItem(listItem)
                return

    def setSelections(self, items):
        if not self.multiSelect:
            return

        for listItem in self.children.getItems():
            listItem.setChecked( self.loadHandler.matchesItems(listItem, items) )

    def setHighlightedItem(self, item):
        if item != None:
            for listItem in self.children.getItems():
                if self.loadHandler.matchesItem(listItem, item):
                    self.children.setCurrentItem(listItem)
                    return
        else:
            self.children.setCurrentItem(None)

    def deselectAll(self):
        self.children.clearSelection()

    def clearList(self):
        self.children.clear()

    def setFocus(self):
        self.children.setFocus()

    def refresh(self, keepSelections=True):
        if keepSelections:
            selections = self.getSelectedItems()
            if self.multiSelect:
                highLighted = self.getHighlightedItem()
        else:
            self.deselectAll()

        super(ListFileChooser, self).refresh()

        if keepSelections:
            if self.multiSelect:
                self.setSelections(selections)
                self.setHighlightedItem(highLighted)
            elif len(selections) > 0:
                self.setSelection(selections[0])

class IconListFileChooser(ListFileChooser):
    def __init__(self, path, extension, previewExtensions='bmp', notFoundImage=None, name="File chooser" , multiSelect=False, verticalScrolling=False, sort=FileSort()):
        super(IconListFileChooser, self).__init__(path, extension, name, multiSelect, verticalScrolling, sort)
        self.setPreviewExtensions(previewExtensions)
        self.notFoundImage = notFoundImage
        self._iconCache = {}
        #self.children.setIconSize(QtCore.QSize(50,50))

    def addItem(self, file, label, preview, tags=[]):
        item = super(IconListFileChooser, self).addItem(file, label, preview, tags)
        if preview not in self._iconCache:
            pixmap = QtGui.QPixmap(preview)
            size = pixmap.size()
            if size.width() > 128 or size.height() > 128:
                pixmap = pixmap.scaled(128, 128, QtCore.Qt.KeepAspectRatio)
            self._iconCache[preview] = QtGui.QIcon(pixmap)
        icon = self._iconCache[preview]
        item.setIcon(icon)
        return item

    def setIconSize(self, width, height):
        self.children.setIconSize(QtCore.QSize(width, height))
