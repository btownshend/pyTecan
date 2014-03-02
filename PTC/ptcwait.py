import ptc
import time
import logging

p=ptc.PTC()
logging.info('Waiting for PTC to complete')
#p.setdebug()
while True:
    status=p.getstatus()
    print "\n"
    logging.info("Status=%s",status)
    p.execute("HTIME?")
    p.execute("RTIME?")

    stat=p.getstatus()
    if stat.bsr&stat.RUNNING == 0:
        logging.warning( "No program running")
        break
    etime=stat.etime-stat.stime
    minutes=int(etime/60);
    seconds=etime-minutes*60;
    pgmstatus="Running"
    if stat.bsr&stat.PAUSED:
        pgmstatus= "PAUSED"
        logging.info( "%s %s step %d cycle %d/%d: '%s', T=%.1f, Lid=%.1f, step elapsed=%.0f seconds, total remaining=%d:%02d"%(pgmstatus,stat.pgm,stat.step,stat.cycle,stat.cycles,stat.cmd,stat.calctemp,stat.lidtemp,stat.stime,minutes,seconds))
    if etime<=0.0:
        logging.info( "Proceeding to next step")
        p.execute("PROCEED")
    else:
        time.sleep(min(5,etime))

logging.info('PTC done')
