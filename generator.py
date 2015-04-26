#!/usr/bin/env python

import json
from xml.etree import ElementTree as et

PAYLOADS_XML = ".\\xml\\payloads.xml"
boundaries = [] 
tests = []

def cleanupVals(text, tag):
    if tag in ("clause", "where"):
        text = text.split(',')

    if isinstance(text, basestring):
        text = int(text) if text.isdigit() else str(text)

    elif isinstance(text, list):
        count = 0

        for _ in text:
            text[count] = int(_) if _.isdigit() else str(_)
            count += 1

        if len(text) == 1 and tag not in ("clause", "where"):
            text = text[0]

    return text

def parseXmlNode(node):
    for element in node.getiterator('boundary'):
        boundary = {} 

        for child in element.getchildren():
            if child.text:
                values = cleanupVals(child.text, child.tag)
                boundary[child.tag] = values
            else:
                boundary[child.tag] = None

        boundaries.append(boundary)


    for element in node.getiterator('test'):
        test = {} 

        for child in element.getchildren():
            if child.text and child.text.strip():
                values = cleanupVals(child.text, child.tag)
                test[child.tag] = values
            else:
                if len(child.getchildren()) == 0:
                    test[child.tag] = None
                    continue
                else:
                    test[child.tag] = {} 
 
                for gchild in child.getchildren():
                    if gchild.tag in test[child.tag]:
                        prevtext = test[child.tag][gchild.tag]
                        test[child.tag][gchild.tag] = [prevtext, gchild.text]
                    else:
                        test[child.tag][gchild.tag] = gchild.text

        tests.append(test)

def loadPayloads():
    try:
        doc = et.parse(PAYLOADS_XML)
    except :
        print "[Error]payloads xml load failed"

    root = doc.getroot()
    parseXmlNode(root)
    print len(tests)
    print "------------"
    print len(boundaries)
    with open("tests_xml","w") as tests_xml:
        for node in tests:
            print >> tests_xml, node,"\n"

# with open("tests","w") as tests_file:
# 	json.dump(tests,tests_file)

# with open("boundaries","w") as boundaries_file:


# 	json.dump(boundaries,boundaries_file)
# tests_file = open("tests","w+")

# boundaries_file = open("boundaries","w+")

# # tests_encodejson = json.dumps(tests)
# try:
# 	# tests_file.write(tests_encodejson)
# 	json.dumps(tests,tests_file)
# except:
# 	print "tests_encodejson write failed"
# finally:
# 	tests_file.close()

# boundaries_encodejson = json.dumps(boundaries)

# try:
# 	# boundaries_file.write(boundaries_encodejson)
# 	json.dumps(boundaries,boundaries_file)
# except:
# 	print "boundaries_encodejson write failed"
# finally:
# 	boundaries_file.close()


# tests_file = open("tests","r")
# try:
# 	tests = json.load(tests_file)
# 	print tests
# except:
# 	print "load failed"
# finally:
# 	tests_file.close

# TESTS_FILE = "tests"
# BOUNDARIES_FILE = "boundaries"

def LoadJson():
	with open("tests","r") as tests_file:
		tests = json.load(tests_file)

	with open("boundaries","r") as boundaries_file:
		boundaries = json.load(boundaries_file)
	print tests
	for key in boundaries[0] :
		print key,"---------",boundaries[0][key]


if __name__ == '__main__':
    # LoadJson()
    loadPayloads()
