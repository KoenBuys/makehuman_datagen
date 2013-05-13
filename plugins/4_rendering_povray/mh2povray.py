#!/usr/bin/python
# -*- coding: utf-8 -*-

""" 
POV-Ray Export functions.

**Project Name:**      MakeHuman

**Product Home Page:** http://www.makehuman.org/

**Code Home Page:**    http://code.google.com/p/makehuman/

**Authors:**           Chris Bartlett, Thanasis Papoutsidakis

**Copyright(c):**      MakeHuman Team 2001-2013

**Licensing:**         AGPL3 (see also http://www.makehuman.org/node/318)

**Coding Standards:**  See http://www.makehuman.org/node/165

Abstract
--------

This module implements functions to export a human model in POV-Ray format. POV-Ray is a 
Raytracing application (a renderer) that is free to download and use. The generated text 
file contains POV-Ray Scene Description Language (SDL), which consists of human-readable 
instructions for building 3D scenes. 

This module supports the export of a simple mesh2 object or the export of arrays of data
with accompanying macros to assemble POV-Ray objects. Both formats include some handy 
variable and texture definitions that are written into a POV-Ray include file. A POV-Ray 
scene file is also written to the output directory containing a range of examples 
illustrating the use of the include file.

The filenames and object names exported are based on the human's current name,
which is the name that was used when saving the MHM model. In case it's unsaved,
the exported files use 'untitled'.

"""

import os
import string
import shutil
import projection
import random
import mh
import log
import numpy
import image_operations as imgop
import gui3d
from exportutils import collect
import subprocess

def downloadPovRay():
    import webbrowser
    webbrowser.open('http://www.povray.org/download/')

def povrayExport(settings):
    """
    This function exports data in a format that can be used to reconstruct all
    renderable MakeHuman objects in POV-Ray.

    Parameters
    ----------

    settings:
      *Dictionary*. Options passed from the Povray exporter GUI.
    """

    settings['name'] = string.replace(getHumanName(), " ", "_")
    log.message('POV-Ray Export of object: %s', settings['name'])
  
    camera = gui3d.app.modelCamera
    settings['resw'] = gui3d.app.settings.get('rendering_width', 800)
    settings['resh'] = gui3d.app.settings.get('rendering_height', 600)
  
    path = os.path.join(mh.getPath('render'),
                        gui3d.app.settings.get('povray_render_dir', 'pov_output'),
                        "%s.inc" % settings['name'])
    
    # The format option defines whether a simple mesh2 object is to be generated
    # or the more flexible but slower array and macro combo is to be generated.
    if settings['format'] == 'array':
        povrayExportArray(gui3d.app.selectedHuman.mesh, camera, path, settings)
    if settings['format'] == 'mesh2':
        povrayExportMesh2(gui3d.app.selectedHuman.mesh, camera, path, settings)

    outputDirectory = os.path.dirname(path)
    log.debug('out folder: %s', outputDirectory)

    povray_bin = (gui3d.app.settings.get('povray_bin', ''))
   
    # try to use the appropriate binary 
    if os.path.exists(povray_bin):
        exetype = settings['bintype']
        if exetype == 'win64':
            povray_bin += '/pvengine64.exe'
        elif exetype == 'win32sse2':
            povray_bin += '/pvengine-sse2.exe'
        elif exetype == 'win32':
            povray_bin += '/pvengine.exe'
        elif exetype == 'linux':
            povray_bin += '/povray'
        log.debug('Povray path: %s', povray_bin)


    povwatchApp = None
    povwatchPath = ""
    povwatchTimer = 0
    def povwatch():
        if povwatchApp.poll() is not None:
            gui3d.app.getCategory('Rendering').getTaskByName('Viewer').setImage(povwatchPath)
            mh.changeTask('Rendering', 'Viewer')
            gui3d.app.statusPersist('Rendering complete')
            mh.removeTimer(povwatchTimer)

    if settings['action'] == 'render':
        if os.path.isfile(povray_bin):
            # Prepare command line.
            if os.name == 'nt':
                cmdLine = (povray_bin, 'MHRENDER', '/EXIT')
            else:
                cmdLine = (povray_bin, 'MHRENDER')
                
            # Pass parameters by writing an .ini file.
            iniFD = open(os.path.join(outputDirectory, 'MHRENDER.ini'), 'w')
            iniFD.write('Input_File_Name="%s.pov"\n' % settings['name'] +
                        '+W%d +H%d +a%s +am2\n' %
                        (settings['resw'], settings['resh'], settings['AA']))
            iniFD.close()

            povwatchApp = subprocess.Popen(cmdLine, cwd = os.path.dirname(path))
            gui3d.app.statusPersist('POV - Ray is rendering.')
            povwatchPath = path.replace('.inc','.png')
            povwatchTimer = mh.addTimer(1000, lambda: povwatch())

        else:
            gui3d.app.prompt(
                'POV-Ray not found',
                'You don\'t seem to have POV-Ray installed or the path is incorrect.',
                'Download', 'Cancel', downloadPovRay)        

