import ptc
import sys

if len(sys.argv)<2:
    print "Usage: ptclistfolder.py FOLDER [ FOLDER ... ]"
    exit(2)
    
p=ptc.PTC(10)   # 10s timeout
p.setdebug()
folders=sys.argv[1:]
for folder in folders:
    print "Scanning folder %s..."%folder
    pgms=p.programs(folder)
    print "pgms=",pgms
exit(0)
