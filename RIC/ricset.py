import ric
import sys
import time

if len(sys.argv)!=2:
    print "Usage: %s (temp|IDLE)"%sys.argv[0]
    exit(2)
    
for i in range(2):
    r=ric.RIC()
    r.open(i)
    print "Status[%d] = %s"%(i,r.status())
    if sys.argv[1]=="IDLE":
        r.idle()
        print "Set RIC[%d] to idle"%i
    else:
        settemp=float(sys.argv[1])
        r.settemp(settemp)
        print "Set temp[%d] to %.1f"%(i,settemp)
    ptemp=r.gettemp()
    print "Plate %d now at %.1f"%(i,ptemp)
    time.sleep(5)
    r.close()

exit(0)