def povrayExportArray(obj, camera, path, settings):
    """
    This function exports data in the form of arrays of data the can be used to 
    reconstruct a humanoid object using some very simple POV-Ray macros. These macros 
    can build this data into a variety of different POV-Ray objects, including a
    mesh2 object that represents the human figure much as it was displayed in MakeHuman. 

    These macros can also generate a union of spheres at the vertices and a union of 
    cylinders that follow the edges of the mesh. A parameter on the mesh2 macro can be 
    used to generate a slightly inflated or deflated mesh. 

    The generated output file always starts with a standard header, is followed by a set 
    of array definitions containing the object data and is ended by a standard set of 
    POV-Ray object definitions. 

    Parameters
    ----------

    obj:
      *3D object*. The object to export. This should be the humanoid object with
      uv-mapping data and Face Groups defined.

    camera:
      *Camera object*. The camera to render from. 

    path:
      *string*. The file system path to the output files that need to be generated. 
    """

  # Certain files and blocks of SDL are mostly static and can be copied directly
  # from reference files into the generated output directories or files.

    headerFile = 'data/povray/headercontent.inc'
    staticFile = 'data/povray/staticcontent.inc'
    sceneFile = 'data/povray/makehuman.pov'
    groupingsFile = 'data/povray/makehuman_groupings.inc'
    pigmentMap = gui3d.app.selectedHuman.mesh.texture

  # Define some additional file related strings

    outputSceneFile = path.replace('.inc', '.pov')
    baseName = os.path.basename(path)
    nameOnly = string.replace(baseName, '.inc', '')
    underScores = ''.ljust(len(baseName), '-')
    outputDirectory = os.path.dirname(path)

  # Make sure the directory exists

    if not os.path.isdir(outputDirectory):
        try:
            os.makedirs(outputDirectory)
        except:
            log.error('Error creating export directory.')
            return 0

  # Open the output file in Write mode

    try:
        outputFileDescriptor = open(path, 'w')
    except:
        log.error('Error opening file to write data.')
        return 0

  # Write the file name into the top of the comment block that starts the file.

    outputFileDescriptor.write('// %s\n' % baseName)
    outputFileDescriptor.write('// %s\n' % underScores)

  # Copy the header file SDL straight across to the output file

    try:
        headerFileDescriptor = open(headerFile, 'r')
    except:
        log.error('Error opening file to read standard headers.')
        return 0
    headerLines = headerFileDescriptor.read()
    outputFileDescriptor.write(headerLines)
    outputFileDescriptor.write('''

''')
    headerFileDescriptor.close()

  # Declare POV_Ray variables containing the current makehuman camera.

    povrayCameraData(camera, resolution, outputFileDescriptor)
    
    outputFileDescriptor.write('#declare MakeHuman_TranslateX      = %s;\n' % -obj.x)
    outputFileDescriptor.write('#declare MakeHuman_TranslateY      = %s;\n' % obj.y)
    outputFileDescriptor.write('#declare MakeHuman_TranslateZ      = %s;\n\n' % obj.z)
    
    outputFileDescriptor.write('#declare MakeHuman_RotateX         = %s;\n' % obj.rx)
    outputFileDescriptor.write('#declare MakeHuman_RotateY         = %s;\n' % -obj.ry)
    outputFileDescriptor.write('#declare MakeHuman_RotateZ         = %s;\n\n' % obj.rz)

  # Calculate some useful values and add them to the output as POV-Ray variable
  # declarations so they can be readily accessed from a POV-Ray scene file.

    povraySizeData(obj, outputFileDescriptor)

    # Collect and prepare all objects.
    stuffs = collect.setupObjects(settings['name'], gui3d.app.selectedHuman, helpers=False, hidden=False,
                                            eyebrows=False, lashes=False, subdivide = settings['subdivide'])

    # Write array data for the object.
    povrayWriteArray(outputFileDescriptor, stuffs)

  # Copy macro and texture definitions straight across to the output file.

    try:
        staticContentFileDescriptor = open(staticFile, 'r')
    except:
        log.error('Error opening file to read static content.')
        return 0
    staticContentLines = staticContentFileDescriptor.read()
    outputFileDescriptor.write(staticContentLines)
    outputFileDescriptor.write('\n')
    staticContentFileDescriptor.close()

  # The POV-Ray include file is complete

    outputFileDescriptor.close()
    log.message("POV-Ray '#include' file generated.")

  # Copy a sample scene file across to the output directory

    try:
        sceneFileDescriptor = open(sceneFile, 'r')
    except:
        log.error('Error opening file to read standard scene file.')
        return 0
    try:
        outputSceneFileDescriptor = open(outputSceneFile, 'w')
    except:
        log.error('Error opening file to write standard scene file.')
        return 0
    sceneLines = sceneFileDescriptor.read()
    sceneLines = string.replace(sceneLines, 'xxFileNamexx', nameOnly)
    sceneLines = string.replace(sceneLines, 'xxUnderScoresxx', underScores)
    sceneLines = string.replace(sceneLines, 'xxLowercaseFileNamexx', nameOnly.lower())
    outputSceneFileDescriptor.write(sceneLines)

    # Copy the skin texture file into the output directory
    collect.copy(pigmentMap, os.path.join(outputDirectory, "texture.png"))


  # Copy the makehuman_groupings.inc file into the output directory

    try:
        shutil.copy(groupingsFile, outputDirectory)
    except (IOError, os.error), why:
        log.error("Can't copy %s" % str(why))

  # Job done

    outputSceneFileDescriptor.close()
    sceneFileDescriptor.close()
    log.message('Sample POV-Ray scene file generated.')

