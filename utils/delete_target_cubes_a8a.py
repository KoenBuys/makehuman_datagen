#
#   As of 2013.05.08, two joint cubes were deleted from the alpha 8 mesh.
#   This script fixes the targets for this change.
#
#   Run script with python32 from a terminal window. It does not have 
#   any visual interface. It will convert all .target files in the given 
#   directory and recursively in all subdirectories.
#
#   At the top of the script, you find paths to the source directory 
#   containing targets, and the new place where the modified targets 
#   should go. Edit these paths to fit your machine. SourceDirectory 
#   should be the top directory where the existing targets are, 
#   TargetDirectory the new, yet non-existing place for the new ones.
# 
#   MAKE A BACKUP IN A SAFE PLACE BEFORE STARTING!!!! 
# 
#   The script will complain if the target directory already exists, 
#   to prevent that existing morphs are overwritten. If you want to 
#   run the script several times, you must specify a new target directory 
#   each time, or delete the old one. This is not failsafe, but hopefully 
#   it will prevent disasters.
# 

SourceDirectory = "/home/myblends/newmesh"
TargetDirectory = "/home/myblends/gentargets"

import os

ExcludeVerts = [
    # Doublet cube
    14574,
    14575,
    14576,
    14577,
    14578,
    14579,
    14580,
    14581,
    # Cube pair
    14510,
    14511,
    14512,
    14513,
    14514,
    14515,
    14516,
    14517,
]

def setupVertTable():
    global VertTable
    VertTable = {}
    n = 0
    for m in range(20000):
        if m in ExcludeVerts:
            VertTable[m] = -1
        else:
            VertTable[m] = n
            n += 1

            
def fixDirectory():
    srcdir = os.path.realpath(os.path.expanduser(SourceDirectory))
    trgdir = os.path.realpath(os.path.expanduser(TargetDirectory))    
    if os.path.exists(trgdir):
        raise NameError("Target directory \"%s\" already exists. Choose a different place" % trgdir)
    os.makedirs(trgdir)
    setupVertTable()
    fixDirs(srcdir, trgdir, 0)

    
def fixDirs(srcdir, trgdir, depth):    
    if depth > 5:
        raise NameError("Exceeded max recursion depth: %s" % srcdir)
        
    for file in os.listdir(srcdir):
        srcpath = os.path.join(srcdir, file)
        trgpath = os.path.join(trgdir, file)
        if os.path.isfile(srcpath) and os.path.splitext(file)[1] == ".target":
            fixFile(srcpath, trgpath)
        elif os.path.isdir(srcpath):
            os.makedirs(trgpath)
            fixDirs(srcpath, trgpath, depth+1)
        else:
            print("Skipping", srcpath)
        

def fixFile(srcpath, trgpath):        
    print("Fix %s => %s" % (srcpath, trgpath))
    
    fp = open(srcpath, "rU")
    lines = []
    for line in fp:
        first,rest = line.split(None, 1)
        try:
            m = int(first)
        except:
            lines.append(line)
            continue
        n = VertTable[m]
        if n >= 0:
            lines.append(str(n) + " " + rest)
    fp.close()
        
    fp = open(trgpath, "w")
    for line in lines:
        fp.write(line)
    fp.close()
        

fixDirectory()


        
        