import sys
import os
from . import worklist
import pymysql.cursors
from . import clock
from . import logging
from .config import Config
from .plate import Plate
from . import decklayout
from .liquidclass import LCPrefilled
import pytz


class DB(object):
    def __init__(self):
        self.db = None
        self.program = None
        self.sampids={}   # Dictionary from (plate,well) to sampid
        self.ops=[]
        self.liquidclasses={}
        self.programComplete=False  # True if db contains all ops needed for program
        self.opdict={}

    def connect(self):
        if Config.usedb:
            if Config.password is None:
                print("Password to database must be supplied on command line using -p option, or use -N option to skip db",file=sys.stderr)
                sys.exit(1)
            try:
                self.db = pymysql.connect(host=Config.host, user=Config.user, password=Config.password, db=Config.db,
                                                     cursorclass=pymysql.cursors.DictCursor)
                print('Connected to remote mysql database:',self.db.get_host_info())
            except Exception as e:
                logging.error("Unable to connect to mysql database -- skipping db entry: ",e)
        else:
            logging.notice("Not connecting to mysql database -- no logging of run will occur")


    def findlog(self,logname):
        # Determine if a run exists for the given logfile and return 0 if not, 1 if incomplete, 2 if complete (has endtime)
        if self.db is None:
            return None
        with self.db.cursor() as cursor:
            cursor.execute("select run,starttime,endtime from runs where logfile=%s",logname)
            res=cursor.fetchone()
            if res is None:
                return 0
            elif res['endtime'] is None:
                return 1
            else:
                return 2

    def getlc(self,lcname):
        # Convert a liquidclass name to a pk
        if lcname is None:
            return None
        if self.program is None:
            return -1
        if len(self.liquidclasses)==0:
            with self.db.cursor() as cursor:
                cursor.execute('select lc, name from liquidclasses')
                rows = cursor.fetchall()
                for row in rows:
                    self.liquidclasses[row['name']] = row['lc']

        if lcname not in self.liquidclasses:
            print('Adding liquid class %s to database',lcname)
            with self.db.cursor() as cursor:
                cursor.execute('insert ignore into liquidclasses(name) values(%s)', lcname)
                cursor.execute('select lc from liquidclasses where name=%s',lcname)
                res =cursor.fetchone()
                self.liquidclasses[lcname]=res['lc']
                logging.notice("Inserted LC %s as %d"%(lcname,res['lc']))
                return res['lc']
        return self.liquidclasses[lcname]


    def clearSamples(self):
        self.ops=[]
        if self.program is None:
            return
        with self.db.cursor() as cursor:
            # Delete any sample names entered
            cursor.execute("DELETE FROM samples WHERE program=%s", (self.program,))
        self.sampids={}
        print("db.clearSamples()")

    def getProgram(self,name,gentime):
        with self.db.cursor() as cursor:
            cursor.execute("select program, complete from programs where name=%s and gentime=%s",(name,gentime))
            res = cursor.fetchone()
            self.programComplete=res['complete']
            return None if res is None else res['program']

    def insertProgram(self,name,gentime,checksum,gitlabel,totalTime,complete):
        with self.db.cursor() as cursor:
            cursor.execute('insert into programs(name,gentime,checksum,gitlabel,totaltime,complete) value(%s,%s,%s,%s,%s,%s)',
                (name, gentime, checksum, gitlabel, totalTime,complete))
            print("Inserted program %s as %d" % (name, cursor.lastrowid))
            return cursor.lastrowid

    def setProgramComplete(self,totalTime=None):
        if self.program is None:
            return
        with self.db.cursor() as cursor:
            if totalTime is None:
                cursor.execute('update programs set complete=True where program=%s',self.program)
                logging.notice('Marked program %s as complete'%self.program)
            else:
                cursor.execute('update programs set complete=True,totaltime=%s where program=%s',(totalTime, self.program,))
                logging.notice('Marked program %s as complete with totalTime=%f'%(self.program,totalTime))

    def getOp(self, lineno, tip, sampid):
        if self.program is None:
            return None
        if len(self.opdict) is 0:
            # Initial read of any samples already in DB
            with self.db.cursor() as cursor:
                # Check if it already exists
                cursor.execute("SELECT op,lineno,tip,sample FROM ops WHERE program=%s",(self.program,))
                rows = cursor.fetchall()
                logging.notice("Loaded %d op records for program %d"%(len(rows),self.program))
                for row in rows:
                    key=(row['lineno'],row['tip'],row['sample'])
                    self.opdict[key]=row['op']
        key=(lineno,tip,sampid)
        if key in self.opdict:
            return self.opdict[key]
        return None

    def insertOp(self, lineno, elapsed, sampid, cmd, tip, volchange, lc):
        with self.db.cursor() as cursor:
            cursor.execute(
                'insert into ops(program,lineno,tip,sample,cmd,lc,volchange,elapsed) values(%s,%s,%s,%s,%s,%s,%s,%s)',
                (self.program, lineno, tip, sampid, cmd, lc, volchange, elapsed))
            return cursor.lastrowid

    def getSample(self, plateName, wellName):
        if self.program is None:
            return None
        if len(self.sampids) is 0:
            # Initial read of any samples already in DB
            with self.db.cursor() as cursor:
                # Check if it already exists
                cursor.execute("SELECT sample,plate,well FROM samples WHERE program=%s",(self.program,))
                rows = cursor.fetchall()
                logging.notice("Loadded %d sample records for program %d"%(len(rows),self.program))
                for row in rows:
                    key=(row['plate'],row['well'])
                    self.sampids[key]=row['sample']
        key=(plateName,wellName)
        if key in self.sampids:
            return self.sampids[key]
        return None

    def insertSample(self, plateName, wellName, sampleName):
        with self.db.cursor() as cursor:
            cursor.execute("insert into samples(program,name,plate,well) VALUES(%s,%s,%s,%s)", (self.program, sampleName, plateName, wellName))
            self.sampids[(plateName,wellName)]=cursor.lastrowid
            logging.notice("Inserted sample %s as %d"%(sampleName,cursor.lastrowid))
            return cursor.lastrowid



