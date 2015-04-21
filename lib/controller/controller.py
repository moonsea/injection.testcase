#!/usr/bin/env python

import os
import re

from lib.controller.action import action
from lib.controller.checks import checkSqlInjection
# from lib.controller.checks import checkDynParam
from lib.controller.checks import checkStability
from lib.controller.checks import checkString
from lib.controller.checks import checkRegexp
from lib.controller.checks import checkConnection
from lib.controller.checks import checkNullConnection
from lib.controller.checks import checkWaf
from lib.controller.checks import heuristicCheckSqlInjection
from lib.controller.checks import identifyWaf
from lib.core.agent import agent
from lib.core.common import dataToStdout
from lib.core.common import extractRegexResult
from lib.core.common import getFilteredPageContent
from lib.core.common import getPublicTypeMembers
from lib.core.common import getUnicode
from lib.core.common import hashDBRetrieve
from lib.core.common import hashDBWrite
from lib.core.common import intersect
from lib.core.common import parseTargetUrl
from lib.core.common import randomStr
from lib.core.common import randomInt
from lib.core.common import readInput
from lib.core.common import safeCSValue
from lib.core.common import showHttpErrorCodes
from lib.core.common import urlencode
from lib.core.common import urldecode
from lib.core.data import conf
from lib.core.data import kb
from lib.core.data import logger
from lib.core.enums import CONTENT_TYPE
from lib.core.enums import HASHDB_KEYS
from lib.core.enums import HEURISTIC_TEST
from lib.core.enums import HTTPMETHOD
from lib.core.enums import PAYLOAD
from lib.core.enums import PLACE
from lib.core.exception import SqlmapBaseException
from lib.core.exception import SqlmapNoneDataException
from lib.core.exception import SqlmapNotVulnerableException
from lib.core.exception import SqlmapSilentQuitException
from lib.core.exception import SqlmapValueException
from lib.core.exception import SqlmapUserQuitException
from lib.core.settings import ASP_NET_CONTROL_REGEX
from lib.core.settings import DEFAULT_GET_POST_DELIMITER
from lib.core.settings import EMPTY_FORM_FIELDS_REGEX
from lib.core.settings import IGNORE_PARAMETERS
from lib.core.settings import LOW_TEXT_PERCENT
from lib.core.settings import GOOGLE_ANALYTICS_COOKIE_PREFIX
from lib.core.settings import HOST_ALIASES
from lib.core.settings import REFERER_ALIASES
from lib.core.settings import USER_AGENT_ALIASES
from lib.core.target import initTargetEnv
from lib.core.target import setupTargetEnv
from thirdparty.pagerank.pagerank import get_pagerank

def _selectInjection():
    """
    Selection function for injection place, parameters and type.
    """

    points = {}

    for injection in kb.injections:
        place = injection.place
        parameter = injection.parameter
        ptype = injection.ptype

        point = (place, parameter, ptype)

        if point not in points:
            points[point] = injection
        else:
            for key in points[point].keys():
                if key != 'data':
                    points[point][key] = points[point][key] or injection[key]
            points[point]['data'].update(injection['data'])

    if len(points) == 1:
        kb.injection = kb.injections[0]

    elif len(points) > 1:
        message = "there were multiple injection points, please select "
        message += "the one to use for following injections:\n"

        points = []

        for i in xrange(0, len(kb.injections)):
            place = kb.injections[i].place
            parameter = kb.injections[i].parameter
            ptype = kb.injections[i].ptype
            point = (place, parameter, ptype)

            if point not in points:
                points.append(point)
                ptype = PAYLOAD.PARAMETER[ptype] if isinstance(ptype, int) else ptype

                message += "[%d] place: %s, parameter: " % (i, place)
                message += "%s, type: %s" % (parameter, ptype)

                if i == 0:
                    message += " (default)"

                message += "\n"

        message += "[q] Quit"
        select = readInput(message, default="0")

        if select.isdigit() and int(select) < len(kb.injections) and int(select) >= 0:
            index = int(select)
        elif select[0] in ("Q", "q"):
            raise SqlmapUserQuitException
        else:
            errMsg = "invalid choice"
            raise SqlmapValueException(errMsg)

        kb.injection = kb.injections[index]

def _formatInjection(inj):
    data = "Place: %s\n" % inj.place
    data += "Parameter: %s\n" % inj.parameter

    for stype, sdata in inj.data.items():
        title = sdata.title
        vector = sdata.vector
        comment = sdata.comment
        payload = agent.adjustLateValues(sdata.payload)
        if inj.place == PLACE.CUSTOM_HEADER:
            payload = payload.split(',', 1)[1]
        if stype == PAYLOAD.TECHNIQUE.UNION:
            count = re.sub(r"(?i)(\(.+\))|(\blimit[^A-Za-z]+)", "", sdata.payload).count(',') + 1
            title = re.sub(r"\d+ to \d+", str(count), title)
            vector = agent.forgeUnionQuery("[QUERY]", vector[0], vector[1], vector[2], None, None, vector[5], vector[6])
            if count == 1:
                title = title.replace("columns", "column")
        elif comment:
            vector = "%s%s" % (vector, comment)
        data += "    Type: %s\n" % PAYLOAD.SQLINJECTION[stype]
        data += "    Title: %s\n" % title
        data += "    Payload: %s\n" % urldecode(payload, unsafe="&", plusspace=(inj.place == PLACE.POST and kb.postSpaceToPlus))
        data += "    Vector: %s\n\n" % vector if conf.verbose > 1 else "\n"

    return data

