import worklist
import logging


def startrun(name,gentime,checksum,gitlabel):
    worklist.pyrun("DB\db.py startrun %s %s %s %s"%(name.replace(' ','_'),gentime.replace(' ','T'),checksum,gitlabel))

def tick(elapsed,remaining):
    worklist.pyrun("DB\db.py tick %f %f"%(elapsed,remaining))

def endrun(name):
    worklist.pyrun("DB\db.py endrun %s"%(name.replace(' ','_'),))

def setvol(sample,volvar):
    worklist.pyrun("DB\db.py setvol %s %s %s ~%s~ %.2f"%(sample.name.replace(' ','_'),sample.plate.name,sample.plate.wellname(sample.well),volvar,sample.volume))
