#!/usr/bin/python
# -*- coding: utf-8 -*-

""" 
**Project Name:**      MakeHuman

**Product Home Page:** http://www.makeinfo.human.org/

**Code Home Page:**    http://code.google.com/p/makehuman/

**Authors:**           Thomas Larsson

**Copyright(c):**      MakeHuman Team 2001-2013

**Licensing:**         AGPL3 (see also http://www.makeinfo.human.org/node/318)

**Coding Standards:**  See http://www.makeinfo.human.org/node/165

Abstract
--------

Gizmos used by rigify rig
"""

def asString():
    return(

"""
# ----------------------------- MESH --------------------- # 

Mesh MHGaze MHGaze 
  Verts
    v -0.000 0 -0.126 ;
    v -0.048 0 -0.117 ;
    v -0.089 0 -0.089 ;
    v -0.117 0 -0.048 ;
    v -0.126 0 0.000 ;
    v -0.117 0 0.048 ;
    v -0.089 0 0.089 ;
    v -0.048 0 0.117 ;
    v -0.000 0 0.126 ;
    v 0.048 0 0.117 ;
    v 0.089 0 0.089 ;
    v 0.117 0 0.048 ;
    v 0.126 0 -0.000 ;
    v 0.117 0 -0.048 ;
    v 0.089 0 -0.089 ;
    v 0.048 0 -0.117 ;
    v -0.000 0 -0.142 ;
    v -0.116 0 -0.132 ;
    v -0.214 0 -0.082 ;
    v -0.279 0 -0.033 ;
    v -0.302 0 0.000 ;
    v -0.279 0 0.033 ;
    v -0.214 0 0.082 ;
    v -0.116 0 0.132 ;
    v -0.000 0 0.142 ;
    v 0.116 0 0.132 ;
    v 0.214 0 0.082 ;
    v 0.279 0 0.033 ;
    v 0.302 0 -0.000 ;
    v 0.279 0 -0.033 ;
    v 0.214 0 -0.082 ;
    v 0.116 0 -0.132 ;
  end Verts
  Edges
    e 1 0 ;
    e 2 1 ;
    e 3 2 ;
    e 4 3 ;
    e 5 4 ;
    e 6 5 ;
    e 7 6 ;
    e 8 7 ;
    e 9 8 ;
    e 10 9 ;
    e 11 10 ;
    e 12 11 ;
    e 13 12 ;
    e 14 13 ;
    e 15 14 ;
    e 15 0 ;
    e 17 16 ;
    e 18 17 ;
    e 19 18 ;
    e 20 19 ;
    e 21 20 ;
    e 22 21 ;
    e 23 22 ;
    e 24 23 ;
    e 25 24 ;
    e 26 25 ;
    e 27 26 ;
    e 28 27 ;
    e 29 28 ;
    e 30 29 ;
    e 31 30 ;
    e 31 16 ;
  end Edges
end Mesh

Object MHGaze MESH MHGaze
  layers Array 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1  ;
  parent Refer Object CustomShapes ;
end Object

""")