def _showInjections():
    header = "sqlmap identified the following injection points with "
    header += "a total of %d HTTP(s) requests" % kb.testQueryCount

    if hasattr(conf, "api"):
        conf.dumper.string("", kb.injections, content_type=CONTENT_TYPE.TECHNIQUES)
    else:
        data = "".join(set(map(lambda x: _formatInjection(x), kb.injections))).rstrip("\n")
        conf.dumper.string(header, data)

    if conf.tamper:
        warnMsg = "changes made by tampering scripts are not "
        warnMsg += "included in shown payload content(s)"
        logger.warn(warnMsg)

    if conf.hpp:
        warnMsg = "changes made by HTTP parameter pollution are not "
        warnMsg += "included in shown payload content(s)"
        logger.warn(warnMsg)

def _randomFillBlankFields(value):
    retVal = value

    if extractRegexResult(EMPTY_FORM_FIELDS_REGEX, value):
        message = "do you want to fill blank fields with random values? [Y/n] "
        test = readInput(message, default="Y")
        if not test or test[0] in ("y", "Y"):
            for match in re.finditer(EMPTY_FORM_FIELDS_REGEX, retVal):
                item = match.group("result")
                if not any(_ in item for _ in IGNORE_PARAMETERS) and not re.search(ASP_NET_CONTROL_REGEX, item):
                    if item[-1] == DEFAULT_GET_POST_DELIMITER:
                        retVal = retVal.replace(item, "%s%s%s" % (item[:-1], randomStr(), DEFAULT_GET_POST_DELIMITER))
                    else:
                        retVal = retVal.replace(item, "%s%s" % (item, randomStr()))

    return retVal

def start():

    try:
              
        ### POST             
        # conf.data = _randomFillBlankFields(conf.data)
        # conf.data = urldecode(conf.data) if conf.data and urlencode(DEFAULT_GET_POST_DELIMITER, None) not in conf.data else conf.data
        testcase_file = open("testcase_file","w")
        print "--------------  Generate Testcase ------------------------"


        # orderList = (PLACE.CUSTOM_POST, PLACE.CUSTOM_HEADER, PLACE.URI, PLACE.POST, PLACE.GET)
        orderList = (PLACE.URI, PLACE.GET)

        parameters = orderList

        for place in parameters:
            
            # paramDict = conf.paramDict[place]
            # ('#1*', u'http://192.168.75.128:80/sqli/example1.php?name=root*')
            paramDict = {'#1*': u'http://192.168.75.128:80/sqli/example1.php?name=root*'}
            # parameter = '#1*'
            # value = u'http://192.168.75.128:80/sqli/example1.php?name=root*'
            for parameter, value in paramDict.items():
            
                ### BOOLEAN TECHNIQUE
                # check = checkDynParam(place, parameter, value)### true if dynamic else false
                #### checkDynParam()
                randInt = randomInt()
                payload = agent.payload(place, parameter, value, getUnicode(randInt))

                print >> testcase_file, payload

                ###  heuristic sql injection
                # check = heuristicCheckSqlInjection(place, parameter)
                origValue = conf.paramDict[place][parameter]

                # according user's input, do heuristiccheck
                prefix = ""
                suffix = ""
                randStr = ""
                while '\'' not in randStr:
                    # HEURISTIC_CHECK_ALPHABET = ('"', '\'', ')', '(', '[', ']', ',', '.')
                    randStr = randomStr(length=10, alphabet=HEURISTIC_CHECK_ALPHABET)
                payload = "%s%s%s" % (prefix, randStr, suffix)
                payload = agent.payload(place, parameter, newValue=payload)
                
                ### without dbmserror and the value is int
                randInt = int(randomInt())
                payload = "%s%s%s" % (prefix, "%d-%d" % (int(origValue) + randInt, randInt), suffix)
                payload = agent.payload(place, parameter, newValue=payload, where=PAYLOAD.WHERE.REPLACE)
                # print >> 
                #### without dbmserror and the value is string
                randStr = randomStr()
                payload = "%s%s%s" % (prefix, "%s%s" % (origValue, randStr), suffix)        
                payload = agent.payload(place, parameter, newValue=payload, where=PAYLOAD.WHERE.REPLACE)

                ### check xss
                # DUMMY_XSS_CHECK_APPENDIX = "<'\">"
                value = "%s%s%s" % (randomStr(), DUMMY_XSS_CHECK_APPENDIX, randomStr())
                payload = "%s%s%s" % (prefix, "'%s" % value, suffix)
                payload = agent.payload(place, parameter, newValue=payload)

                        
                injection = checkSqlInjection(place, parameter, value)               
        
    finally:
        # showHttpErrorCodes()
        testcase_file.close()

    return True
