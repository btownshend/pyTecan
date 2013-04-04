import ric
import sys
import time

if len(sys.argv)!=2:
    print "Usage: %s (temp|IDLE)"%sys.argv[0]
    exit(2)
    
r=ric.RIC()
r.open()
print "Status = ",r.status()
if sys.argv[1]=="IDLE":
    r.idle()
    print "Set RIC to idle"
else:
    settemp=float(sys.argv[1])
    r.settemp(settemp)
    print "Set temp to %.1f"%settemp
ptemp=r.gettemp()
print "Plate now at %.1f"%ptemp
time.sleep(5)
exit(0)

