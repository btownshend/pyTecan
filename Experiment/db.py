import sys
from . import worklist
import pymysql.cursors
from . import clock
from . import logging
from .config import Config

class DB(object):
    def __init__(self):
        self.db = None
        self.id = None
        self.sampids={}
        self.ops=[]
        self.liquidclasses={}

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


        if self.db is None:
            self.id=None
        else:
            with self.db.cursor() as cursor:
                cursor.execute('insert into programs(program) value(null)')   # will fill in other fields later
                self.id=cursor.lastrowid


    def startrun(self, name: str, gentime: str, checksum: str, gitlabel: str):
        if self.db is None:
            self.connect()
        if self.id is None:
            return
        worklist.pyrun("DB\db.py startrun %s %s %s %s %s"%(name,gentime.replace(' ','T'),checksum,gitlabel,self.id))
        with self.db.cursor() as cursor:
            cursor.execute('update programs set name=%s, gentime=%s, checksum=%s,gitlabel=%s where program=%s',(name.replace(' ','_'), gentime, checksum, gitlabel,self.id))

    def tick(self, elapsed: float,remaining: float):
        if self.id is None:
            return
        worklist.pyrun("DB\db.py tick %f %f %d"%(elapsed,remaining,worklist.getline()))

    def endrun(self):
        if self.id is None:
            return
        worklist.pyrun("DB\db.py endrun %d"%self.id)
        if len(self.ops)>0:
            print("ops=",self.ops[:20],'...')
            print("Insert %d ops..."%len(self.ops),end='',flush=True)
            with self.db.cursor() as cursor:
                cursor.executemany('insert into ops(sample, cmd, elapsed, tip, volume,volchange,lineno, lc,program) values(%s,%s,%s,%s,%s,%s,%s,%s,%s)',self.ops)
            print("done")
            self.ops=[]
        self.db.commit()
        #self.db.close()

    def getlc(self,lc):
        # Convert a liquidclass name to a pk
        if lc is None:
            return None
        if len(self.liquidclasses)==0:
            with self.db.cursor() as cursor:
                cursor.execute('select lc, name from liquidclasses')
                rows = cursor.fetchall()
                for row in rows:
                    self.liquidclasses[row['name']] = row['lc']

        if lc.name not in self.liquidclasses:
            print('Adding liquid class %s to database',lc.name)
            with self.db.cursor() as cursor:
                cursor.execute('insert ignore into liquidclasses(name) values(%s)', lc.name)
                cursor.execute('select lc from liquidclasses where name=%s',lc.name)
                res =cursor.fetchone()
                self.liquidclasses[lc.name]=res['lc']
                return res['lc']
        return self.liquidclasses[lc.name]

    def newsample(self, sample):
        # Add sample to database
        if self.id is None:
            return
        with self.db.cursor() as cursor:
            # Check if it already exists
            cursor.execute("SELECT sample,name FROM samples WHERE program=%s AND plate=%s and well=%s",(self.id,sample.plate.name,sample.plate.wellname(sample.well)))
            res=cursor.fetchone()
            if res is not None:
                logging.warning("newsample: Attempt to add sample %s in well %s.%s, but already have %s there"%(sample.name,sample.plate.name,sample.plate.wellname(sample.well),res['name']))
                self.sampids[sample]=res['sample']  # Treat it as an alias
            else:
                cursor.execute("INSERT INTO samples(program,name,plate,well,initialvolume) VALUES(%s,%s,%s,%s,%s)",(self.id,sample.name.replace(' ','_'),sample.plate.name,sample.plate.wellname(sample.well),sample.initVol))
                self.sampids[sample]=cursor.lastrowid

    def clearSamples(self):
        self.ops=[]
        if self.id is None:
            return
        with self.db.cursor() as cursor:
            # Delete any sample names entered
            cursor.execute("DELETE FROM samples WHERE program=%s",(self.id,))

    def setvol(self, sample, lineno: int, tip: int):
        if self.id is None:
            return
        worklist.pyrun("DB\db.py setvol %s %s ~DETECTED_VOLUME_%d~ %d %d %.2f"%(sample.plate.name,sample.plate.wellname(sample.well),tip,tip,lineno,sample.volume),flush=False)
        # TODO: May be able to extract this from log file instead of calling python all the time

    def volchange(self, sample, cmd:str, volume:float, tip: int, liquidClass):
        if self.id is None:
            return
        if sample not in self.sampids:
            logging.warning("Unable to find sample %s in sampids"%sample.name)
            sampid = None
            sampvol = None
        else:
            sampid=self.sampids[sample]
            sampvol=sample.volume

        worklist.comment("@op('%s','%s',%d,'%s',%.2f,%d,%.2f,%.2f,'%s',%d,%d)"%(sample.plate.name,sample.name,sampid,cmd,clock.elapsed(),tip,sampvol,volume,liquidClass,self.getlc(liquidClass),self.id))
        self.ops.append([sampid, cmd, clock.elapsed(), tip, sampvol, volume, worklist.getline(), self.getlc(liquidClass),self.id])

    def wlistOp(self, cmd:str, tipMask:int, liquidClass, volume, plate, wellNums):
        if cmd== 'Mix':
            return
        tip = 1
        tipTmp = tipMask
        for i in range(len(wellNums)):
            while tipTmp & 1 == 0:
                assert tipTmp!=0
                tipTmp = tipTmp >> 1
                tip = tip + 1
            if samp is None:
                logging.warning("Unable to find sample %s.%s"%(plate.name,wellNames[i]))
            else:
                from .sample import Sample
                samp=Sample.lookupByWell(plate, wellNums[i])
                if samp is None:
                    logging.warning("Unable to find sample %s.%s" % (plate.name, wellNums[i]))
                self.volchange(samp, cmd, volume[i], lineno, tip, liquidClass)
                if cmd== 'Detect_Liquid':
                    # Also put a command in .gem to push measured volume
                    self.setvol(samp,tip)
            tipTmp = tipTmp >> 1
            tip += 1

db=DB()