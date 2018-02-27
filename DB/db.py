import sqlite3
import sys
import os
import uuid
import pymysql.cursors
import time

epath=os.path.join(os.path.dirname(__file__),'..')
print "Adding",epath,"to path"
sys.path.append(epath)
from Experiment.plate import Plate
from Experiment import decklayout

class TecanDB(object):
    def __init__(self):
        os.chdir('C:\cygwin\Home\Admin\DB')
        self.con=sqlite3.connect('test.dbs')
        
    def execute(self,argv):
        print "argv=",argv
        if argv[1]=='getflag':
            return self.getflag(argv[2])
        elif argv[1]=='setflag':
            return self.setflag(argv[2],argv[3])
        elif argv[1]=='getvol':
            return self.getvol(argv[2],argv[3])
        elif argv[1]=='setvol':  # Usage: setvol sampname,platename,well,gemvolume,expectvol
            return self.setvol(argv[2],argv[3],argv[4],argv[5],argv[6])
        elif argv[1]=='startrun':   # Usage startrun name gentime checksum gitlabel
            return self.startrun(argv[2],argv[3],argv[4],argv[5])
        elif argv[1]=='endrun':
            return self.endrun(argv[2])
        elif argv[1]=='tick':
            return self.tick(argv[2],argv[3])
        elif argv[1]=='push':
            return self.pushtoserver()
        else:
            print "Bad command: ",argv[1]
            sys.exit(-1)
            
    def startrun(self,program,gentime,checksum,gitlabel):
        run=uuid.uuid4()
        print "run=",run,",gentime=",gentime,",checksum=",checksum,",gitlabel=",gitlabel
        self.con.execute("update runs set endtime=datetime('now') where endtime is null")
        self.con.execute("insert into runs(run,program,starttime,gentime,checksum,gitlabel) values (?,?,datetime('now'),datetime(?),?,?)",(run.hex,program,gentime,checksum,gitlabel))
        self.con.commit()
        return 0
        
    def tick(self,elapsed,remaining):
        self.con.execute("insert into ticks(run,elapsed,remaining,time)  select run,?,?,datetime('now') from runs where endtime is null",(elapsed,remaining))
        self.con.commit()
        return 0
        
    def endrun(self,program):
        self.con.execute("update runs set endtime=datetime('now') where endtime is null and program=?",(program,))
        self.con.commit()
        try:
            self.pushtoserver()
        finally:
            pass
        return 0
        
    def getflag(self,name):
        cursor=self.con.cursor()
        cursor.execute("select value,lastupdate from  flags where name=?",(name,))
        res=cursor.fetchone()
        if res is None:
            print "getflag:  Flag",name," not found in DB"
            return -1
        val=res[0]
        lastupdate=res[1]
        print "value=",val,"lastupdate=",lastupdate
        return val

    def setflag(self,name,value):
        self.con.execute("insert or replace into flags(run,name,value,lastupdate) select run,?,?,datetime('now') from runs where endtime is null",(name,value))
        self.con.commit()
        return 0

    def getvol(self,plate,well):
        cursor=self.con.cursor()
        cursor.execute("select volume,measured from  vols where plate=? and well=? order by vol desc limit 1",(plate,well))
        res=cursor.fetchone()
        if res is None:
            print "getvol:  ",plate,well," not found in DB"
            return None
        volume=res[0]
        measured=res[1]
        print "volume=",volume,"measured=",measured
        return volume

    def setvol(self,sampname,platename,well,gemvolume,expectvol):
        if sampname is not None:
            self.con.execute("insert or replace into sampnames(run,plate,well,name) select max(run),?,?,? from runs",(platename,well,sampname))

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
            print "Unknown plate: ",platename
            plate=None
        
        volume=None
        if plate is not None:
            try:
                height=plate.getgemliquidheight(gemvolume)
                volume=plate.getliquidvolume(height)
            except:
                print "Error converting gemvolume of ",gemvolume

        print "gemvolume=",gemvolume,"volume=",volume
        self.con.execute("insert or replace into vols(run,plate,well,gemvolume,volume,expected,measured) select max(run),?,?,?,?,?,datetime('now') from runs",(platename,well,gemvolume,volume,expectvol))
        self.con.commit()
        return 0

    def pushtoserver(self):
        """Push all completed runs to server"""
        clocal=self.con.cursor()
        clocal.execute("select run,program,starttime,gentime,checksum,gitlabel,endtime from runs where endtime is  null or synctime is null")
        rows=clocal.fetchall()
        print "have %d runs to sync"%len(rows)
        if len(rows)>0:
            # Connect to the database
            connection = pymysql.connect(host='35.203.151.202',
                                user='robot',
                                password='cdsrobot',
                                db='robot',
                                cursorclass=pymysql.cursors.DictCursor)
            try:
                sql0 = "DELETE IGNORE FROM runs WHERE run=%s"
                sql1 = "INSERT INTO runs (run,program,starttime,gentime,checksum,gitlabel,endtime) VALUES(%s,%s,%s,%s,%s,%s,%s)"
                sql2 = "INSERT INTO sampnames (run,plate,well,name) VALUES(%s,%s,%s,%s)"
                sql3 = "INSERT INTO vols (run,vol,plate,well,gemvolume,volume,expected,measured) VALUES(%s,%s,%s,%s,%s,%s,%s,%s)"
                with connection.cursor() as cremote:
                    for row in rows:
                        print "syncing run ",row
                        cremote.execute(sql0,(row[0],))
                        cremote.execute(sql1,row)
                        clocal.execute("select plate,well,name from sampnames where run=?",(row[0],))
                        names=clocal.fetchall()
                        for name in names:
                            cremote.execute(sql2,(row[0],name[0],name[1],name[2]))
                        clocal.execute("select vol,plate,well,gemvolume,volume,expected,measured from vols where run=?",(row[0],))
                        vols=clocal.fetchall()
                        for vol in vols:
                            print "vol=",vol
                            print "type(vol[0])=",type(vol[0])
                            print sql3,(row[0],vol[0],vol[1],vol[2],vol[3],vol[4],vol[5],vol[6])
                            cremote.execute(sql3,(row[0],vol[0],vol[1],vol[2],vol[3],vol[4],vol[5],vol[6]))
                        if row[6] is not None:
                            # If run is done, mark that sync is completed
                            clocal.execute("UPDATE runs SET synctime=datetime('now') WHERE run=?",(row[0],))
                connection.commit()
                self.con.commit()
            finally:
                connection.close()
            
        return 0

#Execute the application
if __name__ == "__main__":
    exitCode=-1
    try:
        db=TecanDB()
        exitCode=db.execute(sys.argv)
    except:
        print "Error:" ,sys.exc_info()
        time.sleep(5)
    sys.exit(int(exitCode))
    
