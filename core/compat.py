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

class MaterialsProxy(object):
    def __init__(self, object):
        self._object = object

    def __len__(self):
        return len(self._object.fmtls)

    def __getitem__(self, idx):
        return self._object._materials[self._object.fmtls[idx]]

    def __iter__(self):
        for idx in xrange(len(self)):
            yield self[idx]

    def __contains__(self, idx):
        return idx >= 0 and idx < len(self)

    def iterkeys(self):
        return xrange(len(self))

    def itervalues(self):
        for idx in xrange(len(self)):
            yield self[idx]

    def iteritems(self):
        for idx in xrange(len(self)):
            yield idx, self[idx]

    def keys(self):
        return range(len(self))

    def values(self):
        return [self[idx] for idx in xrange(len(self))]

    def items(self):
        return [(idx, self[idx]) for idx in xrange(len(self))]
