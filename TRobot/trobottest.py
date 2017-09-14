import debughook
import trobot
import time
import logging

p=trobot.TRobot()
flist=p.folders()
print "Folders=", flist
runtime=p.program("test",105,["c %04x,%04x"%(95*100,30),"c %04x,%04x"%(60*100,30),"c %04x,%04x"%(72*100,30)])
p.showpgm(0,0)
print "Program runtime=",runtime
print "Programs=",p.programs(0)
print  "TRobot Version=",p.version()
print  "Status=",p.getstatus()
print  "Lid status=",p.getlidstatus()
print "Block temperature=",p.gettemp()
print "Lid temperature=",p.getlidtemp()
