# Setup TRP programs on TRobot
# Usage: trobotsetpgm name lidtemp {steps }
import trobot
import sys

try:
    p=trobot.TRobot()   # 10s timeout
    pgm=sys.argv[1]
    lidtemp=int(sys.argv[2])
    steps=[]
    for s in [s.replace('@',' ') for s in sys.argv[3:]]:
        a=s.split()
        if a[0]=='TEMP':
            b=a[1].split(',')
            temp=int(b[0])
            time=int(b[1])
            steps.append(["%x"%(temp*100),"%x"%time,'','','','','',''])
        elif a[0]=='RATE':
            rate=float(a[1])
            steps[-1][7]="%x"%(rate*100)
            pass
        elif a[0]=='GOTO':
            b=a[1].split(',')
            tgt=int(b[0])-1
            nloop=int(b[1])
            print "tgt=",tgt,", nloop=",nloop,",b=",b
            steps[-1][2]="%x"%tgt
            steps[-1][3]="%x"%nloop
        else:
            print "Bad command: ",s
            sys.exit(1)

    print "pgm=",pgm,", lidtemp=",lidtemp,", steps=[",steps,"]"
    p.program(pgm,lidtemp,["c "+",".join(x) for x in steps])
except Exception as err:
    print "Abnormal exit: ",err
    sys.exit(-1)