def writeCamera(hfile, camera, settings):
    hfile.write("camera {\n  orthographic\n")
    hfile.write("  location <%f,%f,%f>\n" % invx(camera.eye))
    hfile.write("  up <0,1,0>\n  right <%f,0,0>\n" %
                (float(settings['resw'])/float(settings['resh'])))
    hfile.write("  angle %f\n" % camera.fovAngle)
    hfile.write("  look_at <%f,%f,%f>\n}\n\n" % invx(camera.focus))

def writeLights(scene, hfile):
    hflig = open('data/povray/lights.inc','r')
    ligfilebuffer = hflig.read()
    hflig.close()
    for light in scene.lights:
        liglines = ligfilebuffer
        liglines = liglines.replace('%%pos%%', '<%f,%f,%f>' % invx(light.position))
        liglines = liglines.replace('%%color%%', '<%f,%f,%f>' % light.color)
        liglines = liglines.replace('%%focus%%', '<%f,%f,%f>' % invx(light.focus))
        liglines = liglines.replace('%%fov%%', str(light.fov))
        liglines = liglines.replace('%%att%%', str(light.attenuation))
        if light.areaLights < 2:
            liglines = liglines.replace('%%arealight%%', '')
        else:
            liglines = liglines.replace(
                '%%arealight%%', 'area_light\n    ' +
                '<{0},0,0>, <0,{0},0>, {1}, {1}\n    '.format(light.areaLightSize, light.areaLights) +
                'adaptive 1\n    jitter circular orient\n')
        hfile.write(liglines)

def writeScene(file, stuffs, settings):
    hfile = open(file, 'w')
    hfile.write('#include "%s.inc"\n\n' % stuffs[0].name)
    writeCamera(hfile, gui3d.app.modelCamera, settings)
    for stuff in stuffs:
        hfile.write(
            "object { \n" +
            "   %s_Mesh2Object \n" % stuff.name +
            "   rotate <0,0,%s_rz> \n" % settings['name'] +
            "   rotate <0,%s_ry,0> \n" % settings['name'] +
            "   rotate <%s_rx,0,0> \n" % settings['name'] +
            "   translate <{0}_x,{0}_y,{0}_z> \n".format(settings['name']) +
            "   material {%s_Material} \n}\n" % stuff.name)
    hfile.close()

