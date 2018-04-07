from . import worklist
from . import logging

#cycler="PTC200"
cycler="TROBOT"
hotlidtemp=100

if cycler=='PTC200':
    tc_prefix="PTC\\ptc"
elif cycler=='TROBOT':
    tc_prefix="TRobot\\trobot"
else:
    logging.error("Bad cycler type: %s"%cycler)

def lid(doopen):
    if doopen:
        worklist.pyrun(tc_prefix+"lid.py OPEN",version=2)
    else:
        worklist.pyrun(tc_prefix+"lid.py CLOSE",version=2)

def test():
    worklist.pyrun(tc_prefix+"test.py",version=2)

def run(pgm,volume):
    global hotlidtemp
    if cycler=='PTC200':
        hotlidmode='CONSTANT'
        assert(hotlidtemp>30)
        worklist.pyrun(tc_prefix+'run.py %s CALC %s,%d %d'%(pgm,hotlidmode,hotlidtemp,volume),version=2)
    else:
        worklist.pyrun(tc_prefix+'run.py',version=2)

def wait():
    worklist.pyrun(tc_prefix+'wait.py',version=2)

def setpgm(name,lidtemp,steps):
    global hotlidtemp
    logging.notice("setpgm(%s,%d,%s)"%(name,lidtemp,steps))
    if cycler=='PTC200':
        hotlidtemp=lidtemp
        worklist.pyrun(tc_prefix+'setpgm.py %s %s'%(name,steps),version=2)
    else:
        if lidtemp>99:
            logging.warning("Lidtemp of %f above max; reducing to 99"%lidtemp)
            lidtemp=99
        worklist.pyrun(tc_prefix+'setpgm.py %s %.0f %s'%(name,lidtemp,steps),version=2)
