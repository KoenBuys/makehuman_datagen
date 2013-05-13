#!/usr/bin/python
# -*- coding: utf-8 -*-

""" 
**Project Name:**      MakeHuman

**Product Home Page:** http://www.makehuman.org/

**Code Home Page:**    http://code.google.com/p/makehuman/

**Authors:**           Jonas Hauquier, Glynn Clements

**Copyright(c):**      MakeHuman Team 2001-2013

**Licensing:**         AGPL3 (see also http://www.makehuman.org/node/318)

**Coding Standards:**  See http://www.makehuman.org/node/165

Abstract
--------

Various image processing operations.
"""

import numpy
from image import Image


def resized(img, width, height):
    sw, sh = img.size
    xmap = numpy.floor((numpy.arange(width) + 0.5) * sw / float(width)).astype(int)
    ymap = numpy.floor((numpy.arange(height) + 0.5) * sh / float(height)).astype(int)
    return Image(data = img.data[ymap,:][:,xmap])

def blurred(img, level=10.0, kernelSize = 15, progressCallback=None):
    """
    Apply a gaussian blur on the specified image. Returns a new blurred image.
    level is the level of blurring and can be any float.
    kernelSize is the size of the kernel used for convolution, and dictates the
    number of samples used, requiring longer processing for higher values.
    KernelSize should be a value between 5 and 30

    Based on a Scipy lecture example from https://github.com/scipy-lectures/scipy-lecture-notes
    Licensed under Creative Commons Attribution 3.0 United States License
    (CC-by) http://creativecommons.org/licenses/by/3.0/us
    """

    def progress(prog):
        if (progressCallback is not None):
            progressCallback(prog)
        else:
            pass
    progress(0)

    kernelSize = int(kernelSize)
    if kernelSize < 5:
        kernelSize = 5
    elif kernelSize > 30:
        kernelSize = 30

    # prepare an 1-D Gaussian convolution kernel
    t = numpy.linspace(-20, 20, kernelSize)
    bump = numpy.exp(-0.1*(t/level)**2)
    bump /= numpy.trapz(bump) # normalize the integral to 1
    padSize = int(kernelSize/2)
    paddedShape = (img.data.shape[0] + padSize, img.data.shape[1] + padSize)
    progress(0.15)

    # make a 2-D kernel out of it
    kernel = bump[:,numpy.newaxis] * bump[numpy.newaxis,:]

    # padded fourier transform, with the same shape as the image
    kernel_ft = numpy.fft.fft2(kernel, s=paddedShape, axes=(0, 1))
    progress(0.4)

    # convolve
    img_ft = numpy.fft.fft2(img.data, s=paddedShape, axes=(0, 1))
    progress(0.65)
    img2_ft = kernel_ft[:,:,numpy.newaxis] * img_ft
    data = numpy.fft.ifft2(img2_ft, axes=(0, 1)).real
    progress(0.9)

    # clip values to range
    data = numpy.clip(data, 0, 255)
    progress(1.0)

    return Image(data = data[padSize:data.shape[0], padSize:data.shape[1], :])

def mix(img1, img2, weight1, weight2 = None):
    if weight2 is None:
        weight2 =  1 - weight1
    return Image(data = numpy.around(
        weight1*img1.data.astype(float)
        + weight2*img2.data.astype(float)).astype(int))

def clipped (img):
    return Image(data = numpy.clip(img.data,0,255))
                 
def compose(channels):
    # 'channels' is a sequence of Images.
    outch = []
    i = 0
    for c in channels:
        if c.components == 1:
            outch.append(c.data[:,:,0:1])
        else:
            if c.components < i:
                raise TypeError("Image No. %i has not enough channels" % i)
            outch.append(c.data[:,:,i:i+1])
        i += 1
    return Image(data = numpy.dstack(outch))

def getAlpha(img):
    return Image(data = img.data[:,:,-1:])

def getChannel(img, channel):
    return Image(data = img.data[:,:,(channel-1):channel])
