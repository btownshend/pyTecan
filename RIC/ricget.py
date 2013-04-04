import ric
import time

r=ric.RIC()
r.open()
print "Status = ",r.status()
ptemp=r.gettemp()
print "Plate now at %.1f"%ptemp
time.sleep(5)
exit(int(ptemp+0.5))


