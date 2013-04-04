import ptc

p=ptc.PTC()
print "PTC Version=",p.version()
print "Status=",p.getstatus()
print "Lid status=",p.getlidstatus()
