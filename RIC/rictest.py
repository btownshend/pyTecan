import ric

r=ric.RIC()
r.open()
print "Status = ",r.status()
r.settemp(50.0)
ptemp=r.gettemp()
print "ptemp=<",ptemp,">"
print "Set temp to 50.0, plate now at %.1f"%(ptemp)
print "Status = ",r.status()
r.idle()
print "Set to idle"
print "Status = ",r.status()
