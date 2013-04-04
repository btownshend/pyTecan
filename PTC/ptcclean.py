# Get status of the various parts of the thermocycler and store in Gemini using named pipes interface
import ptc
import sys

if len(sys.argv)<2:
    print "Usage: ptcclean.py FOLDER [ FOLDER ... ]"
    exit(2)
    
p=ptc.PTC(10)   # 10s timeout
folders=sys.argv[1:]
for folder in folders:
    print "Scanning folder %s..."%folder
    pgms=p.programs(folder)
    print "pgms=",pgms
    for pgm in pgms:
        print "Erasing %s/%s: "%(folder,pgm),
        sys.stdout.flush()
        res=p.erase(pgm)
        print res
        if res!="PGM DELETED":
            print "Error deleting %s/%s: %s" % (folder, pgm, res)
    res=p.execute('DELFOLDER "%s"'%folder)
    print "Deleting folder %s: %s"%(folder,res)
exit(0)