def writeConstants(hfile, settings):
    """
    This function outputs constants of the model's position and dimensions.
    """
    human = gui3d.app.selectedHuman
    humanPos = invx(human.getPosition())
    humanRot = human.getRotation()

    hfile.write('// Figure position and rotation.\n')
    hfile.write('#declare %s_x = %f;\n' % (settings['name'], humanPos[0]))
    hfile.write('#declare %s_y = %f;\n' % (settings['name'], humanPos[1]))
    hfile.write('#declare %s_z = %f;\n' % (settings['name'], humanPos[2]))
    hfile.write('#declare %s_rx = %f;\n' % (settings['name'], humanRot[0]))
    hfile.write('#declare %s_ry = %f;\n' % (settings['name'],-humanRot[1]))
    hfile.write('#declare %s_rz = %f;\n\n' % (settings['name'], humanRot[2]))
    maxX = 0
    maxY = 0
    maxZ = 0
    minX = 0
    minY = 0
    minZ = 0
    for co in human.mesh.coord:
        maxX = max(maxX, co[0])
        maxY = max(maxY, co[1])
        maxZ = max(maxZ, co[2])
        minX = min(minX, co[0])
        minY = min(minY, co[1])
        minZ = min(minZ, co[2])
    hfile.write('// Figure Dimensions.\n')
    hfile.write('#declare MakeHuman_MaxExtent = < %s, %s, %s>;\n' % (maxX, maxY, maxZ))
    hfile.write('#declare MakeHuman_MinExtent = < %s, %s, %s>;\n' % (minX, minY, minZ))
    hfile.write('#declare MakeHuman_Center    = < %s, %s, %s>;\n' % ((maxX + minX) / 2, (maxY + minY) / 2, (maxZ + minZ) / 2))
    hfile.write('#declare MakeHuman_Width     = %s;\n' % (maxX - minX))
    hfile.write('#declare MakeHuman_Height    = %s;\n' % (maxY - minY))
    hfile.write('#declare MakeHuman_Depth     = %s;\n\n' % (maxZ - minZ))

def povrayExportMesh2(obj, camera, path, settings, progressCallback = None):
    """
    This function exports data in the form of a mesh2 humanoid object. The POV-Ray 
    file generated is fairly inflexible, but is highly efficient. 

    Parameters
    ----------

    obj:
      *3D object*. The object to export. This should be the humanoid object with
      uv-mapping data and Face Groups defined.

    camera:
      *Camera object*. The camera to render from. 

    path:
      *string*. The file system path to the output files that need to be generated.

    settings:
      *dictionary*. Settings passed from the GUI.
    """

    progbase = 0
    def progress (prog, desc):
        if progressCallback == None:
            gui3d.app.progress(prog, desc)
        else:
            progressCallback(prog, desc)

    # Certain blocks of SDL are mostly static and can be copied directly from reference
    # files into the output files.
    nextpb = 0.6 - 0.4 * bool(settings['SSS'])
    progress (progbase,"Parsing data")
    staticFile = 'data/povray/staticcontent_mesh2only_fsss.inc' if settings['SSS'] else 'data/povray/staticcontent_mesh2only_tl.inc'

    # Define some additional file locations
    outputSceneFile = path.replace('.inc', '.pov')
    baseName = os.path.basename(path)
    underScores = ''.ljust(len(baseName), '-')
    outputDirectory = os.path.dirname(path)

    # Make sure the directory exists
    if not os.path.isdir(outputDirectory):
        try:
            os.makedirs(outputDirectory)
        except:
            log.error('Error creating export directory.')
            return 0
    
    # Open the output file in Write mode
    try:
        outputFileDescriptor = open(path, 'w')
    except:
        log.error('Error opening file to write data: %s', path)
        return 0

    # Write position and dimension constants.
    writeConstants(outputFileDescriptor, settings)

    # Collect and prepare all objects.
    stuffs = collect.setupObjects(settings['name'], gui3d.app.selectedHuman, helpers=False, hidden=False,
                                            eyebrows=False, lashes=True, subdivide = settings['subdivide'],
                                            progressCallback = lambda p: progress(progbase+p*(nextpb-progbase),"Analyzing objects"))
    progbase = nextpb

    # If SSS is enabled, render the lightmaps.
    if settings['SSS'] == True:
        povrayProcessSSS(stuffs, outputDirectory, settings, lambda p: progress(progbase+p*(0.6-progbase),"Processing Subsurface Scattering"))
        progbase = 0.6

    # Write mesh data for the object.
    povrayWriteMesh2(outputFileDescriptor, stuffs, lambda p: progress(progbase+p*(0.9-progbase),"Writing Objects"))
    progbase = 0.9
    nextpb = 0.95
                                            
    # Copy texture definitions to the output file.
    progress(progbase,"Writing Materials")
    writeLights(settings['scene'], outputFileDescriptor)
    hmatfile = open(staticFile, 'r')
    matlines = hmatfile.read()
    hmatfile.close()
    matlines = matlines.replace('%%spec%%', str(settings['skinoil']*settings['moist']))    
    matlines = matlines.replace('%%edss%%', str(settings['skinoil']*(1-settings['moist'])))
    matlines = matlines.replace('%%rough%%', str(settings['rough']))
    if settings['usebump']:
        _, imgtype = getChannelData(stuffs[0].bump)
        matlines = matlines.replace(
            '%%normal%%','bump_map {%s "%s_bump.%s" bump_size %s interpolate 2}' % (
                imgtype, stuffs[0].name,(stuffs[0].bump[1].split("."))[1],str(
                    settings['wrinkles'])))         
        if settings['SSS']:
            matlines = matlines.replace(
                '%%bluenormal%%','bump_map {%s "%s_bump.%s" bump_size 3*%s interpolate 2}' % (
                    imgtype, stuffs[0].name,(stuffs[0].bump[1].split("."))[1],str(settings['wrinkles'])))         
            matlines = matlines.replace(
                '%%greennormal%%','bump_map {png "%s_sss_greenbump.png" bump_size 3*%s interpolate 2}' % (
                    stuffs[0].name, str(settings['wrinkles'])))         
            matlines = matlines.replace(
                '%%rednormal%%','bump_map {png "%s_sss_redbump.png" bump_size 3*%s interpolate 2}' % (
                    stuffs[0].name, str(settings['wrinkles'])))         
    else:
        matlines = matlines.replace(
            '%%normal%%','wrinkles %s scale 0.0002' % str(settings['wrinkles']))         
        if settings['SSS']:
            matlines = matlines.replace(
                '%%bluenormal%%','wrinkles 3*%s scale 0.0002' % str(settings['wrinkles']))         
            matlines = matlines.replace(
                '%%greennormal%%','wrinkles 1.5*%s scale 0.0004' % str(settings['wrinkles']))         
            matlines = matlines.replace(
                '%%rednormal%%','wrinkles 0.75*%s scale 0.0006' % str(settings['wrinkles']))
    matlines = matlines.replace('%%name%%', stuffs[0].name)    
    matlines = matlines.replace(
        '%%ambience%%','rgb <%f,%f,%f>' % settings['scene'].environment.ambience)
    outputFileDescriptor.write(matlines)
    outputFileDescriptor.write('\n')
    
    progress(progbase+0.65*(nextpb-progbase),"Writing Materials")
    writeItemsMaterials(outputFileDescriptor, stuffs, settings, outputDirectory)
    outputFileDescriptor.close()

    # Write .pov scene file.
    writeScene(outputSceneFile, stuffs, settings)
    progbase = nextpb

    nextpb = 1.0
    writeTextures(stuffs, outputDirectory, lambda p: progress(progbase+p*(nextpb-progbase),"Writing Textures"))
    
    progress(1,"Finished. Pov-Ray project exported successfully at %s" % outputDirectory)

