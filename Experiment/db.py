import sys

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
        self.sampids={}
        self.ops=[]
        self.liquidclasses={}
        self.programComplete=False  # True if db contains all ops needed for program

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

    def setProgramComplete(self):
        if self.program is None:
            return
        with self.db.cursor() as cursor:
            cursor.execute('update programs set complete=True where program=%s',(self.program,))
            logging.notice('Marked program %d as complete'%self.program)

    def getOp(self, lineno, tip):
        with self.db.cursor() as cursor:
            cursor.execute("select op from ops where program=%s and lineno=%s and tip=%s",
                           (self.program, lineno, tip))
            res = cursor.fetchone()
            return None if res is None else res['op']

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

    def insertVol(self, run, op, gemvolume, volume, measured, height, submerge, zmax, zadd):
        with self.db.cursor() as cursor:
            cursor.execute("insert into vols(run,op,gemvolume,volume,measured, height, submerge, zmax, zadd) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)", (run, op, gemvolume, volume, measured, height, submerge, zmax, zadd))
            logging.notice("Inserted vol as %d" % cursor.lastrowid)
            return cursor.lastrowid


class BuildDB(DB):
    """Log actions during compile of program to .gem """
    def embed(self,cmd,params=None,lineno=None):
        """Embed a machine-readable comment in the .gem file"""
        if lineno is None:
            lineno=worklist.getline()
        if self.program is None:
            program=-1
        else:
            program=self.program

        cmt="@%s(%d,%d,%.1f"%(cmd,program,lineno,clock.elapsed())
        if params is None:
            cmt="%s)"%cmt
        else:
            cmt="%s,%s)"%(cmt,params)
        worklist.comment(cmt)

    def startrun(self, name: str, gentime: str, checksum: str, gitlabel: str):
        if self.db is None:
            self.connect()
        if self.db is not None and self.program is None:
            self.program=self.insertProgram(name,gentime,checksum,gitlabel,clock.totalTime,False)
        #worklist.pyrun("DB\db.py startrun %s %s %s %s %s"%(name,gentime.replace(' ','T'),checksum,gitlabel,self.id))
        self.embed("log_startrun","lasttime,'%s','%s','%s','%s',%.0f"%(name,gentime.replace(' ','T'),checksum,gitlabel,clock.totalTime if clock.totalTime is not None else -1))


    def tick(self, remaining: float):
        #worklist.pyrun("DB\db.py tick %f %f %d"%(elapsed,remaining,worklist.getline()))
        self.embed("log_tick","%d"%remaining)

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
                cursor.executemany('insert into ops(sample, cmd, elapsed, tip,volchange,lineno, lc,program) values(%s,%s,%s,%s,%s,%s,%s,%s)',self.ops)
            print("done")
            self.ops=[]
        self.db.commit()
        self.setProgramComplete()
        #self.db.close()


    def newsample(self, sample):
        # Add sample to database
        print("newsample",sample,",program=",self.program)
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

    def addop(self, sample, cmd:str, volume:float, lineno: int, tip: int, liquidClass):
        sampid = self.getSample(sample.plate.name,sample.plate.wellname(sample.well))
        if sampid is None:
            logging.warning("Unable to find sample %s"%sample.name)
            sampid = -1
        self.embed("log_op","'%s','%s','%s',%d,'%s',%d,%.2f,'%s',%d"%(sample.plate.name,sample.name,sample.plate.wellname(sample.well),sampid,cmd,tip,volume,liquidClass,self.getlc(liquidClass.name)),lineno=lineno)
        if self.program is not None:
            self.ops.append([sampid, cmd, clock.elapsed(), tip, volume, lineno, self.getlc(liquidClass.name), self.program])

    def wlistOp(self, cmd:str, lineno:int, tipMask:int, liquidClass, volume, plate, wellNums):
        if cmd== 'Mix':
            return
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

    def wlistWash(self, cmd:str, tipMask:int):
        pass


