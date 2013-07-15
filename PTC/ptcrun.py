import ptc
import sys

if len(sys.argv)!=5 or ( sys.argv[2]!="BLOCK" and sys.argv[2]!="PROBE" and sys.argv[2]!="CALC") or (sys.argv[3]!="ON" and sys.argv[3]!="OFF"):
    print "Usage: %s PGM (BLOCK|PROBE|CALC) (ON|OFF) volume"%sys.argv[0]
    exit(2)

p=ptc.PTC(5)
res=p.execute("VOLUME %d",sys.argv[4]);
res=p.execute('RUN "%s",%s,%s'%(sys.argv[1],sys.argv[2],sys.argv[3]))
status=p.getstatus()
if (status.bsr & status.RUNNING) == 0:
    print "Failed to start program %s: status=%s"%(sys.argv[1],str(status))
    exit(1)
exit(0)
