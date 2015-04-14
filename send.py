#!/usr/bin/env python2.7

import copy
import httplib
import re
import socket
import time


from lib.request.connect import Connect as Request


def connect(hostname)

    try:
        socket.getaddrinfo(hostname, None)
        # print socket.getaddrinfo(hostname,None)
    except socket.gaierror:
        errMsg = "host '%s' does not exist" % hostname
        print errMsg
    except socket.error, ex:
        errMsg = "problem occurred while "
        errMsg += "resolving a host name '%s' ('%s')" % (hostname, str(ex))
        print errMsg

    try:
        page, headers = Request.queryPage(content=True, noteResponseTime=False)
        print "---------------------  page ----------------------------------"    
        print page
        print "--------------------- headers --------------------------------"
        print headers
        print "--------------------------------------------------------------"
       

if __name__ == "__main__":
    connect()