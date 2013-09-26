import ptc
import time

p=ptc.PTC()
print "PTC Version=",p.version()
print "Status=",p.getstatus()
print "Lid status=",p.getlidstatus()
time.sleep(5)
