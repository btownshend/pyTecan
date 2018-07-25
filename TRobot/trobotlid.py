import trobot
import sys
import time
import logging

if len(sys.argv)!=2 or ( sys.argv[1]!="OPEN" and sys.argv[1]!="CLOSE"):
    print "Usage: %s (OPEN|CLOSE)"%sys.argv[0]
    exit(2)
cmd=sys.argv[1]
p=trobot.TRobot()
numAttempts=20
logging.info("Status: %s"%str(p.getstatus()))

for attempt in range(numAttempts):
    try:
        lidstatus=p.getlidstatus()
        #p.email("cmd=%s, lidstatus=%s"%(cmd,lidstatus))
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

        for i in range(20):
            lidstatus=p.getlidstatus()
            logging.info( "Lid status: %s"%str(lidstatus))
            if cmd=="OPEN":
                if lidstatus.isopen():
                    exit(0)
            else:
                if lidstatus.isclosed():
                    exit(0)

            time.sleep(2)
    except ValueError as exc:
        logging.warning("LID operation failed %d times: Exception: %s"%(attempt+1,str(exc)))
        p.email("LID operation failed %d times: Exception: %s"%(attempt+1,str(exc)))
        # Flush buffer
        while p.readline()!="":
            print("Flushed line")
        logging.info("Status before clear: %s"%str(p.getstatus()))
        p.clearerrors()
        logging.info("Status after clear: %s"%str(p.getstatus()))
        if attempt>0:
            # Reopen
            logging.info("Closing connection")
            p.close()
            logging.info("Reopening connection")
            p.open()
            logging.info("Lid Temp=%f, Block temp=%f"%(p.getlidtemp(), p.gettemp()))

        logging.info("Sleeping %d seconds..."%(10*attempt))
        time.sleep(10*attempt)
        logging.info("Retrying")

logging.error( "Lid is not completing operation")
exit(1)
