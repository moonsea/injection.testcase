#!/usr/bin/env python2.7

import bdb
import inspect
import logging
import os
import re
import sys
import time
import traceback
import warnings

warnings.filterwarnings(action="ignore", message=".*was already imported", category=UserWarning)
warnings.filterwarnings(action="ignore", category=DeprecationWarning)

from lib.utils import versioncheck
# this has to be the first non-standard import
#   and the function just check the configuration of os

from lib.controller.controller import start
from lib.core.common import banner
#The picture of sqlmap at the top of the software when run it firstly
from lib.core.common import createGithubIssue
from lib.core.common import dataToStdout
from lib.core.common import getUnicode
from lib.core.common import maskSensitiveData
from lib.core.common import setColor
from lib.core.common import setPaths
from lib.core.common import weAreFrozen
from lib.core.data import cmdLineOptions
from lib.core.data import conf
from lib.core.data import kb
from lib.core.data import logger
from lib.core.data import paths
from lib.core.common import unhandledExceptionMessage
from lib.core.exception import SqlmapBaseException
from lib.core.exception import SqlmapShellQuitException
from lib.core.exception import SqlmapSilentQuitException
from lib.core.exception import SqlmapUserQuitException
from lib.core.option import initOptions
from lib.core.option import init
from lib.core.profiling import profile
from lib.core.settings import LEGAL_DISCLAIMER
from lib.core.testing import smokeTest
from lib.core.testing import liveTest
from lib.parse.cmdline import cmdLineParser
#from lib.utils.api import setRestAPILog
#from lib.utils.api import StdDbOut

def modulePath():
    """
    This will get us the program's directory, even if we are frozen
    using py2exe
    """

    try:
        _ = sys.executable if weAreFrozen() else __file__
    except NameError:
        _ = inspect.getsourcefile(modulePath)

    '''
    print "_:"
    print _
    print "__file__:"
    print __file__
    print "real path:"
    print getUnicode(_,sys.getfilesystemencoding())
    print sys.getfilesystemencoding()
    print os.path.realpath(getUnicode(_,sys.getfilesystemencoding()))
    print "------------------------------------------------"
    '''

    return os.path.dirname(os.path.realpath(getUnicode(_, sys.getfilesystemencoding())))

def main():
    """
    Main function of sqlmap when running from command line.
    """

    """"
    print " "
    print "-------------------------------------------------------------------"
    print "------------Just Test conf -------------------------------------------------"
    for i in conf :
        print i
    print conf
    print "-------------------------------------------------------------------"
    """

    try:
        paths.SQLMAP_ROOT_PATH = modulePath()#Get current path of sqlmap.py
        setPaths()

        # Store original command line options for possible later restoration
        cmdLineOptions.update(cmdLineParser().__dict__)

        """
        ###Get the options from cmdline command
        print "-----------------------------------------------------------------"
        print "---------------------  cmdLineOptions ---------------------------"
        print cmdLineOptions
        print "----------------------------------------------------------------"
        for i in cmdLineOptions.keys() :
            print i,"---------",cmdLineOptions[i]
        print "-----------------------------------------------------------------"
        """

        initOptions(cmdLineOptions)

        """
        if hasattr(conf, "api"):
            # Overwrite system standard output and standard error to write
            # to an IPC database
            sys.stdout = StdDbOut(conf.taskid, messagetype="stdout")
            sys.stderr = StdDbOut(conf.taskid, messagetype="stderr")
            setRestAPILog()
        """

        banner()
        #Show the banner of the software

        conf.showTime = True
        dataToStdout("[!] legal disclaimer: %s\n\n" % LEGAL_DISCLAIMER, forceOutput=True)
        dataToStdout("[*] starting at %s\n\n" % time.strftime("%X"), forceOutput=True)

        init()
        #According to the input parameters, set the configure of the software

        if conf.profile:
            profile()
        elif conf.smokeTest:
            smokeTest()
        elif conf.liveTest:
            liveTest()
        else:
        
            """
            print "-------------------------  kb ------------------------------------"
            kb_info_file = open("kb_info_file","w+")
            for key in kb.keys():
                print >> kb_info_file, key,"-------",kb[key]
            print "------------------------------------------------------------------"

            info_file = open("conf_info_file.txt","w+")
            print "-----------------------  conf ----------------------------------"
            for key  in conf.keys():
                print >> info_file, key,"------",conf[key]
            info_file.close()
            print "------------------------------------------------------------------"
            """
            start()

    except SqlmapUserQuitException:
        errMsg = "user quit"
        logger.error(errMsg)

    except (SqlmapSilentQuitException, bdb.BdbQuit):
        pass

    except SqlmapShellQuitException:
        cmdLineOptions.sqlmapShell = False

    except SqlmapBaseException as ex:
        errMsg = getUnicode(ex.message)
        logger.critical(errMsg)
        sys.exit(1)

    except KeyboardInterrupt:
        print
        errMsg = "user aborted"
        logger.error(errMsg)

    except EOFError:
        print
        errMsg = "exit"
        logger.error(errMsg)

    except SystemExit:
        pass

    except:
        print
        errMsg = unhandledExceptionMessage()
        excMsg = traceback.format_exc()

        for match in re.finditer(r'File "(.+?)", line', excMsg):
            file_ = match.group(1)
            file_ = os.path.relpath(file_, os.path.dirname(__file__))
            file_ = file_.replace("\\", '/')
            file_ = re.sub(r"\.\./", '/', file_).lstrip('/')
            excMsg = excMsg.replace(match.group(1), file_)

        errMsg = maskSensitiveData(errMsg)
        excMsg = maskSensitiveData(excMsg)

        logger.critical(errMsg)
        kb.stickyLevel = logging.CRITICAL
        dataToStdout(excMsg)
        createGithubIssue(errMsg, excMsg)

    finally:
        if conf.get("showTime"):
            dataToStdout("\n[*] shutting down at %s\n\n" % time.strftime("%X"), forceOutput=True)

        kb.threadContinue = False
        kb.threadException = True

        if conf.get("hashDB"):
            try:
                conf.hashDB.flush(True)
            except KeyboardInterrupt:
                pass

        if cmdLineOptions.get("sqlmapShell"):
            cmdLineOptions.clear()
            conf.clear()
            kb.clear()
            main()

        if hasattr(conf, "api"):
            try:
                conf.database_cursor.disconnect()
            except KeyboardInterrupt:
                pass

        if conf.get("dumper"):
            conf.dumper.flush()

        # Reference: http://stackoverflow.com/questions/1635080/terminate-a-multi-thread-python-program
        if conf.get("threads", 0) > 1 or conf.get("dnsServer"):
            os._exit(0)

if __name__ == "__main__":
    main()
