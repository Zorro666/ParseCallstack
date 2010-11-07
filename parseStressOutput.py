import sys
import os
import getopt
import hashlib

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

	# START - Optional parameters for debug output
	debug = 0
	numEntriesToOutput = 5
	# END - Optional parameters for debug output

	# Internal variables with initial values
	state = lookingForRUN
	callstackState = lookingForSTART

	crashDetails = dict()
	crashUniqueDetails = dict()
	callstackLines = dict()
	callstackLineCounts = dict()

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
				# Parse the crashtag into the level/playlist tag for it 
				# e.g. 04/11/2010 13:10:21.11 Perf_cw2_rooftop_gardens_04_11_2010__12_56:CRASH -> cw2_rooftop_gardens
				# e.g. 04/11/2010  9:46:15.71 Play_MP_Reveal_04_11_2010__08_44:CRASH -> MP_Reveal
				# <blah>_<level/playlist>_<number>
				crashTagTokens = line.split("_")
				crashTags = list()
				for i in range(1,len(crashTagTokens)):
					token = crashTagTokens[i]
					if unicode(token).isnumeric() == False:
							crashTags.append(token)
							continue
					break;
				crashTag = "_".join(crashTags)
					
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
				crashTag = currentCrashDetails[0]
				callstackHash = hashlib.md5()
				for i in range(1,len(currentCrashDetails)):
					callstackLine = currentCrashDetails[i]
					# Add a hash for each line in the callstack
					callstackLineHash = hashlib.md5()
					callstackLineHash.update(callstackLine)
					callstackLineHexHash = callstackLineHash.hexdigest()
					callstackLineCounts.setdefault(callstackLineHexHash, []).append(crashTag)
					callstackLines[callstackLineHexHash] = callstackLine

					# Make a combined hash from the total callstack
					callstackHash.update(callstackLine)

				currentUniqueHash = callstackHash.hexdigest()

				crashDetails.setdefault(currentUniqueHash, []).append(currentCrashDetails)
				crashUniqueDetails.setdefault(currentUniqueHash, []).append(crashTag)
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

	numUniqueCrashes = len(crashUniqueDetails)
	numCrashes = 0
	for crashHash, crashList in crashDetails.items():
		for crashDetail in crashList:
			numCrashes += 1

	# Sort the unique crashes to put the most common at the top
	# Make a list of the hashes with counts so we can sort them
	uniqueCrashCounts = list()
	for crashHash, crashList in crashDetails.items():
		numCrashesForHash = len(crashList)
		uniqueCrashCounts.append( (crashHash,numCrashesForHash) )

	# Quick bubble sort 
	numUniqueCounts = len(uniqueCrashCounts)
	for i in range(numUniqueCounts):
		for j in range(i+1,numUniqueCounts):
			numCrashI = uniqueCrashCounts[i][1]
			numCrashJ = uniqueCrashCounts[j][1]
			if numCrashJ > numCrashI:
				# Swap element
				tempCrashCount = uniqueCrashCounts[j]
				uniqueCrashCounts[j] = uniqueCrashCounts[i]
				uniqueCrashCounts[i] = tempCrashCount

	# Sort the callstackCounts by the number of counts to put most common at the top
	# Make a list of the hashes with counts so we can sort them
	uniqueCallstackLineCounts = list()
	for callstackLineHash, crashList in callstackLineCounts.items():
		numCrashesForHash = len(crashList)
		uniqueCallstackLineCounts.append( (callstackLineHash,numCrashesForHash) )

	# Quick bubble sort 
	numUniqueCallstackLineCounts = len(uniqueCallstackLineCounts)
	for i in range(numUniqueCallstackLineCounts):
		for j in range(i+1,numUniqueCallstackLineCounts):
			numCrashI = uniqueCallstackLineCounts[i][1]
			numCrashJ = uniqueCallstackLineCounts[j][1]
			if numCrashJ > numCrashI:
				# Swap element
				tempCrashCount = uniqueCallstackLineCounts[j]
				uniqueCallstackLineCounts[j] = uniqueCallstackLineCounts[i]
				uniqueCallstackLineCounts[i] = tempCrashCount

	print "NumUniqueCounts = " + str(numUniqueCounts)
	for i in range(numUniqueCounts):
		crashHash = uniqueCrashCounts[i][0]
		crashDetail = crashUniqueDetails[crashHash]
		print
		print "UNIQUE CRASH: " + crashHash + " NumTimes:" + str(len(crashDetail))
		for detail in crashDetail:
			print "Level/Playlist: " + detail
		print "#### CallStack ####"
		currentCrashDetails = crashDetails[crashHash][0]
		for i in range(1,len(currentCrashDetails)):
			print currentCrashDetails[i]

	print
	print "NumUniqueCallstackLineCounts = " + str(numUniqueCallstackLineCounts)
	for i in range(numUniqueCallstackLineCounts):
		callstackLineHash = uniqueCallstackLineCounts[i][0]
		callstackLine = callstackLines[callstackLineHash]
		callstackDetail = callstackLineCounts[callstackLineHash]
		print
		print callstackLine + " NumTimes:" + str(len(callstackDetail))
		for detail in callstackDetail:
			print "Level/Playlist: " + detail

	if debug > 0:
		print "NumCrashes = " + str(numCrashes)
		for crashHash, crashList in crashDetails.items():
			for crashDetail in crashList:
				currentCrashDetails = crashDetail
				lenCurrentCrashDetails = len(currentCrashDetails);
				if lenCurrentCrashDetails > 0:
					crashTag = currentCrashDetails[0]
				print "################ START CRASH: " + crashHash
				print crashTag
				for i in range(1,lenCurrentCrashDetails):
					print currentCrashDetails[i]
					if i >= numEntriesToOutput:
						break
				print "################ END CRASH ################"
	
	print
	print "NumUniqueCrashes:" + str(numUniqueCrashes) + " NumCrashes:" + str(numCrashes)


#########################################################
#
# Main function call if running from command line
#
#########################################################

if __name__ == "__main__":
    sys.exit(main())