def writeTextures(stuffs, outDir, progressCallback = None):
    def progress(prog):
        if progressCallback == None:
            gui3d.app.progress(prog)
        else:
            progressCallback(prog)
    progress(0)
    
    i = 0.0
    stuffnum = float(len(stuffs))
    for stuff in stuffs:
        if stuff.textureImage:
            teximg = stuff.textureImage
        elif stuff.texture:
            teximg = mh.Image(path = collect.getpath(stuff.texture))
        # Export diffuse texture, with subtextures.
        teximg.save(os.path.join(
            outDir,"%s_texture.png" % stuff.name))
        progress((i+0.4)/stuffnum)
        # Export transparency map.
        imgop.getAlpha(teximg).save(path = os.path.join(outDir,"%s_alpha.png" % stuff.name))
        progress((i+0.8)/stuffnum)
        # Export bump map.
        if stuff.bump:
            collect.copy(stuff.bump, os.path.join(
                outDir, "%s_bump.%s" % (stuff.name,(
                    stuff.bump[1].split("."))[1])))
        elif stuff.displacement:
            collect.copy(stuff.displacement, os.path.join(
                outDir, "%s_bump.%s" % (stuff.name,(
                    stuff.displacement[1].split("."))[1])))
        i += 1.0
        progress(i/stuffnum)
        
