import ptc
import sys
import string
import logging

if len(sys.argv)!=5 or ( sys.argv[2]!="BLOCK" and sys.argv[2]!="PROBE" and sys.argv[2]!="CALC") :
	print "Usage: %s PGM (BLOCK|PROBE|CALC) (TRACKING,xx|CONSTANT,xx|OFF) volume"%sys.argv[0]
	exit(1)
	
p=ptc.PTC(5)
p.setdebug()

if sys.argv[3]=="OFF":
	hl="OFF"
else:
	ss=string.split(sys.argv[3],',')
	if len(ss)!=2 or (ss[0]!="TRACKING" and ss[0]!="CONSTANT"):
		logging.error( "Bad lid setting: %s"%sys.argv[3])
		exit(1)
	res=p.execute('HOTLID "%s",%s,25'%(ss[0],ss[1]))
	hl="ON"
	

res=p.execute('VESSEL "Plate"');
res=p.execute("VOLUME %s"%sys.argv[4]);
res=p.execute('RUN "%s",%s,%s'%(sys.argv[1],sys.argv[2],hl))
status=p.getstatus()
if (status.bsr & status.RUNNING) == 0:
    logging.error("Failed to start program %s: status=%s"%(sys.argv[1],str(status)))
    exit(1)
if status.pgm!=sys.argv[1]:
    logging.error("Started program '%s', but '%s' is running"%(sys.argv[1],status.pgm))
    exit(1)
exit(0)
