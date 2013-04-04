import ptc
import sys
import time

if len(sys.argv)!=2 or ( sys.argv[1]!="OPEN" and sys.argv[1]!="CLOSE"):
    print "Usage: %s (OPEN|CLOSE)"%sys.argv[0]
    exit(2)
cmd=sys.argv[1]
p=ptc.PTC()
res=p.execute('LID %s'%(cmd))
if len(res)>0:
    print "Result=",res
for i in range(5):
    lidstatus=p.getlidstatus()
    print "Lid is %s"%lidstatus
    if cmd=="OPEN":
        if lidstatus=="OPEN":
            exit(0)
        elif lidstatus!="OPENING":
            print "Unexpected lid status"
            exit(1)
    else:
        if lidstatus=="CLOSED":
            exit(0)
        elif lidstatus!="CLOSING":
            print "Unexpected lid status"
            exit(1)
    time.sleep(2)

print "Lid is not completing operation"
exit(1)
