import trobot
import time
import logging

p=trobot.TRobot()
firstpass=True
remt=0

logging.info('Waiting for TRobot to complete')
#p.setdebug()
while True:
    try:
        remt=p.getremainingtime()
        status=p.getrunstatus()
        blocktemp=p.gettemp()
        lidtemp=p.getlidtemp()
        bstatus=p.getstatus()
        lstatus=p.getlidstatus()
        loopcntrs=p.getloopcounters()
    except ValueError:
        print "error"
        if remt>2:
            # Premature termination
            logging.error("Program terminated with %.0f minutes still remaining"%remt)
            sys.exit(1)
        break

    print "%s: [%s] LID=%.1f/%.1f [%s], step=%d, temp=%.1f/%.1f, time=%d, loop=%d, loop#=%s/%d, remt=%d min"%(status.progname, str(bstatus),lidtemp,status.lidtemp,str(lstatus),status.stepnr,blocktemp,status.bltemp,status.htime,status.loop,loopcntrs,status.numloop,remt)
    if remt==0:
        break
    time.sleep(min(5,remt*60))

logging.info('TROBOT done')
