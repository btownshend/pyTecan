import scale
import time

r=scale.Scale()
wt=r.getweight()
fd=open("weight.csv","a")
print >>fd,time.ctime(),",",wt,",",",".join(sys.argv[1:])
ptemp=r.gettemp()
print "Weight=",wt
exit(int(wt*100))
