import ptc
import time
import logging

p=ptc.PTC()
firstpass=True

logging.info('Waiting for PTC to complete')
#p.setdebug()
while True:
    status=p.getstatus()
    p.execute("HTIME?")
    p.execute("RTIME?")

    stat=p.getstatus()
    pgmstatus="Running"
    if stat.bsr&stat.PAUSED:
        pgmstatus= "PAUSED"
    if stat.bsr&stat.RUNNING == 0:
        pgmstatus="NOT RUNNING"
    etime=stat.etime-stat.stime
    minutes=int(etime/60)
    seconds=etime-minutes*60

    print  "%s %s step %d cycle %d/%d: '%s', T=%.1f, Lid=%.1f, step elapsed=%.0f seconds, total remaining=%d:%02d"%(pgmstatus,stat.pgm,stat.step,stat.cycle,stat.cycles,stat.cmd,stat.calctemp,stat.lidtemp,stat.stime,minutes,seconds)
    if stat.bsr&stat.RUNNING == 0:
        if firstpass:
            logging.warning( "No program running")
        break
    # noinspection PyRedeclaration
    firstpass=False
    if etime<=0.0:
        logging.info( "Proceeding to next step")
        p.execute("PROCEED")
    else:
        time.sleep(min(5,etime))

logging.info('PTC done')
