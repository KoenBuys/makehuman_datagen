#!/usr/bin/python
# -*- coding: utf-8 -*-

""" 
**Project Name:**      MakeHuman

**Product Home Page:** http://www.makehuman.org/

**Code Home Page:**    http://code.google.com/p/makehuman/

**Authors:**           Jonas Hauquier
                       Marc Flerackers
                       Thanasis Papoutsidakis

**Copyright(c):**      MakeHuman Team 2001-2013

**Licensing:**         AGPL3 (see also http://www.makehuman.org/node/318)

**Coding Standards:**  See http://www.makehuman.org/node/165

Abstract
--------

Functions for processing .mhstx files
and manipulating subtextures as Image objects.
"""

import os
import mh

def combine(image, mhstx):
    f = open(mhstx, 'rU')
    try:
        subTextures = mh.parseINI(f.read(), [("(","["), (")","]")])
    except:
        log.warning("subtextures.combine(%s)", mhstx, exc_info=True)
        f.close()
        return mh.Image()
    f.close()
    
    texdir = os.path.dirname(mhstx)
    img = mh.Image(data = image.data)
    for subTexture in subTextures:
        path = os.path.join(texdir, subTexture['txt'])
        subImg = mh.Image(path)
        x, y = subTexture['dst']
        img.blit(subImg, x, y)

    return img

