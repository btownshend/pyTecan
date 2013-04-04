import ptc
import sys

p=ptc.PTC()
print "Status=",p.getstatus()
res=p.execute(" ".join(sys.argv[1:]))
print "Result=",res

