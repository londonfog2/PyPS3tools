#!/usr/bin/python
# -*- coding: utf-8 -*-

# *************************************************************************
# PyPS3checker - Python checker scypt for PS3 flash memory dump files
#
# Copyright (C) 2015 littlebalup@gmail.com
#
# This code is licensed to you under the terms of the GNU GPL, version 2;
# see http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt
# *************************************************************************


import os
import time
import sys
import re
import hashlib
from xml.etree import ElementTree
from collections import Counter


class Tee(object):
    def __init__(self, *files):
        self.files = files
    def write(self, obj):
        for f in self.files:
            f.write(obj)

def checkReversed(file):
	bytes = file[0x200:(0x200 + 0x4)]
	if bytes == '\x49\x46\x49\x00':
		return False
	elif bytes == '\x46\x49\x00\x49':
		return True
	else:
		sys.exit("ERROR: unable to define if file %s is byte reversed! It doesn't seem to be a valid dump."%file)

def getDatas(file, offset, length):
	bytes = file[offset:(offset + length)]
	return bytes

def reverse(data):
	return ''.join([c for t in zip(data[1::2], data[::2]) for c in t])

def string2hex(data):
	return "".join("{:02x}".format(ord(c)) for c in data)

def hex2string(data):
    bytes = []
    for i in range(0, len(data), 2):
        bytes.append(chr(int(data[i:i+2], 16)))
    return ''.join(bytes)

def chunks(s, n):
	# Produce `n`-character chunks from `s`.
	for start in range(0, len(s), n):
		yield s[start:start+n]

def print_formatedlines(s, n):
	c = 0
	for chunk in chunks(s, n):
		if c == 0:
			tab = "   >"
		else:
			tab = "    "
		print tab, " ".join(a+b for a,b in zip(chunk[::2], chunk[1::2]))
		c += 1

def getMD5(file, offset, length):
	h = hashlib.md5()
	h.update(getDatas(file, offset, length))
	return h.hexdigest()


