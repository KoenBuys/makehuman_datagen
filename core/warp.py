#!/usr/bin/python
# -*- coding: utf-8 -*-

""" 
**Project Name:**      MakeHuman

**Product Home Page:** http://www.makehuman.org/

**Code Home Page:**    http://code.google.com/p/makehuman/

**Authors:**           Thomas Larsson, Alexis Mignon

**Copyright(c):**      MakeHuman Team 2001-2013

**Licensing:**         AGPL3 (see also http://www.makehuman.org/node/318)

**Coding Standards:**  See http://www.makehuman.org/node/165

Abstract
--------

Warp vertex locations from a source character to a target character.

Let

    x_n             Location of vertex n in source character
    y_n             Location of vertex n in target character
    
    x + dx = f(x)   Morph of source character    
    y + dy = g(y)   Morph of target character
    
Given the sets (x_n) and (y_n) and the function f(x), we want to find g(y). To this
end, introduce the warp field U(x) and its inverse V(y)

    y = U(x)        Warp source location to target location
    x = V(y)        Warp target location to source location
    
Clearly, g = U o f o V, or

    g(y) = U(f(V(y)))
    
We only need the inverse warp field at vertex locations, viz. V(y_n) = x_n.  
The target morph (dy_n) is thus given by

    y_n + dy_n = U(x_n + dx_n)

The warp field U(x) is needed outside the original vertex set. 
Pick a set of landmark points (x_i), which is a subset of the vertices of the source 
character. The landmarks should be denser in interesting detail, and can be chosen 
differently depending on the morph. The warp function is assumed to be of the form

    U(x) = sum_i w_i h_i(x)
    
where (w_i) is a set of weights, and h_i(x) is a basis of RBFs (Radial Basis Function).
An RBF only depends on the distance from the landmark, i.e.

    h_i(x) = phi(|x - x_i|).
    
Our RBFs are Hardy functions,

    h_i(x) = sqrt( |x - x_i|^2 + s_i^2 ),
    
where s_i = min_(j != i) |x_j - x_i| is the minimal distance to another landmark.
To determine the weights w_i, we require that the warp field is exact for the landmarks:

    y_i = y(x_i) = U(x_i)
    
    y_i = sum_j H_ij w_j
    
    H_ij = h_j(x_i)
    
This can be written in matrix form: w = (w_j), y = (y_i), H = (H_ij):

    y = H w
    
We solve the equivalent equation, which probably has better numerical properties
    
    A w = b, 
    
where A = HT H, b = HT b, where HT is the transpose of H.
    
"""
   
import math
import numpy
import sys
import imp
import os
import log

#----------------------------------------------------------
#   class CWarp2
#----------------------------------------------------------

def compute_distance2(x, y=None):
    if y is None:
        gram = numpy.dot(x,x.T)
        diag = gram.diagonal()
        return diag[:,numpy.newaxis] + diag[numpy.newaxis] - 2 * gram
    else:
        gram = numpy.dot(x, y.T)
        diagx = (x*x).sum(-1)
        diagy = (y*y).sum(-1)
        return diagx[:,numpy.newaxis] + diagy[numpy.newaxis] - 2* gram


class CWarp2(object):
    
    def __init__(self, source, target, landmarks):
        self.source = numpy.asarray(source, dtype="float32")
        self.target = numpy.asarray(target, dtype="float32")
        
        self.xverts = self.source[landmarks]
        self.yverts = self.target[landmarks]
        H = self.rbf(self.xverts)
        w = numpy.linalg.lstsq(H,self.yverts)[0]
        self.w = w


    def rbf(self, x, y=None):
        dists2 = compute_distance2(x, y)

        if y is None:
            dmax = dists2.max()
            dtmp = dists2 + dmax * numpy.identity(x.shape[0])
            self.s2 = dtmp.min(0)

        return numpy.sqrt(dists2 + self.s2)
        #~ return numpy.exp(- 0.003 * dists2 / dists2.max())


    def warpTarget(self, morph):
        idx = morph.keys()
        disp = numpy.asarray(morph.values(), dtype="float")
        xmorph = self.source[idx] + disp
        H = self.rbf(xmorph, self.xverts)
        ymorph = numpy.dot(H, self.w) - self.target[idx]
        return dict(zip(idx, ymorph))


#----------------------------------------------------------
#   External interface
#----------------------------------------------------------

def warp_target1(morph, source, target, landmarks):
    return CWarp().warpTarget(morph, source, target, landmarks)

def warp_target(morph, source, target, landmarks):
    return CWarp2(source, target, landmarks).warpTarget(morph)


#----------------------------------------------------------
#   Testing
#----------------------------------------------------------

def test_warp():
    import time
    numpy.random.seed(5643)
    
    n = 1000
    angle = 2*numpy.pi * numpy.random.rand(n)
    z = numpy.random.rand(n)
    x = numpy.cos(angle)
    y = numpy.sin(angle)
    points = numpy.vstack([x,y,z]).T
    
    morph = dict([ (i+n/2, 0.1 * numpy.random.rand(3)) for i in range(n/2) ])
    landmarks = range(n/2)
    
    t0 = time.time()
    ymorph = warp_target1(morph, points, points * (1,3,1), landmarks )
    t1 = time.time()
    ymorph2 = warp_target2(morph, points, points * (1,3,1), landmarks )
    t2 = time.time()
    
    log.message("time warp 1 %s", (t1 - t0) )
    log.message("time warp 2 %s", (t2 - t1) )
    log.message("t1/t2 %s", (t1 - t0)/(t2 - t1) )
        
    log.message("difference morph1/morph2 %s", numpy.abs(numpy.array(ymorph.values()) - numpy.array(ymorph2.values())).mean() )
    log.message("morph error 1 %s", numpy.abs(numpy.array(morph.values()) * (1,3,1) - numpy.array(ymorph.values())).mean() )
    log.message("morph error 2 %s", numpy.abs(numpy.array(morph.values()) * (1,3,1) - numpy.array(ymorph2.values())).mean() )

if __name__ == '__main__':
    test_warp() 
