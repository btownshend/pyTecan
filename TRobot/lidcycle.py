# Cycle lid and log errors
# Tests for issue with lid giving errors after a while

import trobot
import sys
import time
import logging

p=trobot.TRobot()
excnt=[0,0,0]
fd=open('lidcycle.log','a',0)
while True:
    status=1
    print >>fd, "%d,'%s'"%(time.time(),str(p.getstatus())), 
    try:
        lidstatus=p.getlidstatus()
        if lidstatus.isopen():
            print >>fd, ",close",  
            p.lidclose()
            for i in range(20):
                lidstatus=p.getlidstatus()
                if lidstatus.isclosed():
                    print >>fd, ",ok,%d"%i,  
                    status=0
                    break
                time.sleep(2)
        else:
            print >>fd, ",open",  
            p.lidopen()
            for i in range(20):
                lidstatus=p.getlidstatus()
                if lidstatus.isopen():
                    print >>fd, ",ok,%d"%i,  
                    status=0
                    break
                time.sleep(2)
    except ValueError as exc:
        #logging.warning("LID operation failed with exception: %s"%(str(exc)))
        print >>fd, ",'%s'"%(str(exc)),  
        status=2
        # Flush buffer
        extra=p.readline()
        #print >>fd, ",'%s'"%extra,  
        #p.clearerrors()
        #p.close()
        #p.open()

    print >>fd, ",%d"%(time.time())  
    excnt[status]+=1
    print "%d success, %d timeout, %d exception"%(excnt[0],excnt[1],excnt[2])
    time.sleep(60)
    
    
