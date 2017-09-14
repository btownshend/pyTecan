import trobot
import sys
import time
import logging

if len(sys.argv)!=2 or ( sys.argv[1]!="OPEN" and sys.argv[1]!="CLOSE"):
    print "Usage: %s (OPEN|CLOSE)"%sys.argv[0]
    exit(2)
cmd=sys.argv[1]
p=trobot.TRobot()

lidstatus=p.getlidstatus()
if cmd=="OPEN":
    if lidstatus.isopen():
        print "Already open"
        exit(0)
    p.lidopen()
elif cmd=="CLOSE":
    if lidstatus.isclosed():
        print "Already closed"
        exit(0)
    p.lidclose()

for i in range(100):
    lidstatus=p.getlidstatus()
    logging.info( "Lid status: %s"%str(lidstatus))
    if cmd=="OPEN":
        if lidstatus.isopen():
            exit(0)
    else:
        if lidstatus.isclosed():
            exit(0)

    time.sleep(2)

logging.error( "Lid is not completing operation")
exit(1)
