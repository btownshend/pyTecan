import ptc
import sys
import time
import logging

if len(sys.argv)!=2 or ( sys.argv[1]!="OPEN" and sys.argv[1]!="CLOSE"):
    print "Usage: %s (OPEN|CLOSE)"%sys.argv[0]
    exit(2)
cmd=sys.argv[1]
p=ptc.PTC()
res=p.execute('LID %s'%(cmd))
if len(res)>0:
    logging.debug( "Result=%s",res)
for i in range(30):
    lidstatus=p.getlidstatus()
    logging.info( "Lid is %s"%lidstatus)
    if cmd=="OPEN":
        if lidstatus=="OPEN":
            exit(0)
        elif lidstatus=="ER_TIMEOUT":
            logging.warning("Got ER_TIMEOUT, continuing wait")
        elif lidstatus!="OPENING":
            logging.error( "Unexpected lid status: %s"%lidstatus)
            exit(1)
    else:
        if lidstatus=="CLOSED":
            exit(0)
        elif lidstatus=="ER_TIMEOUT":
            logging.warning("Got ER_TIMEOUT, continuing wait")
        elif lidstatus!="CLOSING":
            logging.error( "Unexpected lid status: %s"%lidstatus)
            exit(1)
    time.sleep(2)

logging.error( "Lid is not completing operation")
exit(1)