def writeItemsMaterials(hfile, stuffs, settings, outDir):
    for stuff in stuffs[1:]:
        texdata = getChannelData(stuff.texture)
        if settings['usebump'] == False:
            bumpdata = None
        elif stuff.bump:
            bumpdata = getChannelData(stuff.bump)
            bumpext = stuff.bump[1].split(".")[1]
        elif stuff.displacement:
            bumpdata = getChannelData(stuff.displacement)
            bumpext = stuff.displacement[1].split(".")[1]
        else:
            bumpdata = None
        if stuff.type == 'Hair':
            if settings['hairShine']:
                hinfile = open ("data/povray/hair_2.inc",'r')
            else:
                hinfile = open ("data/povray/hair_0.inc",'r')
        else:
            hinfile = open ("data/povray/clothes.inc",'r')
        inlines = hinfile.read()
        hinfile.close()
        inlines = inlines.replace ("%%name%%",stuff.name)
        inlines = inlines.replace (
            "%%ambience%%", 'rgb <%f,%f,%f>' %
            settings['scene'].environment.ambience)
        if stuff.type == 'Hair':
            if settings['hairShine']:
                inlines = inlines.replace ("%%spec%%",str(settings['hairSpec']))
                inlines = inlines.replace ("%%hard%%",str(settings['hairHard']))
                inlines = inlines.replace ("%%rough%%",str(settings['hairRough']))
            inlines = inlines.replace (
                "%%texture%%", '%s "%s_texture.%s"' %
                (texdata[1], stuff.name, stuff.texture[1].split(".")[1]))
            if bumpdata:
                inlines = inlines.replace (
                    "%%bumpmap%%", '%s "%s_bump.%s"' %
                    (bumpdata[1], stuff.name, bumpext))
            elif settings['hairShine']:
                inlines = inlines.replace (
                    "%%bumpmap%%", 'png "%s_alpha.png"' % stuff.name)
        else:               
            if texdata:                
                inlines = inlines.replace (
                    "%%texture%%", 'image_map {%s "%s_texture.%s" interpolate 2}' %
                    (texdata[1], stuff.name, stuff.texture[1].split(".")[1]))
            else:
                inlines = inlines.replace ("%%texture%%", 'rgb <1,1,1>')
            if bumpdata:
                inlines = inlines.replace (
                    "%%bumpmap%%", 'bump_map {%s "%s_bump.%s" interpolate 2}' %
                    (bumpdata[1], stuff.name, bumpext))
            else:
                inlines = inlines.replace (
                    "%%bumpmap%%", 'wrinkles 0.2 scale 0.0001')
        hfile.write(inlines)


def getChannelData(value):
    if value:
        (folder, file) = value
        (fname, ext) = os.path.splitext(file)
        ext = ext.lower()
        if ext == ".tif":
            type = "tiff"
        elif ext == ".jpg":
            type = "jpeg"
        else:
            type = ext[1:]
        return file,type
    else:
        return None
                
def povrayWriteMesh2(hfile, stuffs, progressCallback = None):

    def progress(prog):
        if progressCallback == None:
            gui3d.app.progress(prog)
        else:
            progressCallback(prog)
    progress(0)
        
    i = 0.0
    stuffnum = float(len(stuffs))
    for stuff in stuffs:
        obj = stuff.meshInfo.object

        hfile.write('// Mesh2 object definition\n')
        hfile.write('#declare %s_Mesh2Object = mesh2 {\n' % stuff.name)

        # Vertices
        hfile.write('  vertex_vectors {\n      %s\n  ' % len(obj.coord))
        for co in obj.coord:
            hfile.write('<%s,%s,%s>' % (-co[0],co[1],co[2]))
        hfile.write('\n  }\n\n')
        progress((i+0.142)/stuffnum)

        # Normals
        hfile.write('  normal_vectors {\n      %s\n  ' % len(obj.vnorm))
        for no in obj.vnorm:
            hfile.write('<%s,%s,%s>' % (-no[0],no[1],no[2]))
        hfile.write('\n  }\n\n')
        progress((i+0.286)/stuffnum)
    
        # UV Vectors
        hfile.write('  uv_vectors {\n      %s\n  ' % len(obj.texco))
        for uv in obj.texco:
            hfile.write('<%s,%s>' % tuple(uv))        
        hfile.write('\n  }\n\n')
        progress((i+0.428)/stuffnum)
        
        nTriangles = 2*len(obj.fvert) # MH faces are quads.

        hfile.write('  face_indices {\n      %s\n  ' % nTriangles)
        for fverts in obj.fvert:
            hfile.write('<%s,%s,%s>' % (fverts[0], fverts[1], fverts[2]))
            hfile.write('<%s,%s,%s>' % (fverts[2], fverts[3], fverts[0]))
        hfile.write('\n  }\n\n')
        progress((i+0.714)/stuffnum)


        # UV Indices for each face
        hfile.write('  uv_indices {\n      %s\n  ' % nTriangles)
        for fuv in obj.fuvs:
            hfile.write('<%s,%s,%s>' % (fuv[0], fuv[1], fuv[2]))
            hfile.write('<%s,%s,%s>' % (fuv[2], fuv[3], fuv[0]))
        hfile.write('\n  }\n')

        # Write the end squiggly bracket for the mesh2 object declaration
        hfile.write('\n      uv_mapping\n}\n\n')
        
        i += 1.0
        progress(i/stuffnum)