class LogDB(DB):
    """Log actions when accessed from log-file parsing"""
    def __init__(self,logfile):
        super().__init__()
        self.run=None
        self.measurements={}
        self.tz = pytz.timezone('US/Pacific')
        self.logfile = logfile

    def local2utc(self,dt):
        return self.tz.localize(dt).astimezone(pytz.utc)

    def log_startrun(self, program, lineno, elapsed, startTime, name, genTime, checksum, gitlabel, totalTime):
        if self.db is None:
            self.connect()
        print(
            "startrun: program=%d,lineno=%d,elapsed=%f,name=%s,gentime=%s,checksum=%s,gitlabel=%s,totalTime=%f" % (
                program, lineno, elapsed, name, genTime, checksum, gitlabel, totalTime))
        startTime=self.local2utc(startTime)  ## Naive datetimes read from log file
        # Note: gentime is already UTC
        if not Config.usedb:
            return
        if program > 0:
            self.program = program
        else:
            # Check if we already have a matching program (name,gentime)
            self.program = self.getProgram(name, genTime)
            if self.program is None:
                # Create a program for this run
                self.insertProgram(name, genTime, checksum, gitlabel, totalTime, False)

        # Create a run
        with self.db.cursor() as cursor:
            cursor.execute("insert into runs(starttime,program,logfile) values (%s,%s,%s)",(startTime, self.program, self.logfile))
            self.run=cursor.lastrowid
            logging.notice("Inserted run %d"%self.run)
            self.db.commit()

    def log_endrun(self,program,lineno,elapsed, endTime):
        if self.db is None:
            return
        endTime=self.local2utc(endTime)
        self.setProgramComplete()
        self.setRunEndTime(endTime)
        self.db.commit()

    def setRunEndTime(self,endTime):
        with self.db.cursor() as cursor:
            cursor.execute('update runs set endtime=%s where run=%s',(endTime, self.run))
            logging.notice('Added endtime to run %d'%self.run)

    def lastmeasure(self,tip,lineno,height,sbl,sml,zadd,lasttime):
        lasttime=self.local2utc(lasttime)
        logging.notice("lastmeasure(%d,%d,%d,%d,%d,%d,%s)"%(tip,lineno,height,sbl,sml,zadd,str(lasttime)))
        self.measurements[(lineno,tip)]=[height,sbl,sml,zadd,lasttime]

    def log_op(self, program, lineno, elapsed, plateName, sampleName, wellName, sampid, cmd, tip, volchange,liquidClassName, lc):
        logging.notice("op(%s,%d,%.2f,%s,%s,%s,%d,%s,%d,%.2f,%s,%d)"%(program, lineno, elapsed, plateName, sampleName, wellName, sampid, cmd, tip, volchange,
              liquidClassName, lc))
        if self.db is None:
            return
        # Locate op in current program
        assert program == -1 or self.program == program  # Make sure we're still referring to correct program
        op = self.getOp(lineno, tip)
        if op is None:
            if self.programComplete:
                logging.error('Database indicates program %d is complete, but op for line %d, tip %d is missing'%(self.program,lineno,tip))
            logging.notice("Op not found, inserting")
            if lc == -1:
                lc = self.getlc(liquidClassName)
            if sampid==-1:
                sampid=self.getSample(plateName,wellName)
                if sampid is None:
                    sampid=self.insertSample(plateName, wellName, sampleName)  # FIXME: This won't take initial volume into account
            op = self.insertOp(lineno, elapsed, sampid, cmd, tip, volchange, lc)
        logging.notice("lc=%d, sampid=%d, op=%d"%(lc,sampid,op))
        logging.notice("measurements="+str(self.measurements))
        if (lineno,tip) in self.measurements:
            # Add volume measurement
            measurement=self.measurements[(lineno, tip)]
            logging.notice("measurement: %s"%str(measurement))
            plate=Plate.lookupByName(plateName)
            logging.notice("plate=%s"%str(plate))
            height,submerge,zmax,zadd,meastime=measurement
            curzmax=2100-plate.location.zmax-390+decklayout.TIPOFFSETS[tip-1]
            if zmax!=curzmax:
                logging.warning("ZMax for plate %s, tip %d at time of run was %.0f, currently at %.0f"%(plate.name, tip, zmax, curzmax))
            if height==-1:
                height=None
                gemvolume=None
                volume=None
            else:
                gemvolume=plate.plateType.getgemliquidvolume((height+submerge-zmax)/10.0)
                volume=plate.plateType.getliquidvolume((height+submerge-zmax)/10.0)
            logging.notice("meastime=%s,gemvolume=%s,volume=%s"%(str(meastime),gemvolume,volume))
            self.insertVol(self.run, op, gemvolume, volume, meastime, height, submerge, zmax, zadd)
        self.db.commit()




db=BuildDB()   # For use during compile
