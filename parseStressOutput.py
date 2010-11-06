import fileinput

# Callstack example inside a big log file
# 04/11/2010 13:10:21.11 Perf_cw2_church_04_11_2010__12_56:RUN 
# 04/11/2010 13:10:21.11 Perf_cw2_church_04_11_2010__12_56:CRASH 
# 04/11/2010  9:35:54.31 Play_MP_Reveal_04_11_2010__08_35:END

lookingForRUN = 0
lookingForCRASH = 1
lookingForEND = 2

lookingForSTART = 0
parseCALLSTACK = 1

state = lookingForRUN
callstackState = lookingForSTART

inputfile = file("/home/jake/Documents/main_pc.log", "rU")
line = inputfile.readline()

while len(line):
	# remove the newline from the line string
	line = line.splitlines()[0]
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
			crashTag = line
			currentCallstack = list()
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
			print "################ CRASH ################"
			print crashTag
			for entry in currentCallstack:
				print entry
			currentCallstack = list()
			print ""
			continue

		if callstackState == lookingForSTART:
			# Now looking for the start of the call stack e.g. "Call Stack Trace:"
			if line.startswith("Call Stack Trace:"):
				callstackState = parseCALLSTACK
		elif callstackState == parseCALLSTACK:
			# Parse each stack line

			if len(line) > 0:
				currentCallstack.append(line)

	line = inputfile.readline()