def povrayWriteArray(hfile, stuffs, progressCallback = None):

    def progress(prog):
        if progressCallback == None:
            gui3d.app.progress(prog)
        else:
            progressCallback(prog)
    progress(0)

    obj = stuffs[0].object
    
    # Vertices
    hfile.write('#declare MakeHuman_VertexArray = array[%s] {\n  ' % len(obj.coord))
    for co in obj.coord:
        hfile.write('<%s,%s,%s>' % (co[0], co[1], co[2]))
    hfile.write("\n}\n\n")

    # Normals
    hfile.write('#declare MakeHuman_NormalArray = array[%s] {\n  ' % len(obj.vnorm))
    for no in obj.vnorm:
        hfile.write('<%s,%s,%s>' % (no[0], no[1], no[2]))
    hfile.write("\n}\n\n")

    faces = [f for f in obj.faces if not 'joint-' in f.group.name]

    # UV Vectors
    hfile.write('#declare MakeHuman_UVArray = array[%s] {\n  ' % len(obj.texco))
    for uv in obj.texco:
        
        hfile.write('<%s,%s>' % (uv[0], uv[1]))

    # hfile.write("\n")
    hfile.write("\n}\n\n")

    # Faces
    hfile.write('#declare MakeHuman_FaceArray = array[%s][3] {\n  ' % (len(faces) * 2))
    for f in faces:
        hfile.write('{%s,%s,%s}' % (f.verts[0].idx, f.verts[1].idx, f.verts[2].idx))
        hfile.write('{%s,%s,%s}' % (f.verts[2].idx, f.verts[3].idx, f.verts[0].idx))
    hfile.write("\n}\n\n")

    # FaceGroups - Write a POV-Ray array to the output stream and build a list of indices
    # that can be used to cross-reference faces to the Face Groups that they're part of.
    hfile.write('#declare MakeHuman_FaceGroupArray = array[%s] {\n  ' % obj.faceGroupCount)
    fgIndex = 0
    faceGroupIndex = {}
    for fg in obj.faceGroups:
        faceGroupIndex[fg.name] = fgIndex
        hfile.write('  "%s",\n' % fg.name)
        fgIndex += 1
    hfile.write("}\n\n")

    # FaceGroupIndex
    hfile.write('#declare MakeHuman_FaceGroupIndexArray = array[%s] {\n  ' % len(faces))
    for f in faces:
        hfile.write('%s,' % faceGroupIndex[f.group.name])
    hfile.write("\n}\n\n")

    # UV Indices for each face
    hfile.write('#declare MakeHuman_UVIndexArray = array[%s][3] {\n  ' % (len(faces) * 2))
    for f in faces:
        hfile.write('{%s,%s,%s}' % (f.uv[0], f.uv[1], f.uv[2]))
        hfile.write('{%s,%s,%s}' % (f.uv[2], f.uv[3], f.uv[0]))
    hfile.write("\n}\n\n")

    # Joint Positions
    faceGroupExtents = {}
    for f in obj.faces:
        if 'joint-' in f.group.name:

      # Compare the components of each vertex to find the min and max values for this faceGroup

            if f.group.name in faceGroupExtents:
                maxX = max([f.verts[0].co[0], f.verts[1].co[0], f.verts[2].co[0], f.verts[3].co[0], faceGroupExtents[f.group.name][3]])
                maxY = max([f.verts[0].co[1], f.verts[1].co[1], f.verts[2].co[1], f.verts[3].co[1], faceGroupExtents[f.group.name][4]])
                maxZ = max([f.verts[0].co[2], f.verts[1].co[2], f.verts[2].co[2], f.verts[3].co[2], faceGroupExtents[f.group.name][5]])
                minX = min([f.verts[0].co[0], f.verts[1].co[0], f.verts[2].co[0], f.verts[3].co[0], faceGroupExtents[f.group.name][0]])
                minY = min([f.verts[0].co[1], f.verts[1].co[1], f.verts[2].co[1], f.verts[3].co[1], faceGroupExtents[f.group.name][1]])
                minZ = min([f.verts[0].co[2], f.verts[1].co[2], f.verts[2].co[2], f.verts[3].co[2], faceGroupExtents[f.group.name][2]])
            else:
                maxX = max([f.verts[0].co[0], f.verts[1].co[0], f.verts[2].co[0], f.verts[3].co[0]])
                maxY = max([f.verts[0].co[1], f.verts[1].co[1], f.verts[2].co[1], f.verts[3].co[1]])
                maxZ = max([f.verts[0].co[2], f.verts[1].co[2], f.verts[2].co[2], f.verts[3].co[2]])
                minX = min([f.verts[0].co[0], f.verts[1].co[0], f.verts[2].co[0], f.verts[3].co[0]])
                minY = min([f.verts[0].co[1], f.verts[1].co[1], f.verts[2].co[1], f.verts[3].co[1]])
                minZ = min([f.verts[0].co[2], f.verts[1].co[2], f.verts[2].co[2], f.verts[3].co[2]])
            faceGroupExtents[f.group.name] = [minX, minY, minZ, maxX, maxY, maxZ]

    # Write out the centre position of each joint
    for fg in obj.faceGroups:
        if 'joint-' in fg.name:
            jointVarName = string.replace(fg.name, '-', '_')
            jointCentreX = (faceGroupExtents[fg.name][0] + faceGroupExtents[fg.name][3]) / 2
            jointCentreY = (faceGroupExtents[fg.name][1] + faceGroupExtents[fg.name][4]) / 2
            jointCentreZ = (faceGroupExtents[fg.name][2] + faceGroupExtents[fg.name][5]) / 2

      # jointCentre  = "<"+jointCentreX+","+jointCentreY+","+jointCentreZ+">"

            hfile.write('#declare MakeHuman_%s=<%s,%s,%s>;\n' % (jointVarName, jointCentreX, jointCentreY, jointCentreZ))
    hfile.write("\n\n")

    #TEMP# Write the rest using Mesh2 format.
    povrayWriteMesh2(hfile,stuffs[1:])