class BuildDB(DB):
    def __init__(self):
        super().__init__()
        self.clean={}  # Map from tip # to clean state (T=clean, F=dirty, None=unknown)
        self.status=[] # List of status elements

    """Log actions during compile of program to .gem """
    def embed(self,cmd,params=None,lineno=None):
        """Embed a machine-readable comment in the .gem file"""
        if lineno is None:
            lineno=worklist.getline()
        if self.program is None:
            program=-1
        else:
            program=self.program

        cmt="@%s(%d,%d,%.1f,lasttime"%(cmd,program,lineno,clock.elapsed())
        if params is None:
            cmt="%s)"%cmt
        else:
            cmt="%s,%s)"%(cmt,params.replace("'None'","None"))
        worklist.comment(cmt)

    def startrun(self, name: str, gentime: str, checksum: str, gitlabel: str):
        if self.db is None:
            self.connect()
        if self.db is not None and self.program is None:
            self.program=self.insertProgram(name,gentime,checksum,gitlabel,clock.totalTime,False)
        #worklist.pyrun("DB\db.py startrun %s %s %s %s %s"%(name,gentime.replace(' ','T'),checksum,gitlabel,self.id))
        self.embed("log_startrun","'%s','%s','%s','%s',%.0f"%(name,gentime.replace(' ','T'),checksum,gitlabel,clock.totalTime if clock.totalTime is not None else -1))

    def endrun(self):
        # noinspection PyStringFormat
        #worklist.pyrun("DB\db.py endrun %d"%self.id)
        self.embed("log_endrun","lasttime")
        if self.program is None:
            return

        if len(self.ops)>0:
            print("ops=",self.ops[:20],'...')
            print("Insert %d ops..."%len(self.ops),end='',flush=True)
            with self.db.cursor() as cursor:
                cursor.executemany('insert into ops(sample, cmd, elapsed, tip,volchange,lineno, lc,program,clean) values(%s,%s,%s,%s,%s,%s,%s,%s,%s)',self.ops)
            print("done")
            self.ops=[]
        self.setProgramComplete(totalTime=clock.elapsed())
        self.db.commit()

        #self.db.close()


    def newsample(self, sample):
        # Add sample to database
        #logging.notice("newsample %s, program %s"%(sample,self.program))
        if self.program is None:
            return
        sampid=self.getSample(sample.plate.name,sample.plate.wellname(sample.well))
        if sampid is None:
            sampid=self.insertSample(sample.plate.name, sample.plate.wellname(sample.well),sample.name)
        if sample.initVol>0:
            # Initial op
            self.addop(sample,'Initial',sample.initVol, 0, 0, LCPrefilled )
        else:
            return sampid

    def setStatus(self):
        self.embed("log_status","'%s'"%".".join(self.status))

    def pushStatus(self,msg):
        self.status.append(msg)
        print("pushStatus(%s) -> "%msg,self.status)
        self.setStatus()

    def popStatus(self):
        self.status.pop()
        print("popStatus() -> ",self.status)
        self.setStatus()

    def addop(self, sample, cmd:str, volume:float, lineno: int, tip: int, liquidClass):
        if self.program is None:
            sampid=-1
        else:
            sampid = self.getSample(sample.plate.name,sample.plate.wellname(sample.well))
            if sampid is None:
                logging.warning("Unable to find sample %s"%sample.name)
                sampid = -1
        if tip in self.clean:
            clean=self.clean[tip]
        else:
            clean=None
        self.embed("log_op","'%s','%s','%s',%d,'%s',%d,%.2f,'%s',%d"%(sample.plate.name,sample.name,sample.plate.wellname(sample.well),sampid,cmd,tip,volume,liquidClass,self.getlc(liquidClass.name)),lineno=lineno)
        if self.program is not None:
            self.ops.append([sampid, cmd, clock.elapsed(), tip, volume, lineno, self.getlc(liquidClass.name), self.program, clean])
        self.clean[tip]=False

    def wlistOp(self, cmd:str, lineno:int, tipMask:int, liquidClass, volume, plate, wellNums):
        # if cmd== 'Mix':
        #     return
        tip = 1
        tipTmp = tipMask
        for i in range(len(wellNums)):
            while tipTmp & 1 == 0:
                assert tipTmp!=0
                tipTmp = tipTmp >> 1
                tip = tip + 1
            from .sample import Sample
            samp=Sample.lookupByWell(plate, wellNums[i])
            if samp is None:
                logging.warning("Unable to find sample %s.%s" % (plate.name, wellNums[i]))
            if liquidClass.name.startswith('Mix') and volume[i]<0:
                vol=volume[i]-2.9/4    # Similar to Sample.MIXLOSS assuming 4 cycles  FIXME: This is a kludge and redundant
            elif volume[i]<0:
                vol=-liquidClass.volRemoved(-volume[i])  # FIXME: Should probably lose some volume on dispenses too
            else:
                vol=volume[i]
            self.addop(samp, cmd, vol, lineno, tip, liquidClass)
            tipTmp = tipTmp >> 1
            tip += 1

    # noinspection PyUnusedLocal
    def wlistWash(self, cmd:str, tipMask:int):
        tip=1
        while tipMask>0:
            if tipMask & 1:
                self.clean[tip]=True
            tip+=1
            tipMask>>=1


