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
from lib.core.settings import LEGAL_DISCLAIMER
from lib.parse.cmdline import cmdLineParser

def modulePath():
    """
    This will get us the program's directory, even if we are frozen
    using py2exe
    """

    try:
        _ = sys.executable if weAreFrozen() else __file__
    except NameError:
        _ = inspect.getsourcefile(modulePath)

    return os.path.dirname(os.path.realpath(getUnicode(_, sys.getfilesystemencoding())))

def main():
    """
    Main function of sqlmap when running from command line.
    """
    try:
        """
        paths.SQLMAP_ROOT_PATH = modulePath()#Get current path of sqlmap.py
        setPaths()

        # Store original command line options for possible later restoration
        cmdLineOptions.update(cmdLineParser().__dict__)

        initOptions(cmdLineOptions)
        """

        banner()
        #Show the banner of the software

        conf.showTime = True
        dataToStdout("[!] freedom disclaimer: %s\n\n" % LEGAL_DISCLAIMER, forceOutput=True)
        dataToStdout("[*] starting at %s\n\n" % time.strftime("%X"), forceOutput=True)

        """
        init()
        #According to the input parameters, set the configure of the software
        #### Generate testcase
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

 
if __name__ == "__main__":
    main()
