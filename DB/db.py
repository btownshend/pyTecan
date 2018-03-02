import sqlite3
import sys
import os
import uuid
import pymysql.cursors
import time
import logging

epath=os.path.join(os.path.dirname(__file__),'..')
sys.path.append(epath)
from Experiment.plate import Plate
from Experiment import decklayout

class TecanDB(object):
    def __init__(self):
        # Setup logging
        self.debug=True
        fname=time.strftime("DB-%Y%m%d.log")
        logging.basicConfig(filename=fname, level=logging.DEBUG,format='%(asctime)s %(levelname)s:\t %(message)s')
        logging.captureWarnings(True)
        console = logging.StreamHandler()
        console.setLevel(logging.DEBUG if self.debug else logging.INFO)
        formatter=logging.Formatter('%(message)s')
        console.setFormatter(formatter)
        logging.getLogger('').addHandler(console)
        
        try:
            os.chdir('C:\cygwin\Home\Admin\DB')
        except:
            pass   # Ignore
        self.con=sqlite3.connect('robot.dbs')
        self.con.execute("PRAGMA foreign_keys=ON")
        self.dbchanged=False   # True to flag when local database has been modified and updates need to be pushed
        self.remoteconn=None   # Open when needed

    def execute(self,argv):
        logging.info("Running: %s"," ".join(argv))
        retval=-1   # For error

        if len(argv)<2:
                logging.error('Usage: db.py cmd [args]')
        elif argv[1]=='getflag':
            if len(argv)!=3:
                logging.error('Usage: db.py getflag <flagname>')
            else:
                try:
                    self.pullfromserver()   # In case there are any updates
                except:
                    logging.error('Error during automatic pull ignored')
                retval=self.getflag(argv[2])
        elif argv[1]=='setflag':
            if len(argv)!=4:
                logging.error('Usage: db.py setflag <flagname> <value>')
            else:
                retval=self.setflag(argv[2],argv[3])
        elif argv[1]=='getvol':
            if len(argv)!=4:
                logging.error('Usage: db.py getvol <plate> <well>')
            else:
                retval=self.getvol(argv[2],argv[3])
        elif argv[1]=='setvol':  
            if len(argv)!=7:
                logging.error('Usage: db.py setvol <sampname> <plate> <well> <gemvol> <expectvol>')
            else:
                retval=self.setvol(argv[2],argv[3],argv[4],argv[5],argv[6])
        elif argv[1]=='startrun':   # Usage startrun name gentime checksum gitlabel
            if len(argv)!=6:
                logging.error('Usage: db.py startrun <name> <gentime> <checksum> <gitlabel>')
            else:
                retval= self.startrun(argv[2],argv[3],argv[4],argv[5])
        elif argv[1]=='endrun':
            if len(argv)!=3:
                logging.error('Usage: db.py endrun <name>')
            else:
                retval=self.endrun(argv[2])
        elif argv[1]=='tick':
            if len(argv)!=4:
                logging.error('Usage db.py tick <elapsed> <remaining>')
            else:
                retval=self.tick(argv[2],argv[3])
        elif argv[1]=='push':
            if len(argv)!=2:
                logging.error('Usage db.py push')
            else:
                retval=self.pushtoserver()
        elif argv[1]=='pull':
            if len(argv)!=2:
                logging.error('Usage db.py pull')
            else:
                retval=self.pullfromserver()
        else:
            logging.error( "Bad command: %s"," ".join(argv))
        if retval>=0 and self.dbchanged:
            # Push if possible
            try:
                self.pushtoserver()
            except:
                logging.error('Error during automatic push ignored')
        if self.remoteconn is not None:
            self.remoteconn.close()
            self.remoteconn=None
        return retval
    
    def startrun(self,program,gentime,checksum,gitlabel):
        run=uuid.uuid4()
        logging.debug(str(("run=",run,",gentime=",gentime,",checksum=",checksum,",gitlabel=",gitlabel)))
        self.con.execute("update runs set endtime=datetime('now') where endtime is null")
        # Store values in DB in UTC ('now' always gives UTC, need to convert gentime from localtime to UTC)
        self.con.execute("insert into runs(run,program,starttime,gentime,checksum,gitlabel) values (?,?,datetime('now'),datetime(?,'utc'),?,?)",(run.hex,program,gentime,checksum,gitlabel))
        self.con.commit()
        return 0
        
    def tick(self,elapsed,remaining):
        try:
            elapsed=float(elapsed)
            remaining=float(remaining)
        except:
            logging.error('tick: elapsed,remaiing must be floats')
            return -1
        
        run=self.getrun()
        if run is None:
            return -1
        cursor=self.con.cursor()
        cursor.execute("insert into ticks(run,elapsed,remaining,time)  select run,?,?,datetime('now') from runs where endtime is null",(elapsed,remaining))
        if cursor.rowcount!=1:
            logging.error('tick: Failed insert of (%f,%f) into ticks: rowcount=%d',elapsed,remaining,cursor.rowcount)
        else:
            logging.info("inserted %d rows", cursor.rowcount)
        self.con.commit()
        self.dbchanged=True
        return 0
        
    def endrun(self,program):
        cursor=self.con.cursor()
        cursor.execute("update runs set endtime=datetime('now') where endtime is null")
        if cursor.rowcount==0:
            logging.info('endrun: No run to end')
        elif cursor.rowcount>1:
            logging.error("endrun: Had %d runs which had not ended",cursor.rowcount)
            
        self.con.commit()
        self.dbchanged=True
        return 0
        
    def getflag(self,name):
        cursor=self.con.cursor()
        cursor.execute("select value,lastupdate from  flags where name=? order by lastupdate desc limit 1",(name,))
        res=cursor.fetchone()
        if res is None:
            logging.error("getflag:  Flag %s not found in DB",name)
            self.setflag(name,0)
            return 0
        val=res[0]
        lastupdate=res[1]
        logging.info("value=%s, lastupdate=%s",val,lastupdate)
        try:
            return int(val)
        except:
            logging.warning("getflag: Value for flag %s is '%s', not an integer, exitting with code 1",name,val)
            return 1

    def setflag(self,name,value):
        try:
            value=int(value)
        except:
            logging.error('setflag: Only integers allowed, not "%s"',value)
            return -1
        
        run=self.getrun()
        if run is None:
            return -1
        cursor=self.con.cursor()
        cursor.execute("insert or replace into flags(run,name,value,lastupdate) values(?,?,?,datetime('now'))",(run,name,value))
        if cursor.rowcount!=1:
            logging.error("setflag: Failed insert of (%s,%s,%s) into flags: rowcount=%d",run,name,value,cursor.rowcount)
        else:
            logging.info("Inserted %d rows",cursor.rowcount)
        self.con.commit()
        self.dbchanged=True
        return 0

    def getrun(self):
        """Get Current run"""
        cursor=self.con.cursor()
        cursor.execute("select run from runs where endtime is null")
        res=cursor.fetchall()
        if len(res)!=1:
            logging.error('getrun: Unable to retrieve current run, have %d entries with null endtime',len(res))
            return None
        run=res[0][0]
        logging.info('run=%s',run)
        return run
    
    def getvol(self,plate,well):
        cursor=self.con.cursor()
        cursor.execute("select volume,measured from  vols where plate=? and well=? order by vol desc limit 1",(plate,well))
        res=cursor.fetchone()
        if res is None:
            logging.error("getvol:  plate %s, well %s not found in DB",plate,well)
            return None
        volume=res[0]
        measured=res[1]
        logging.info( "volume=%f, measured=%f",volume,measured)
        return volume

    def setvol(self,sampname,platename,well,gemvolume,expectvol):
        try:
            gemvolume=float(gemvolume)
            expectvol=float(expectvol)
        except:
            logging.error('setvol: gemvolume,expectvol must be floats')
            return -1

        run=self.getrun()  
        if run is None:
            return -1
        cursor=self.con.cursor()
        if sampname is not None:
            cursor.execute("insert or replace into sampnames(run,plate,well,name) values(?,?,?,?)",(run,platename,well,sampname))
            if cursor.rowcount!=1:
                logging.error("setvol: Failed insert of (%s,%s,%s,%s) into sampname: rowcount=%d",run,platename,well,sampname,cursor.rowcount)

        gemvolume=float(gemvolume)
        if platename=='Reagents':
            plate=decklayout.REAGENTPLATE
        elif platename=='Samples':
            plate=decklayout.SAMPLEPLATE
        elif platename=='Dilutions':
            plate=decklayout.DILPLATE
        elif platename=='Water':
            plate=decklayout.WATERLOC
        elif platename=='SSDDil':
            plate=decklayout.SSDDILLOC
        else:
            logging.error( "setvol: Unknown plate: %s ",platename)
            plate=None
        
        volume=None
        if plate is not None:
            try:
                height=plate.getgemliquidheight(gemvolume)
                volume=plate.getliquidvolume(height)
                logging.info("gemvolume=%.1f, volume=%.1f",gemvolume,volume)
            except:
                logging.error( "setvol: Unable to convert gemvolume of %f to actual volume ",gemvolume)

        cursor.execute("insert or replace into vols(run,plate,well,gemvolume,volume,expected,measured) values(?,?,?,?,?,?,datetime('now'))",(run,platename,well,gemvolume,volume,expectvol))
        if cursor.rowcount!=1:
            logging.error("setvol: Failed insert of (%s,%s,%s,%.1f,%s) into vols: rowcount=%d",platename,well,gemvolume,volume,expectvol,cursor.rowcount)
        self.con.commit()
        self.dbchanged=True
        return 0

    def openremote(self):
        if self.remoteconn is None:
            self.remoteconn = pymysql.connect(host='35.203.151.202',user='robot',password='cdsrobot',db='robot',cursorclass=pymysql.cursors.DictCursor)

    def pullfromserver(self):
        """Pull any flag updates from server"""
        self.openremote()
        with self.remoteconn.cursor() as cremote:
            cremote.execute('select * from flags where pulltime is null')
            flags=cremote.fetchall()
            logging.info("Pulling %d flags",len(flags))
            if len(flags)>0:
                clocal = self.con.cursor()
                for flag in flags:
                    logging.debug('pulling flag %d',flag['flag'])
                    clocal.execute("insert into flags(run,name,value,lastupdate,synctime) values(?,?,?,?,datetime('now'))",
                                   (flag['run'],flag['name'],flag['value'],flag['lastupdate']))
                    if clocal.rowcount != 1:
                        logging.error("pullfromserver: Failed insert of (%s,%s,%s,%s) into flags: rowcount=%d",
                                      flag['run'],flag['name'],flag['value'],flag['lastupdate'],clocal.rowcount)
                        return -1
                    else:
                        logging.info("Inserted %d rows", clocal.rowcount)
                    cremote.execute("update flags set pulltime=now() where flag=%s",flag['flag'])
                self.remoteconn.commit()
                self.con.commit()
        return 0

    def pushtoserver(self):
        """Push all completed runs to server"""
        clocal=self.con.cursor()
        clocal.execute("select run,program,starttime,gentime,checksum,gitlabel,endtime from runs where synctime is null")
        runs=clocal.fetchall()
        clocal.execute("select run,endtime from runs where synctime is not null and endtime is not null and endtime>synctime ")
        runends=clocal.fetchall()
        clocal.execute("select sampname,run,plate,well,name  from sampnames where synctime is null")
        sampnames=clocal.fetchall()
        clocal.execute("select vol,run,plate,well,gemvolume,volume,expected,measured from vols where synctime is null")
        vols=clocal.fetchall()
        clocal.execute("select flag,run,name,value,lastupdate from flags where synctime is null")
        flags=clocal.fetchall()
        clocal.execute("select tick,run,elapsed,remaining,time from ticks where synctime is null")
        ticks=clocal.fetchall()

        logging.info( "Pushing: %d runs,  %d endruns, %d sampnames, %d vols, %d flags, %d ticks",len(runs),len(runends),len(sampnames),len(vols),len(flags),len(ticks))
        if len(runs)+len(runends)+len(sampnames)+len(vols)+len(flags)+len(ticks) > 0:
            # Connect to the database if needed
            self.openremote()
            try:
                # run primary key is persistent across both local and remote
                sql1 = "INSERT INTO runs (run,program,starttime,gentime,checksum,gitlabel,endtime) VALUES(%s,%s,CONVERT_TZ(%s,'UTC','SYSTEM'),CONVERT_TZ(%s,'UTC','SYSTEM'),%s,%s,CONVERT_TZ(%s,'UTC','SYSTEM'))"
                sql1u = "UPDATE runs SET endtime=CONVERT_TZ(%s,'UTC','SYSTEM') WHERE run=%s"
                # Local and remote maintain their own primary keys for sampnames,vols, ticks, flags
                sql2 = "INSERT INTO sampnames (run,plate,well,name) VALUES(%s,%s,%s,%s)"
                sql3 = "INSERT INTO vols (run,plate,well,gemvolume,volume,expected,measured) VALUES(%s,%s,%s,%s,%s,%s,CONVERT_TZ(%s,'UTC','SYSTEM'))"
                sql4 = "INSERT INTO ticks (run,elapsed,remaining,time) VALUES(%s,%s,%s,%s)"
                sql5 = "INSERT INTO flags (run,name,value,lastupdate,pulltime) VALUES(%s,%s,%s,CONVERT_TZ(%s,'UTC','SYSTEM'),now())"
                with self.remoteconn.cursor() as cremote:
                    for run in runs:
                        logging.debug("pushing run %s",run[0])
                        if cremote.execute(sql1,run) != 1:
                            logging.error("Failed %s for run %s",sql1,run[0])
                            return -1
                        clocal.execute("update runs set synctime=datetime('now') where run=?",(run[0],))
                    for runend in runends:
                        logging.debug("pushing run endtime %s",runend[0])
                        if cremote.execute(sql1u,(runend[1],runend[0])) != -1:
                            logging.error("Failed %s",sql1u%(runend[1],runend[0]))
                            return -1
                        clocal.execute("update runs set synctime=datetime('now') where run=?",(runend[0],))
                    for sampname in sampnames:
                        logging.debug("pushing sampname %d (run %s)",sampname[0],sampname[1])
                        cremote.execute(sql2,sampname[1:])
                        clocal.execute("update sampnames set synctime=datetime('now') where sampname=?",(sampname[0],))
                    for vol in vols:
                        logging.debug("pushing vol %d (run %s)",vol[0],vol[1])
                        cremote.execute(sql3,vol[1:])
                        clocal.execute("update vols set synctime=datetime('now') where vol=?",(vol[0],))
                    for tick in ticks:
                        logging.debug("pushing tick %d (run %s)",tick[0],tick[1])
                        cremote.execute(sql4,tick[1:])
                        clocal.execute("update ticks set synctime=datetime('now') where tick=?",(tick[0],))
                    for flag in flags:
                        logging.debug("pushing flag %d (run %s)",flag[0],flag[1])
                        cremote.execute(sql5,flag[1:])
                        clocal.execute("update flags set synctime=datetime('now') where flag=?",(flag[0],))
                self.remoteconn.commit()
                self.con.commit()
            finally:
                pass
        return 0

#Execute the application
if __name__ == "__main__":
    exitCode=-1
    try:
        db=TecanDB()
        exitCode=db.execute(sys.argv)
        logging.info('Exit code %d',exitCode)
    except:
        (typ,val,tb)=sys.exc_info()
        logging.error("Exception: %s",str(typ))
        import traceback
        logging.error(traceback.format_exc(tb))
        time.sleep(5)
    sys.exit(int(exitCode))
    
