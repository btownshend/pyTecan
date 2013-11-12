# Setup TRP programs on PTC
import ptc
import sys

p=ptc.PTC()   # 10s timeout
p.setdebug()
p.execute('FOLDER "TRP"')
p.program('TRP',sys.argv[1],[s.replace('@',' ') for s in sys.argv[2:]])
pgms=p.programs("TRP")
print "pgms=",pgms
