# Setup TRP programs on PTC
import ptc

p=ptc.PTC()   # 10s timeout
p.setdebug()
p.execute('FOLDER "TRP"')
p.program('TRP','TRPOMNI',['TEMP 37,3000'])
p.program('TRP','TRPANN',['TEMP 95,60','TEMP 25,1','RATE 0.5'])
p.program('TRP','TRPLIG',['TEMP 16,1800','TEMP 65,600','TEMP 25,30'])
p.program('TRP','LIG15RT',['TEMP 25,900','TEMP 65,600','TEMP 25,30'])
p.program('TRP','COOLDOWN',['TEMP 16,60'])
p.program('TRP','DRY',['TEMP 95,300','TEMP 25,1'])
p.program('TRP','BOIL',['TEMP 105,600','TEMP 25,6000'])
pgms=p.programs("TRP")
print "pgms=",pgms
