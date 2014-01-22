# Setup TRP programs on PTC
import ptc

p=ptc.PTC()   # 10s timeout
p.setdebug()
p.execute('FOLDER "TRP"')
p.program('TRP','TRPOMNI',['TEMP 37,3000'])
p.program('TRP','TRP37-15',['TEMP 37,900'])
p.program('TRP','TRP37-20',['TEMP 37,1200'])
p.program('TRP','TRP37-30',['TEMP 37,1800'])
p.program('TRP','TRP37-45',['TEMP 37,2700'])
p.program('TRP','TRP37-60',['TEMP 37,3600'])
p.program('TRP','TRPANN',['TEMP 95,60','TEMP 25,1','RATE 0.5'])
p.program('TRP','TRPLIG',['TEMP 16,1800','TEMP 65,600'])
p.program('TRP','TRPLIG15RT',['TEMP 25,900','TEMP 65,600'])
p.program('TRP','COOLDOWN',['TEMP 16,60'])
p.program('TRP','PCR30',['TEMP 95,60','TEMP 95,15','TEMP 55,15','TEMP 72,15','GOTO 2,29','TEMP 72,120','TEMP 16,1'])
p.program('TRP','PCR25',['TEMP 95,120','TEMP 95,30','TEMP 55,30','TEMP 72,25','GOTO 2,24','TEMP 72,180','TEMP 16,1'])
p.program('TRP','PCR20',['TEMP 95,60','TEMP 95,15','TEMP 55,15','TEMP 72,15','GOTO 2,19','TEMP 72,120','TEMP 16,1'])
p.program('TRP','PCR15',['TEMP 95,120','TEMP 95,30','TEMP 55,30','TEMP 72,25','GOTO 2,14','TEMP 72,180','TEMP 16,1'])
pgms=p.programs("TRP")
print "pgms=",pgms
