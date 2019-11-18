# Module to interface to RIC
import serial
import sys
import time
import os
from liquidlevel import LiquidLevel

epath = os.path.join(os.path.dirname(__file__), '..')
sys.path.append(epath)

from Experiment.config import Config
from Experiment import worklist   # Need to import this first to avoid circular imports
from Experiment.db import DB

debug=True
x=LiquidLevel()
x.open()

while True:
    val=x.getlevel()
    if debug:
        print("got:%d"%val)

    db=DB()
    Config.password="cdsrobot"
    db.connect()

    with db.db.cursor() as cursor:
        cursor.execute("select run,endtime from runs order by run desc limit 1")
        res=cursor.fetchone()
        print(res)
        if res['endtime'] is None:
            cursor.execute("insert into robot.flags(run,name,value,lastupdate) select %d,'%s','%d',NOW() from dual"%(res['run'],'syslevel',val))
            db.db.commit()
        else:
            print("No active run, so not logging system liquid level")
    time.sleep(300)
