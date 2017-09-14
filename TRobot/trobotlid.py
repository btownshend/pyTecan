import trobot
import sys
import time
import logging

if len(sys.argv)!=2 or ( sys.argv[1]!="OPEN" and sys.argv[1]!="CLOSE"):
    print "Usage: %s (OPEN|CLOSE)"%sys.argv[0]
    exit(2)
cmd=sys.argv[1]
p=trobot.TRobot()
if cmd=="OPEN":
    p.lidopen()
elif cmd=="CLOSE":
    p.lidclose()

for i in range(100):
    lidstatus=p.getlidstatus()
    logging.info( "Lid is %s"%lidstatus)
    if cmd=="OPEN":
        if lidstatus=="OPEN":
            exit(0)
        elif lidstatus=="ER_TIMEOUT":
            logging.warning("Got ER_TIMEOUT, continuing wait")
        elif lidstatus!="OPENING":
            logging.error( "Unexpected lid status: %s"%lidstatus)
    else:
        if lidstatus=="CLOSED":
            exit(0)
        elif lidstatus=="ER_TIMEOUT":
            logging.warning("Got ER_TIMEOUT, continuing wait")
        elif lidstatus!="CLOSING":
            logging.error( "Unexpected lid status: %s"%lidstatus)

    time.sleep(2)

logging.error( "Lid is not completing operation")
exit(1)
