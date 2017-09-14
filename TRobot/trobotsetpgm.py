# Setup TRP programs on TRobot
import debughook
import trobot
import sys

try:
    p=trobot.TRobot()   # 10s timeout
    p.setdebug()
    cmds=[]
    for s in [s.replace('@',' ') for s in sys.argv[2:]]:
        a=s.split()
        if a[0]=='TEMP':
            b=a[1].split(',')
            temp=int(b[0])
            time=int(b[1])
            cmds.append(["%x"%(temp*100),"%x"%time,'','','','','',''])
        elif a[0]=='RATE':
            rate=float(a[1])
            cmds[-1][7]="%x"%(rate*100)
            pass
        elif a[0]=='GOTO':
            b=a[1].split(',')
            tgt=int(b[0])-1
            nloop=int(b[1])
            print "tgt=",tgt,", nloop=",nloop,",b=",b
            cmds[-1][2]="%x"%tgt
            cmds[-1][3]="%x"%nloop
        else:
            print "Bad command: ",s
            sys.exit(1)

            print "cmds=",cmds
            p.program(sys.argv[1],99,["c "+",".join(x) for x in cmds])
except:
    sys.exit(-1)