class LogDB(DB):
    """Log actions when accessed from log-file parsing"""
    def __init__(self,logfile):
        super().__init__()
        self.measurements={}
        self.tz = pytz.timezone('US/Pacific')
        self.logfile = os.path.basename(logfile)
        self.sampvols={}  # Dictionary from sampid to best estimate of current volume
        self.volsqueue=[]   # Queue of vols insertions to be done with executemany
        self.curline=None
        self.db=None
        self.run=None
        self.expt=None

    def logfileStart(self,logheader,starttime):
        # Create a run
        print("logheader=",logheader)
        # Parse header of form: 'Starting program "voltest.gem" (lines 1 to 352)'
        firstline=None
        p1=logheader.find('lines ')
        if p1 is None:
            logging.warning("Unable to parse logheader to fine 'lines ' in '%s'"%logheader)
        else:
            p2=logheader[p1+6:].find(' ')
            if p2 is None:
                logging.warning("Unable to parse logheader to fine ' ' in '%s'" % logheader)
            else:
                firstline=int(logheader[p1+6:p1+6+p2])

        starttime=self.local2utc(starttime)
        self.connect()
        if self.db is None:
            return
        with self.db.cursor() as cursor:
            if self.logfile is not None:
                cursor.execute("select run,starttime,endtime,expt from runs where logfile=%s",self.logfile)
                res=cursor.fetchone()
                if res is not None:
                    if res['endtime'] is not None:
                        logging.error("Already processed logfile %s: have run %d with starttime=%s, endtime=%s"%(self.logfile,res['run'],res['starttime'],res['endtime']))
                    else:
                        logging.warning("Deleting vols for run %d previously processed from logfile %s with starttime=%s and no endtime"%(res['run'],self.logfile,res['starttime']))
                        cursor.execute("delete from vols where run=%s",res['run'])
                        self.run=res['run']
                        self.expt=res['expt']
                        logging.notice("Rebuilding run %d"%self.run)
                        self.db.commit()
                        return

            cursor.execute("insert into runs(starttime,program,logfile,logheader,firstline) values (%s,%s,%s,%s,%s)", (starttime, self.program, self.logfile,logheader,firstline))
            self.run=cursor.lastrowid
            logging.notice("Inserted run %d"%self.run)
            self.db.commit()
        self.expt=None   # Don't have enough information yet to link this to an expt

    def setProgram(self, program):
        """Called if we hit an operation, but haven't seen a log_startrun.
        Probably due to resume an experiment part way through
        Link this run to an expt using heuristics """
        assert self.program is None and program is not None

        self.program = program

        with self.db.cursor() as cursor:
            # Add program to run
            cursor.execute("update runs set program=%s where run=%s",(self.program, self.run))
            if self.expt is None:
                # Link to an experiment
                cursor.execute("select e.expt from runs r, expts e where e.expt=r.expt and r.program=%s and e.complete is false order by r.starttime desc limit 1",(self.program,))
                res=cursor.fetchone()
                if res is not None:
                    self.expt=res['expt']
                    cursor.execute("update runs set expt=%s where run=%s",(self.expt, self.run))
                    return
                logging.warning("Unable to link logfile %s to an existing run with program %d, creating a new expt" % (self.logfile, self.program))
                # Create an experiment for this run
                cursor.execute("insert into expts(complete) values(false)")
                self.expt=cursor.lastrowid
                cursor.execute("update runs set expt=%s where run=%s",(self.expt,self.run))

    def logfileDone(self,lineno, endtime):
        """Completed parse of log file"""
        if self.db is None:
            return
        self.insertQueuedVols()
        endtime=self.local2utc(endtime)
        with self.db.cursor() as cursor:
            cursor.execute("update runs set endtime=%s, lineno=%s where run=%s",(endtime,lineno,self.run))

    def local2utc(self,dt):
        return self.tz.localize(dt).astimezone(pytz.utc)

    def insertQueuedVols(self):
        if len(self.volsqueue)==0:
            return
        print("Insert %d vols..." % len(self.volsqueue), end='', flush=True)
        with self.db.cursor() as cursor:
            cursor.executemany("insert into vols(run,op,gemvolume,volume,measured, height, submerge, zmax, zadd, estvol) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)", self.volsqueue)
            logging.notice("Inserted vol as %d" % cursor.lastrowid)
            self.volsqueue=[]
        print("done")

    def flush(self):
        if self.db is None:
            return
        self.insertQueuedVols()
        self.updatecurline()
        self.db.commit()

    def insertVol(self, run, op, gemvolume, volume, measured, height, submerge, zmax, zadd, estVolume):
        if self.db is None:
            return

        self.volsqueue.append((run, op, gemvolume, volume, measured, height, submerge, zmax, zadd, estVolume))
        if len(self.volsqueue) >= 100:
            self.insertQueuedVols()

    # noinspection PyUnusedLocal
    def log_startrun(self, program, lineno, elapsed, lasttime, name, genTime, checksum, gitlabel, totalTime):
        """Process log_startrun embedded command (which is really a start to an expt, not a run) """
        lasttime=self.local2utc(lasttime)  ## Naive datetimes read from log file

        print(
            "startrun: program=%d,lineno=%d,elapsed=%f,name=%s,gentime=%s,checksum=%s,gitlabel=%s,totalTime=%f" % (
                program, lineno, elapsed, name, genTime, checksum, gitlabel, totalTime))
        # Note: gentime is already UTC
        if not Config.usedb:
            return
        if self.program is None:
            self.setProgram(program)
        assert self.program==program

    # noinspection PyUnusedLocal
    def log_status(self, program, lineno, elapsed, lasttime, status):
        print("Status:",status)
        if self.db is None:
            return
        with self.db.cursor() as cursor:
            cursor.execute("UPDATE runs SET status=%s WHERE run=%s",(status, self.run))

    def updatecurline(self):
        if self.run is None or self.curline is None:
            return
        with self.db.cursor() as cursor:
            cursor.execute("update runs set lineno=%s where run=%s", (self.curline, self.run) )

    # noinspection PyUnusedLocal
    def log_endrun(self,program,lineno,elapsed, lasttime, endTime):
        """Process log_endrun embedded command (which is really the end to an expt, not a run) """
        # FIXME: endTime  and lasttime not both used
        if self.db is None:
            return
        #self.insertQueuedVols()
        self.logfileDone(lineno,endTime)  # Force marking log file done (since it may not be until next run that logfile is actually closed)
        #self.setProgramComplete()   # FIXME: program not fully defined at build time is untested, probably non-working
        with self.db.cursor() as cursor:
            cursor.execute('update expts set complete=True where expt=%s', self.expt)
            logging.notice('Marked expt %s as complete.'%self.expt)
        self.db.commit()

    def setline(self,lineno):
        self.curline=lineno

    def lastmeasure(self,tip,lineno,height,sbl,sml,zadd,lasttime):
        lasttime=self.local2utc(lasttime)
        logging.notice("lastmeasure(%d,%d,%s,%d,%d,%d,%s)"%(tip,lineno,str(height),sbl,sml,zadd,str(lasttime)))
        self.measurements[(lineno,tip)]=[height if height!=0 else None,sbl,sml,zadd,lasttime]

    def log_op(self, program, lineno, elapsed, lasttime, plateName, sampleName, wellName, sampid, cmd, tip, volchange,liquidClassName, lc):
        lasttime=self.local2utc(lasttime)
        logging.notice("op(%s,%d,%.2f,%s,%s,%s,%d,%s,%d,%.2f,%s,%d)"%(program, lineno, elapsed, plateName, sampleName, wellName, sampid, cmd, tip, volchange,
              liquidClassName, lc))
        if self.db is None:
            return
        # Locate op in current program
        if self.program is None:
            self.setProgram(program)

        assert self.program == program  # Make sure we're still referring to correct program
        if sampid == -1:
            sampid = self.getSample(plateName, wellName)
            if sampid is None:
                sampid = self.insertSample(plateName, wellName, sampleName)

        op = self.getOp(lineno, tip, sampid)
        if op is None:
            if self.programComplete:
                logging.error('Database indicates program %d is complete, but op for line %d, tip %d, sample %d is missing'%(self.program,lineno,tip,sampid))
            logging.notice("Op not found, inserting")
            if lc == -1:
                lc = self.getlc(liquidClassName)
            op = self.insertOp(lineno, elapsed, sampid, cmd, tip, volchange, lc)
        if sampid not in self.sampvols:
            self.sampvols[sampid]=0.0
        logging.notice("lc=%d, sampid=%d, op=%d"%(lc,sampid,op))
        logging.notice("measurements="+str(self.measurements))
        if (lineno,tip) in self.measurements:
            # Add volume measurement
            measurement=self.measurements[(lineno, tip)]
            logging.notice("measurement: %s"%str(measurement))
            plate=Plate.lookupByName(plateName)
            assert plate is not None
            logging.notice("plate=%s"%str(plate))
            height,submerge,zmax,zadd,meastime=measurement
            curzmax=2100-plate.getzmax()-390+decklayout.TIPOFFSETS[tip-1]
            if zmax!=curzmax:
                logging.warning("ZMax for plate %s, tip %d at time of run was %.0f, currently at %.0f (using latter)"%(plate.name, tip, zmax, curzmax))
                zmax=curzmax
            if height is None:
                gemvolume=None
                volume=None
            else:
                gemvolume=plate.plateType.getgemliquidvolume((height+submerge-zmax)/10.0)
                volume=plate.plateType.getliquidvolume((height+submerge-zmax)/10.0)
            logging.notice("meastime=%s,gemvolume=%s,volume=%s"%(str(meastime),gemvolume,volume))
            self.insertVol(self.run, op, gemvolume, volume, meastime, height, submerge, zmax, zadd, self.sampvols[sampid])
            # Corrected volume
            if volume is not None:
                self.sampvols[sampid]=volume
        else:
            # Make an entry anyway to keep track of what has actually been done
            self.insertVol(self.run, op, None, None, lasttime, None, None, None, None, self.sampvols[sampid])

        # Update current sample volume based on op
        self.sampvols[sampid]+=volchange
        self.db.commit()




db=BuildDB()   # For use during compile
