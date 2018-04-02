#from .sample import Sample
from . import worklist


def startrun(name: str, gentime: str, checksum: str, gitlabel: str):
    worklist.pyrun("DB\db.py startrun %s %s %s %s"%(name.replace(' ','_'),gentime.replace(' ','T'),checksum,gitlabel))

def tick(elapsed: float,remaining: float):
    worklist.pyrun("DB\db.py tick %f %f"%(elapsed,remaining))

def endrun(name: str):
    worklist.pyrun("DB\db.py endrun %s"%(name.replace(' ','_'),))

def setvol(sample,volvar: float):
    worklist.pyrun("DB\db.py setvol %s %s %s ~%s~ %.2f"%(sample.name.replace(' ','_'),sample.plate.name,sample.plate.wellname(sample.well),volvar,sample.volume))
