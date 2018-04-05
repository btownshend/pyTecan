#from .sample import Sample
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
            logging.warning("Not connecting to mysql database -- no logging of run will occur")


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
        worklist.pyrun("DB\db.py startrun %s %s %s %s %s"%(name.replace(' ','_'),gentime.replace(' ','T'),checksum,gitlabel,self.id))
        with self.db.cursor() as cursor:
            cursor.execute('update programs set gentime=%s, checksum=%s,gitlabel=%s where program=%s',(gentime, checksum, gitlabel,self.id))

    def tick(self, elapsed: float,remaining: float):
        if self.id is None:
            return
        worklist.pyrun("DB\db.py tick %f %f"%(elapsed,remaining))

    def endrun(self, name: str):
        if self.id is None:
            return
        worklist.pyrun("DB\db.py endrun %s"%(name.replace(' ','_'),))
        if len(self.ops)>0:
            print("Insert %d ops..."%len(self.ops),end='')
            with self.db.cursor() as cursor:
                cursor.executemany('insert into pgm_ops(pgm_sample, elapsed, tip, volume,volchange) values(%s,%s,%s,%s,%s)',self.ops)
            print("done")
            self.ops=[]
        self.db.commit()
        #self.db.close()

    def newsample(self, sample):
        # Add sample to database
        if self.id is None:
            return
        with self.db.cursor() as cursor:
            # Check if it already exists
            cursor.execute("SELECT pgm_sample,name FROM pgm_samples WHERE program=%s AND plate=%s and well=%s",(self.id,sample.plate.name,sample.plate.wellname(sample.well)))
            res=cursor.fetchone()
            if res is not None:
                logging.warning("newsample: Attempt to add sample %s in well %s.%s, but already have %s there"%(sample.name,sample.plate.name,sample.plate.wellname(sample.well),res['name']))
                self.sampids[sample]=res['pgm_sample']  # Treat it as an alias
            else:
                cursor.execute("INSERT INTO pgm_samples(program,name,plate,well,initialvolume) VALUES(%s,%s,%s,%s,%s)",(self.id,sample.name.replace(' ','_'),sample.plate.name,sample.plate.wellname(sample.well),sample.initVol))
                self.sampids[sample]=cursor.lastrowid

    def clearSamples(self):
        self.ops=[]
        if self.id is None:
            return
        with self.db.cursor() as cursor:
            # Delete any sample names entered
            cursor.execute("DELETE FROM pgm_samples WHERE program=%s",(self.id,))

    def setvol(self, sample,volvar: str):
        if self.id is None:
            return
        worklist.pyrun("DB\db.py setvol %s %s %s ~%s~ %.2f"%(sample.name.replace(' ','_'),sample.plate.name,sample.plate.wellname(sample.well),volvar,sample.volume))

    def volchange(self, sample, volume:float, tip: int):
        if self.id is None:
            return
        sampid=self.sampids[sample]
        self.ops.append([sampid,clock.elapsed(),tip, sample.volume,volume])



db=DB()