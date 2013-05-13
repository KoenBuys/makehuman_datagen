/** \file main.c
 *  \brief The main C application file.

 <table>
 <tr><td>Project Name:                                   </td>
     <td><b>MakeHuman</b>                                </td></tr>
 <tr><td>Product Home Page:                              </td>
     <td>http://www.makehuman.org/                       </td></tr>
 <tr><td>Google code Home Page:                          </td>
     <td>http://code.google.com/p/makehuman/      </td></tr>
 <tr><td>Copyright(c):                                   </td>
     <td>MakeHuman Team 2001-2013                        </td></tr>
 <tr><td>Licensing:                                      </td>
     <td>AGPL3 (see also
         http://www.makehuman.org/node/318</td></tr>
 <tr><td>Coding Standards:                               </td>
     <td>See http://www.makehuman.org/node/165
                                                         </td></tr>
 </table>

 This is the main C application file used to run the MakeHuman application
 (when compiled as a binary).
 */

#ifdef _DEBUG
#undef _DEBUG
#include <Python.h>
#define _DEBUG
#else
#include <Python.h>
#endif
#include <stdio.h>
#include <stdlib.h>

int main(int argc, char *argv[])
{
    int err;

#ifdef __WIN32__
    //Let's make sure we're in the directory where the executable
    //is since this is required for Makehuman to function on Windows
    //Makehuman will fail to start if you're not in the same directory
    //as the executable
    TCHAR exepath[MAX_PATH];
    if (0 == GetModuleFileName(0, exepath, MAX_PATH)) {
	fprintf(stderr, "coulnd't get executable path\n");
    }
    else {
	PathRemoveFileSpec(exepath);
	SetCurrentDirectory(exepath);
    }
#endif

    Py_SetProgramName(argv[0]);
#if 0
    Py_SetPythonHome(".");
#endif
    Py_Initialize();

    if (!Py_IsInitialized())
    {
        fprintf(stderr, "Could not initialize Python\n");
        exit(EXIT_FAILURE);
    }

    PySys_SetArgv(argc, argv);

    PyEval_InitThreads();

    err = PyRun_SimpleString("execfile('makehuman.py')");

    if (err != 0)
    {
        fprintf(stderr, "Could not run main Python script\n");
        getchar();
        exit(EXIT_FAILURE);
    }

    Py_Finalize();

    return 0;
}

/*
 * Local variables:
 *  compile-command: "gcc -Wall -o makehuman -I/usr/include/python2.7 main.c -lpython2.7"
 * End:
 */