if __name__ == "__main__":

	release = "v0.2"


	print
	print "  ____        ____  ____ _____      _               _             "
	print " |  _ \ _   _|  _ \/ ___|___ /  ___| |__   ___  ___| | _____ _ __ "
	print " | |_) | | | | |_) \___ \ |_ \ / __| '_ \ / _ \/ __| |/ / _ \ '__|"
	print " |  __/| |_| |  __/ ___) |__) | (__| | | |  __/ (__|   <  __/ |   "
	print " |_|    \__, |_|   |____/____/ \___|_| |_|\___|\___|_|\_\___|_|   "
	print "        |___/                                               %s "%release
	print
	print "Python checker scypt for PS3 flash memory dump files"
	print "Copyright (C) 2015 littlebalup@gmail.com"
	print
	if len(sys.argv) == 1:
		print "Usage:"
		print "%s [input_file]"%(os.path.basename(__file__))
		print
		print " [input_file]   Dump filename to check."
		print
		print " Examples:"
		print "  %s mydump.bin"%(os.path.basename(__file__))
		sys.exit()


	startTime = time.time()

	# get args and set recording lists and counts
	inputFile = sys.argv[1]
	if not os.path.isfile(inputFile):
		sys.exit("ERROR: input file \"%s\" was not found!"%inputFile)

	dangerList = []
	warningList = []
	checkCount = 0
	dangerCount = 0
	warningCount = 0

	# parse file
	print "Loading file to memory...",
	f = open(inputFile,"rb")
	rawfiledata = f.read()
	f.close()
	# parse xml
	if not os.path.isfile("checklist.xml"):
		sys.exit("ERROR: checklist.xml file was not found!")
	if not os.path.isfile("hashlist.xml"):
		sys.exit("ERROR: hashlist.xml file was not found!")
	with open('checklist.xml', 'rt') as f:
		chktree = ElementTree.parse(f)
	with open('hashlist.xml', 'rt') as f:
		hashtree = ElementTree.parse(f)

	# parse file type:
	isReversed = False
	fileSize = len(rawfiledata)
	if fileSize == 16777216:
		flashType = "NOR"
		if checkReversed(rawfiledata) == True:
			isReversed = True
			rawfiledata = reverse(rawfiledata)
	elif fileSize == 268435456:
		flashType = "NAND"
	else:
		print
		print "ERROR: unable to define flash type! It doesn't seem to be a valid dump."
		quit()

	print " Done"

	# create and start log
	cl = open('%s.checklog.txt'%inputFile, 'w')
	cl.write("PyPS3checker %s. Check log.\n\n"%release + "Checked file : %s\n"%inputFile)
	original = sys.stdout
	sys.stdout = Tee(sys.stdout, cl)

	print
	print
	print "******* Getting flash type *******"
	print "  Flash type :", flashType
	if flashType == "NOR" and isReversed == True:
		print "  Reversed : YES"
	elif flashType == "NOR" and isReversed == False:
		print "  Reversed : NO"


	# SKU identification
	print
	print
	print "******* Getting SKU identification datas *******"
	skufiledata = {}
	for entry in chktree.findall('.//%s/skulistdata/'%flashType):
		filedata = string2hex(getDatas(rawfiledata, int(entry.attrib.get("offset"), 16), int(entry.attrib.get("size"), 16)))
		tag = entry.text
		if tag == "bootldrsize":
			calc = (int(filedata, 16) * 0x10) + 0x40
			filedata = "%X"%calc
		skufiledata[tag] = filedata.lower()
		if tag == "idps":
			print "  %s = 0x%s"%(tag, filedata[-2:].upper())  #print only last 2 digits
		else:
			print "  %s = 0x%s"%(tag, filedata.upper())
	print
	print "  Matching SKU :",
	checkCount += 1
	ChkResult = False
	for node in chktree.findall('.//%s/skumodels'%flashType):
		risklevel = node.attrib.get("risklevel").upper()
	for node in chktree.findall('.//%s/skumodels/'%flashType):
		d = {}
		for subnode in chktree.findall(".//%s/skumodels/%s[@id='%s']/"%(flashType, node.tag, node.attrib.get("id"))):
			tag = subnode.attrib.get("type")
			d[tag] = subnode.text.lower()
		if d == skufiledata:
			ChkResult = True
			print "OK"
			print "   %s"%node.attrib.get("name")
			print "   Minimum version %s"%node.attrib.get("minver")
			if node.attrib.get("warn") == "true":
				warningCount += 1
				warningList.append("SKU identification")
				print " %s"%node.attrib.get("warnmsg")
			break
	if ChkResult == False:
		if risklevel == "DANGER":
			dangerCount += 1
			dangerList.append("SKU identification")
		elif risklevel == "WARNING":
			warningCount += 1
			warningList.append("SKU identification")
		print "%s!"%risklevel
		print "   No matching SKU found!"

	# SDK vesrions
	print
	print
	print "******* Getting SDK versions *******"
	checkCount += 1
	ChkResult = True
	for node in chktree.findall('.//%s/sdk'%flashType):
		risklevel = node.attrib.get("risklevel").upper()
	for sdk in chktree.findall('.//%s/sdk/sdk_version'%flashType):
		index = rawfiledata.find(hex2string("73646B5F76657273696F6E"), int(sdk.attrib.get("offset"), 16), int(sdk.attrib.get("offset"), 16) + 0x4f0)
		addressPos = index - 0xc
		address = int(sdk.attrib.get("offset"), 16) + int(string2hex(getDatas(rawfiledata, addressPos, 0x4)), 16)
		ver = getDatas(rawfiledata, address, 0x8)
		ver = ver[:-1]                       #remove useless last char   
		r = re.compile('\d{3}\.000')         #def format 
		if r.match(ver) is not None:
			print "  %s : %s"%(sdk.attrib.get("name"), ver)
		else:
			print "  %s : (unknown)"%(sdk.attrib.get("name"))
			ChkResult = False
	if ChkResult == False:
		if risklevel == "DANGER":
			dangerCount += 1
			dangerList.append("SDK versions")
		elif risklevel == "WARNING":
			warningCount += 1
			warningList.append("SDK versions")
		print "%s! : unable to get all versions."%risklevel

	# Start other checks
	for node in chktree.findall('.//%s/'%flashType):
		if node.tag not in ["skulistdata", "skumodels", "sdk"]:
			print
			print
			print "******* Checking %s *******"%node.tag

		for subnode in chktree.findall('.//%s/%s/'%(flashType, node.tag)):
			if subnode.attrib.get("risklevel") is not None:
				risklevel = subnode.attrib.get("risklevel").upper()

		 	if subnode.tag == "binentry":
		 		checkCount += 1
				filedata = string2hex(getDatas(rawfiledata, int(subnode.attrib.get("offset"), 16), len(subnode.text)/2))
				print "%s :"%subnode.attrib.get("name"),
				if filedata.lower() == subnode.text.lower():
					print "OK"
				else:
					if risklevel == "DANGER":
						dangerCount += 1
						dangerList.append(subnode.attrib.get("name"))
					elif risklevel == "WARNING":
						warningCount += 1
						warningList.append(subnode.attrib.get("name"))
					print "%s!"%risklevel
					print "  At offset : 0x%s"%subnode.attrib.get("offset").upper()
					if isReversed:
						print "  Actual data (reversed from original) :"
					else:
						print "  Actual data :"
					print_formatedlines(filedata.upper(), 32)
					print "  Expected data :"
					print_formatedlines(subnode.text.upper(), 32)
					print

			if subnode.tag == "multibinentry":
				checkCount += 1
				ChkResult = False
				filedata = string2hex(getDatas(rawfiledata, int(subnode.attrib.get("offset"), 16), int(subnode.attrib.get("length"), 16)))
				print "%s :"%subnode.attrib.get("name"),
				for entry in chktree.findall(".//%s/%s/%s[@name='%s']/"%(flashType, node.tag, subnode.tag, subnode.attrib.get("name"))):
					if filedata.lower() == entry.text.lower():
						print "OK"
						ChkResult = True
						break
				if ChkResult == False:
					if risklevel == "DANGER":
						dangerCount += 1
						dangerList.append(subnode.attrib.get("name"))
					elif risklevel == "WARNING":
						warningCount += 1
						warningList.append(subnode.attrib.get("name"))
					print "%s!"%risklevel
					print "  At offset : 0x%s"%subnode.attrib.get("offset").upper()
					if isReversed:
						print "  Actual data (reversed from original) :"
					else:
						print "  Actual data :"
					print_formatedlines(filedata.upper(), 32)
					print "  Expected data (one of the list):"
					for entry in chktree.findall(".//%s/%s/%s[@name='%s']/"%(flashType, node.tag, subnode.tag, subnode.attrib.get("name"))):
						print_formatedlines(entry.text.upper(), 32)
					print
						
			if subnode.tag == "datafill":
				checkCount += 1
				ChkResult = True
				print "%s :"%subnode.attrib.get("name"),
				if subnode.attrib.get("ldrsize") is not None:
					ldrsize = (int(string2hex(getDatas(rawfiledata, int(subnode.attrib.get("ldrsize"), 16), 0x2)), 16) * 0x10) + 0x40
					start = int(subnode.attrib.get("regionstart"), 16) + ldrsize
					length = int(subnode.attrib.get("regionsize"), 16) - ldrsize
				else:
					start = int(subnode.attrib.get("offset"), 16)
					length = int(subnode.attrib.get("size"), 16)
				filedata = getDatas(rawfiledata, start, length)
				c = 0
				for data in filedata:
					b = string2hex(data)
					if b.lower() != subnode.text.lower():
						ChkResult = False
						FalseOffset = start + c
						FalseValue = b
						break
					c += 1
				f.close()
				if ChkResult:
					print "OK"
				else:
					if risklevel == "DANGER":
						dangerCount += 1
						dangerList.append(subnode.attrib.get("name"))
					elif risklevel == "WARNING":
						warningCount += 1
						warningList.append(subnode.attrib.get("name"))
					print "%s!"%risklevel
					print "  All bytes from offset 0x%X to offset 0x%X should be 0x%s."%(start, start + length, subnode.text.upper())
					print "  Byte at offset 0x%X has value : 0x%s"%(FalseOffset, FalseValue.upper())
					print "  Subsequent bytes in the range may be wrong as well."
					print

			if subnode.tag == "hash":
				checkCount += 1
				ChkResult = False
				print "%s :"%subnode.attrib.get("name"),
				hashdata = getMD5(rawfiledata, int(subnode.attrib.get("offset"), 16), int(subnode.attrib.get("size"), 16))
				for hash in hashtree.findall(".//type[@name='%s']/"%(subnode.attrib.get("type"))):
					if hashdata.lower() == hash.text.lower():
						print "OK"
						ChkResult = True
						print "  MD5 =", hashdata.upper()
						print "  Version =", hash.attrib.get("name")
						break
				if 	ChkResult == False:
					if risklevel == "DANGER":
						dangerCount += 1
						dangerList.append(subnode.attrib.get("name"))
					elif risklevel == "WARNING":
						warningCount += 1
						warningList.append(subnode.attrib.get("name"))
					print "%s!"%risklevel
					print "  MD5 =", hashdata.upper()
					print "  Version = (unknown)"
				print

			if subnode.tag == "datalist":
				print "%s :"%subnode.attrib.get("name"),
				if subnode.attrib.get("ldrsize") is not None:
					d = string2hex(getDatas(rawfiledata, int(subnode.attrib.get("ldrsize"), 16), 0x2))
					size = (int(d, 16) * 0x10) + 0x40
				else:
					size = int(subnode.attrib.get("size"), 16)
				filedata = getDatas(rawfiledata, int(subnode.attrib.get("offset"), 16), size)
				for datatreshold in chktree.findall(".//%s/%s/%s[@name='%s']/"%(flashType, node.tag, subnode.tag, subnode.attrib.get("name"))):
					checkCount += 1
					ChkResult = True
					r = {}
					if datatreshold.attrib.get("key") == "*":
						for k,v in Counter(filedata).items():
							c = float(v) / size * 100
							if c > float(datatreshold.text.replace(',','.')):
								ChkResult = False
								tag = string2hex(k).upper()
								r[tag] = c
					else:
						c = float(filedata.count(chr(int(datatreshold.attrib.get("key"), 16)))) / size * 100
						if c > float(datatreshold.text.replace(',','.')):
							tag = datatreshold.attrib.get("key").upper()
							r[tag] = c
					if ChkResult:
						print "OK"
					else:
						if risklevel == "DANGER":
							dangerCount += 1
							dangerList.append(subnode.attrib.get("name"))
						elif risklevel == "WARNING":
							warningCount += 1
							warningList.append(subnode.attrib.get("name"))
						print "%s!"%risklevel
						if datatreshold.attrib.get("key") == "*":
							print "  Any bytes",
						else:
							print "  0x%s bytes"%datatreshold.attrib.get("key").upper(),
						print "from offset 0x%s to offset 0x%X should be less than %s%%."%(subnode.attrib.get("offset").upper(), int(subnode.attrib.get("offset"), 16) + size, datatreshold.text.replace(',','.'))
						for x in sorted(r.keys()):
							print "    0x%s is %.2f%%"%((x), r[x])

			if subnode.tag == "datamatchid":
				print subnode.text, ":",
				d = {}
				for id in chktree.findall(".//%s/%s//datamatch[@id='%s']"%(flashType, node.tag, subnode.attrib.get("id"))):
					checkCount += 1
					if id.attrib.get("seqrep") is not None:
						c = 0
						while c != int(id.attrib.get("seqrep"), 16):
							filedata = string2hex(getDatas(rawfiledata, int(id.attrib.get("offset"), 16) + c * int(id.attrib.get("length"), 16), int(id.attrib.get("length"), 16)))
							tag = "%s at 0x%X"%(id.text, int(id.attrib.get("offset"), 16) + c * int(id.attrib.get("length"), 16))
							d[tag] = filedata.upper()
							c += 1
					else:
						filedata = string2hex(getDatas(rawfiledata, int(id.attrib.get("offset"), 16), int(id.attrib.get("length"), 16)))
						tag = id.text
						d[tag] = filedata.upper()
				if len(set(d.values())) != 1:
					if risklevel == "DANGER":
						dangerCount += 1
						dangerList.append("datamatches : %s"%subnode.text)
					elif risklevel == "WARNING":
						warningCount += 1
						warningList.append("datamatches : %s"%subnode.text)
					print "%s!"%risklevel
					print "  Following datas should be the same :"
					for id in chktree.findall(".//%s/%s//datamatch[@id='%s']"%(flashType, node.tag, subnode.attrib.get("id"))):
						if id.attrib.get("nodisp") is not None:
							print "  %s at offset 0x%s length 0x%s"%(id.text, id.attrib.get("offset").upper(), id.attrib.get("length").upper())
							print "    (too long to dilplay)"
						elif id.attrib.get("seqrep") is not None:
							print "  %s at offset 0x%s length 0x%s, repeted 0x%s time"%(id.text, id.attrib.get("offset").upper(), id.attrib.get("length").upper(), id.attrib.get("seqrep").upper())
							print "    (too long to dilplay)"
						else:
							print "  %s at offset 0x%s length 0x%s"%(id.text, id.attrib.get("offset").upper(), id.attrib.get("length").upper())
							print_formatedlines(d[id.text], 32)
					print
				else:
					print "OK"

			if subnode.tag == "repcheck":
				checkCount += 1
				ChkResult = True
				print "%s :"%subnode.attrib.get("name"),
				key = hex2string(subnode.text)
				beg = 0
				index = beg
				nothing = True
				indexlist = []
				while index != -1:
					index = rawfiledata.find(key, beg)
					if index != -1 and index != int(subnode.attrib.get("offset"), 16):
						nothing = False
						ChkResult = False
						indexlist.append("0x%X"%index)
					elif index == int(subnode.attrib.get("offset"), 16):
						nothing = False
					beg = index + (len(subnode.text) / 2)
				if nothing or not ChkResult:
					if risklevel == "DANGER":
						dangerCount += 1
						dangerList.append("repcheck : %s"%subnode.attrib.get("name"))
					elif risklevel == "WARNING":
						warningCount += 1
						warningList.append("repcheck : %s"%subnode.attrib.get("name"))
					print "%s!"%risklevel
					print "  Following data expected at offset 0x%s :"%subnode.attrib.get("offset").upper()
					print_formatedlines(subnode.text, 32)
					if nothing:
						print "    No matching data found!"
						print
					else:
						print "  Repetition(s) found at offset(s) :"
						print "   ", ", ".join(indexlist)
						print
				else:
					print "OK"


	print
	print
	print "******* Checks completed *******"
	print
	print "Total number of checks =", checkCount
	print "Number of dangers =", dangerCount
	print "Number of warnings =", warningCount

	if dangerCount > 0:
		print
		print "Following check(s) returned a DANGER :"
		print " ", '\n  '.join(dangerList)
		
	if warningCount > 0:
		print
		print "Following check(s) returned a WARNING :"
		print " ", '\n  '.join(warningList)

	print
	print "All checks done in %.2f seconds."%(time.time() - startTime)

	cl.close()

	if dangerCount > 0:
		sys.exit(3)
	elif warningCount > 0:
		sys.exit(2)
	else:
		sys.exit()