def povrayProcessSSS(stuffs, outDir, settings, progressCallback = None):

    def progress(prog):
        if progressCallback == None:
            gui3d.app.progress(prog)
        else:
            progressCallback(prog)
    progress(0)
        
    progbase = 0
    nextpb = 1 - 0.65*settings['usebump']
    # get lightmap
    lmap = projection.mapSceneLighting(
        settings['scene'],progressCallback = lambda p: progress(0.3*nextpb*p))
    lmap = imgop.getChannel(lmap,1)
    # prepare channels
    black = imgop.Image(data=imgop.numpy.zeros((lmap.height, lmap.width, 1), dtype=imgop.numpy.uint8))
    # calculate blur level of each cannel, according to settings
    sssa = float(settings['SSSA'])
    # blue channel
    imgop.compose([black,black,lmap]).save(
        os.path.join(outDir, '%s_sss_bluelmap.png' % stuffs[0].name))
    # green channel
    progress(0.4*nextpb)
    lmap2 = imgop.blurred(lmap, 10*sssa, 13, lambda p: progress((0.4+0.3*p)*nextpb))
    imgop.compose([black,lmap2,black]).save(
        os.path.join(outDir, '%s_sss_greenlmap.png' % stuffs[0].name))
    # red channel
    progress(0.7*nextpb)
    lmap2 = imgop.blurred(lmap2, 20*sssa, 13, lambda p: progress((0.7+0.3*p)*nextpb))
    imgop.compose([lmap2,black,black]).save(
        os.path.join(outDir, '%s_sss_redlmap.png' % stuffs[0].name))
    progbase = nextpb
    progress(progbase)
    if settings['usebump']:
        # Export blurred bump maps
        lmap = imgop.Image(os.path.join(stuffs[0].bump[0], stuffs[0].bump[1]))
        lmap = imgop.getChannel(lmap,1)
        lmap = imgop.blurred(lmap, float(lmap.width)/1024*5*sssa, 15,
                             lambda p: progress(progbase+0.5*p*(1-progbase)))
        progress(progbase+0.5*(1-progbase))
        lmap.save(os.path.join(outDir, '%s_sss_greenbump.png' % stuffs[0].name))
        lmap = imgop.blurred(lmap, float(lmap.width)/1024*10*sssa, 15,
                             lambda p: progress(progbase+(0.5+0.5*p)*(1-progbase)))
        lmap.save(os.path.join(outDir, '%s_sss_redbump.png' % stuffs[0].name))
        progress(1.0)

def getHumanName():
    sav = str(gui3d.app.categories['Files'].tasksByName['Save'].fileentry.edit.text())
    if sav == "":
        return 'Untitled'
    else:
        return (os.path.basename(sav).split("."))[0]

def invx(pos):
    return (-pos[0],pos[1],pos[2])

    
