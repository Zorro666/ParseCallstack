import sys
import os
import getopt
import hashlib

# Callstack example inside a big log file
# 04/11/2010 13:10:21.11 Perf_cw2_church_04_11_2010__12_56:RUN 
# 04/11/2010 13:10:21.11 Perf_cw2_church_04_11_2010__12_56:CRASH 
# 04/11/2010  9:35:54.31 Play_MP_Reveal_04_11_2010__08_35:END

#logFileName = "home/jake/Documents/main_pc.log"
#logFileName = "home/jake/Documents/main_360.log"
#logFileName = "home/jake/Documents/main_ps3.log"

class Usage(Exception):
	def __init__(self, msg):
		self.msg = msg

#########################################################
#
# main function wrapper for parseStressOutput
#
#########################################################

def main(argv=None):
	if argv is None:
		argv = sys.argv
	try:
		try:
			opts, args = getopt.getopt(argv[1:], "h", ["help"])
		except getopt.error, msg:
			raise Usage(msg)

		return parseStressOutput(opts,args)

	except Usage, err:
		print >>sys.stderr, err.msg
		print >>sys.stderr, "for help use --help"
		return 2

#########################################################
#
# parseStressOutput function
#
#########################################################

def parseStressOutput(opts,args):

	# Constants
	lookingForRUN = 0
	lookingForCRASH = 1
	lookingForEND = 2

	lookingForSTART = 0
	parseCALLSTACK = 1

	# Optional parameters for debug output
	debug = 0
	numEntriesToOutput = 5

	# Internal variables with initial values
	state = lookingForRUN
	callstackState = lookingForSTART

	crashDetails = list()
	crashHashes = list()
	crashUniqueHashes = list()
	crashUniqueCrashes = list()

	logFileName = args[0]
	if os.path.isfile(logFileName) == False:
		print >>sys.stderr, "ERROR: Stress output log file not found:"+logFileName
		return 2

	inputfile = file(logFileName,"rU")
	if inputfile == None:
		print >>sys.stderr, "ERROR: failed to open file:"+logFileName
		return 2

	while True:
		line = inputfile.readline()
		if len(line) == 0:
			break

		# remove the newline from the line string
		line = line.splitlines()[0]
		line = line.strip()

		if state == lookingForRUN:
			# Look for the RUN line e.g. 04/11/2010 13:10:21.11 Perf_cw2_church_04_11_2010__12_56:RUN 
			if line.endswith(":RUN"):
				state = lookingForCRASH
				continue

		if state == lookingForCRASH:
			# Look for the CRASH line e.g. 04/11/2010 13:10:21.11 Perf_cw2_church_04_11_2010__12_56:CRASH 
			if line.endswith(":CRASH"):
				state = lookingForEND
				callstackState = lookingForSTART
				# Found a crash mark it
				currentCrashDetails = list()
				crashTag = line
				currentCrashDetails.append(crashTag)
				continue

		if state == lookingForEND:
			# Look for the END line e.g. 04/11/2010 13:10:21.11 Perf_cw2_church_04_11_2010__12_56:END 
			if line.endswith(":END"):
				state = lookingForRUN

			# Ignore lines from suspended threads e.g.  Suspended thread (RenderThread):
			# This also marks the end of the callstack
			if line.startswith("Suspended thread"):
				state = lookingForRUN

			if state == lookingForRUN:
				if debug > 0:
					print "################ CRASH ################"
					for entry in currentCrashDetails:
						print entry
					print ""

				# Make a total hash of the callstack for pure equivalence testing
				rawCallstack = currentCrashDetails
				crashTag = rawCallstack[0]
				rawCallstack.pop(0)
				callstackHash = hashlib.md5()
				for entry in currentCrashDetails:
					callstackHash.update(entry)

				currentUniqueHash = callstackHash.hexdigest()

				crashDetails.append(currentCrashDetails)
				crashHashes.append(currentUniqueHash)

				if currentUniqueHash in crashUniqueHashes:
					# This crash has already happened append the crash info to the crashUniqueCrashes list
					foundIndex = crashUniqueHashes.index(currentUniqueHash)
					crashUniqueCrashes[foundIndex].append(crashTag)
				else:
					# A new crash
					crashUniqueHashes.append(currentUniqueHash)
					crashTags = list()
					crashTags.append(crashTag)
					crashUniqueCrashes.append(crashTags)

				continue

			if callstackState == lookingForSTART:
				# Now looking for the start of the call stack e.g. "Call Stack Trace:"
				if line.startswith("Call Stack Trace:"):
					callstackState = parseCALLSTACK
					continue

			if callstackState == parseCALLSTACK:
				# Parse each stack line
				# Looking for patterns like this: 
				# 38) function=0x8009C4B4
				# 32) IDebugCallStack::FatalError() [idebugcallstack.cpp:144] 
				# i.e. <number> + ") " + "function=" + <ASCII>
				# OR
				# i.e. <number> + ") " + <ASCII> + " [" + <ASCII> + ":" + <number> + "]"
				lineTokens = line.split(")")
				if unicode(lineTokens[0]).isnumeric() == False:
					continue

				lineTokens.pop(0)
				callstackLine = ")".join(lineTokens)
				callstackLine = callstackLine.strip()
				currentCrashDetails.append(callstackLine)

	print "NumCrashDetails = " + str(len(crashDetails))
	print "NumCrashUniqueHashes = " + str(len(crashUniqueHashes))
	for currentCrash, crash in enumerate(crashDetails):
		currentCrashDetails = crash
		if len(currentCrashDetails) > 0:
			crashTag = currentCrashDetails[0]
			print "################ START CRASH: " + crashHashes[currentCrash]
			print crashTag
			currentCrashDetails.pop(0)
			for index,entry in enumerate(currentCrashDetails):
				print entry
				if index > numEntriesToOutput:
					break
			print "################ END CRASH ################"
			currentCrash += 1
	
	print "NumUniqueCrashes = " + str(len(crashUniqueCrashes))
	for currentCrash, uniqueCrashTags in enumerate(crashUniqueCrashes):
		crashUniqueHash = crashUniqueHashes[currentCrash]
		print "################ START UNIQUE CRASH: " + crashUniqueHash
		for crashTag in uniqueCrashTags:
			print crashTag
		crashIndex = crashHashes.index(crashUniqueHash)
		currentCrashDetails = crashDetails[crashIndex]
		currentCrashDetails.pop(0)
		for index,entry in enumerate(currentCrashDetails):
			print entry
			if index > numEntriesToOutput:
				break
		print "################ END UNIQUE CRASH ################"

	print "NumCrashDetails = " + str(len(crashDetails))
	print "NumCrashUniqueHashes = " + str(len(crashUniqueHashes))
	print "NumUniqueCrashes = " + str(len(crashUniqueCrashes))


#########################################################
#
# Main function call if running from command line
#
#########################################################

if __name__ == "__main__":
    sys.exit(main())

