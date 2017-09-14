import worklist

#cycler="PTC200"
cycler="TROBOT"

if cycler=='PTC200':
    tc_prefix="PTC\\ptc"
elif cycler=='TROBOT':
    tc_prefix="TRobot\\trobot"
else:
    print "Bad cycler type: ",cycler
    assert(False)

def lid(open):
    if open:
        worklist.pyrun(tc_prefix+"lid.py OPEN")
    else:
        worklist.pyrun(tc_prefix+"lid.py CLOSE")

def test():
    worklist.pyrun(tc_prefix+"test.py")

def run(pgm,hotlidmode,hotlidtemp,volume):
    if cycler=='PTC200':
        worklist.pyrun(tc_prefix+'run.py %s CALC %s,%d %d'%(pgm,hotlidmode,hotlidtemp,volume))
    else:
        worklist.pyrun(tc_prefix+'run.py')

def wait():
    worklist.pyrun(tc_prefix+'wait.py')

def setpgm(str):
    worklist.pyrun(tc_prefix+'setpgm.py %s'%(str))
