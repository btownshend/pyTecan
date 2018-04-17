import debughook
import re
import codecs
import datetime
import time

from Experiment.config import Config
from Experiment import logging
from datalog import Datalog
from Experiment.db import LogDB, DB   # Note: parselog is both the parent and current module name

Config.usedb=False



'Parse a GEMINI log file'
debug=False
dl=Datalog()

lnum=1
sbl=[0,0,0,0]
sml=[0,0,0,0]
zadd=[0,0,0,0]
tipSelect=0
ldpending=False
logdb=None

syscmds={
      'ALO':['Activate door lock output',['locknum','setting'],[]],
      'RFV':['Report firmare revision',[],['version']],
      'RLO':['Read door lock output',['locknum'],['setting']],
      'RLS':['UNDOCUMENTED Report',[],[]],
      'RSL':['UNDOCUMENTED Report ?light/alarm',['selector'],['value']],
      'SLO':['UNDOCUMENTED Set',[],[]],
      'SPN':['UNDOCUMENTED Set',[],[]],
      'SPS':['UNDOCUMENTED Set',[],[]],
      'SSL':['UNDOCUMENTED Set ?light/alarm',['selector','value'],[]],
}
romacmds={
      'AAA':['Action move to coordinate position',[]],
      'PAG':['Position absolute for gripper axis',['G'],[]],
      'PAX':['Position absolute for X-axis',['X'],[]],
      'PIA':['Position initialization',[],[]],
      'REE':['Report extended error code',[],['extError']],
      'RFV':['Report firmare revision',[],['version']],
      'RHW':['Report ROMA hardware version',[],['version']],
      'ROD':['Report gripper outrigger distance',[],['speed','PWMlimit','currLimit']],
      'RPG':['Report current parameter for gripper-axis',['selector'],['p1','p2','p3','p4','p5','p6','p7','p8']],
      'RPX':['Report current parameter for X-axis',['selector'],['p1','p2','p3','p4','p5','p6','p7','p8']],
      'RPY':['Report current parameter for Y-axis',['selector'],['p1','p2','p3','p4','p5','p6','p7','p8']],
      'RPZ':['Report current parameter for Z-axis',['selector'],['p1','p2','p3','p4','p5','p6','p7','p8']],
      'RPR':['Report current parameter for rotator-axis',['selector'],['p1','p2','p3','p4','p5','p6','p7','p8']],
      'SAA':['Set coordinate position into table',['tableindex','X','Y','Z','R','G','speed'],[]],
      'SRA':['Set range for absolute field',['X','Y','Z','R','G'],[]],
      'SGG':['Set gripper parameter',['speed','PWMlimit','CurLimit'],[]],
      'AGR':['Grip plate',['pos'],[]],
}      
m1cmds={
      'RFV':['Report firmare revision',[],['version']],
      'RSD':['UNDOCUMENTED Report',[],[]],
      }
lihacmds={
      'AGT':['Get a disposable tip',['TipSelect','Zstart','searchDist'],[]],
      'AST':['Spash free discard tip',['tipSelect','logPos'],[]],
      'BMX':['Stop X drive movement immediately',[]],
      'BMY':['Stop Y drive movement immediately',[]],
      'BMZ':['Stop Z drive movement immediately',[]],
      'MAX':['Position absolute slow speed for X axis',['speed1','speed2','speed3','speed4','speed5','speed6','speed7','speed8'],[]],
      'MAY':['Position absolute slow speed for Y axis',['speed1','speed2','speed3','speed4','speed5','speed6','speed7','speed8'],[]],
      'MAZ':['Position absolute slow speed for Z axis',['speed1','speed2','speed3','speed4','speed5','speed6','speed7','speed8'],[]],
      'MDT':['Move tip, detect liquid, submerge',['tipSelect','submerge','Zstart','Zmax','Zadd1','Zadd2','Zadd3','Zadd4','Zadd5','Zadd6','Zadd7','Zadd8'],[]],
      'MET':['Move tip, detect liquid, submerge (stay at Z-max on error)',['tipSelect','submerge','Zstart','Zmax','Zadd1','Zadd2','Zadd3','Zadd4','Zadd5','Zadd6','Zadd7','Zadd8'],[]],
      'MRX':['Position relative slow speed for X axis',['X','slowSpeed'],[]],
      'MRY':['Position relative slow speed for Y axis',['Y','slowSpeed'],[]],
      'MRZ':['Position relative slow speed for Z axis',['Z','slowSpeed'],[]],
      'MTR':['Move plunger in units of 1/12 ul (UNDOCUMENTED)',['vol1','vol2','vol3','vol4','vol5','vol6','vol7','vol8'],[]],
      'PAA':['Position absolute for all axis',['X','Y','Ys','Z1','Z2','Z3','Z4','Z5','Z6','Z7','Z8'],[]],
      'PAZ':['Position aboslute for Z-axis',['Z1','Z2','Z3','Z4','Z5','Z6','Z7','Z8'],[]],
      'PIA':['Position initialization',[],[]],
      'PID':['UNDOCUMENTED ?Position',[],[]],
      'PIX':['Position initialization X axis',[],[]],
      'PPA':['UNDOCUMENTED ?Position',[],[]],
      'PPR':['Airgap plunger move (UNDOCUMENTED)',['vol1','vol2','vol3','vol4'],[]],
      'PRX':['Position relative for X axis',['X'],[]],
      'PRY':['Position relative for Y axis',['Y'],[]],
      'PRZ':['Position relative for Z axis',['Z'],[]],
      'PRR':['Position relative for rotator axis',['R'],[]],
      'PRG':['Position relative for gripper axis',['gripper'],[]],
      'PSY':['Y spacing of tips',['spacing'],[]],
      'PVL':['UNDOCUMENTED',[],[]],
      'RDA':['Report liquid detection acceleration',[],['acceleration']],
      'RDS':['UNDOCUMENTED Report',[],[]],
      'RDZ':['Report diagnotic functions Z-Axis',['selector'],['d1','d2','d3','d4','d5','d6','d7','d8']],
      'REE':['Report extended error code',[],['extError']],
      'RFV':['Report firmare revision',[],['version']],
      'RGD':['UNDOCUMENTED Report',[],[]],
      'RNT':['Report number of tips on arm',['decimalNotBinary'],['numtips']],
      'RPP':['UNDOCUMENTED (get max of each tip?)',[],['vol1','vol2','vol3','vol4','vol5','vol6','vol7','vol8']],
      'RPX':['Report current parameter for X-axis',['selector'],['p1','p2','p3','p4','p5','p6','p7','p8']],
      'RPY':['Report current parameter for Y-axis',['selector'],['p1','p2','p3','p4','p5','p6','p7','p8']],
      'RPZ':['Report current parameter for Z-axis',['selector'],['p1','p2','p3','p4','p5','p6','p7','p8']],
      'RSD':['Report presence of splash-free DiTi eject option',[],['isPresent']],
      'RST':['Report presence of splash-free DiTi eject logical positions',[],['upperPos','lowerPos','discardDist']],
      'RTS':['Report tip status DiTi',[],['fetched']],
      'RVZ':['Report Z-axis values and parameters',['selector'],['p1','p2','p3','p4','p5','p6','p7','p8']],
      'SBL':['Set individual submerge for liquid search command',['submerge1','submerge2','submerge3','submerge4','submerge5','submerge6','submerge7','submerge8'],[]],
      'SDL':['Set individual safe detection retract distance for liquid search command',['safeDRD1','safeDRD2','safeDRD3','safeDRD4','safeDRD5','safeDRD6','safeDRD7','safeDRD8',],[]],
      'SDM':['Set liquid detection mode',['detProc(0-common,1-commonsafe,2-semi,3-semisafe,4-full,5-fullsafe,6-delay,7-trough)','sensitivity','phase','dipIn','dipOut'],[]],
      'SEP':['UNDOCUMENTED Set',[],[]],
      'SHZ':['Set individual Z-travel height',['Ztravel1','Ztravel2','Ztravel3','Ztravel4','Ztravel5','Ztravel6','Ztravel7','Ztravel8'],[]],
      'SML':['Set individual z-max for liquid search command',['Zmax1','Zmax2','Zmax3','Zmax4','Zmax5','Zmax6','Zmax7','Zmax8'],[]],
      'STL':['Set individual z-start for liquid search command',['Zstart1','Zstart2','Zstart3','Zstart4','Zstart5','Zstart6','Zstart7','Zstart8'],[]],
      'SPP':['UNDOCUMENTED Set',[],[]],
      'SPS':['Set pierce speed for piercing commands',['speed','pwmlimit','curlimit'],[]],
      'SSL':['Set search speed for liquid search commands',['speed1','speed2','speed3','speed4','speed5','speed6','speed7','speed8'],[]],
      'SSX':['Set slow speed for X-axis',['speed1','speed2','speed3','speed4','speed5','speed6','speed7','speed8'],[]],
      'SSY':['Set slow speed for Y-axis',['speed1','speed2','speed3','speed4','speed5','speed6','speed7','speed8'],[]],
      'SSZ':['Set slow speed for Z-axis',['speed1','speed2','speed3','speed4','speed5','speed6','speed7','speed8'],[]],
      'STZ':['UNDOCUMENTED Set',[],[]],
      'T20':['UNDOCUMENTED',[],[]],
      'T21':['UNDOCUMENTED',[],[]],
      'T22':['UNDOCUMENTED',[],[]],
      'T23':['UNDOCUMENTED',[],[]],
      'T30':['UNDOCUMENTED',[],[]],
      'T32':['UNDOCUMENTED',[],[]],
      }
devnames={'C1':['RoMa',romacmds],'C2':[ 'RoM2',romacmds], 'C5':['LiHa',lihacmds],'C6':['LiH6',lihacmds], 'O1':['Syst',syscmds],'M1':['M1',m1cmds] }

errors={1:'Initialization Error',  # Common errors
        2:'Invalid Command',
        3:'Invalid Operand',
        4:'Invalid Cmd Sequence',
        5:'Device no implement',
        6:'Time-out Error',
        7:'Device not initialized',
        8:'Command overflow of CU',
        15:'Command overflow of subdevice'}
errorsA={9:'No liquid detected',    # Device A error codes (LiHa)
        10:'Drive no load',
        11:'Not enough liquid',
        12:'Not enough liquid',
        13:'Arm collision avoided with PosId',
        16:'Power fail circuit error',
        17:'Arm collision avoided with RoMa',
        18:'Clot limit passed',
        19:'No clot exit detected',
        20:'No liquid exit detected',
        23:'Not yet moved',
        24:'Ilid pulse error',
        25:'Tip not fetched',
        26:'Tip not mounted',
        27:'Tip mounted'}
errorsR={9:'Plate not fetched',         # ROMA Errors (R)
        10:'Drive no load',
        16:'Power fail circuit error',
        17:'Arm collision avoided with LiHa'}
errorsM={13:'No access to serial EEPROM',   # System errors (M)
        16:'Power fail circuit error',
        17:'Arm collision avoided between LiHa and RoMa',
        18:'Door lock 1 failed',
        19:'Door lock 2 failed',
        20:'No new device node detected',
        21:'Device node already defined'}

def displaymatch(match):
    if match is None:
        return None
    return '<Match: %r, groups=%r>' % (match.group(), match.groups())

def gemtip(tipcmd,line2,outfd):
    """Handle Gemini command of form:  tip 2 : aspirate 9.00ul 10, 1 HSP96xx on carrier [4,2]                 8.00ul "Water-InLiquid" Standard <all volumes> Multi"""
    fullcmd=tipcmd[8:]+line2
    if debug:
        print("XFR ",fullcmd,file=outfd)
    # Parse the line
    parser1=re.compile(r"tip (\d+) : (\S+) +(?:(\d+\.\d+)(.l) +)?(?:\((\d)+x\))? *(\d+), *(\d+) +(.+) +\[(\d+),(\d+)\]")
    if debug:
        print(displaymatch(parser1.match(tipcmd)),file=outfd)
    match=parser1.match(tipcmd)
    g=match.groups()
    assert(len(g)==10)
    tip=int(g[0])
    op=g[1]
    if g[2] is None:
        vol=0
    else:
        vol=float(g[2])
    units=g[3]
    if units=='nl':
        vol=vol/1000.0
    if g[4] is not None:
        nmix=int(g[4])
    else:
        nmix=None
    wellx=int(g[5])
    welly=int(g[6])
    rack=g[7]
    grid=int(g[8])
    pos=int(g[9])
    parser2=re.compile(r" +(?:(\d+\.\d+)(.l) +)?\"(.+)\" (?:(.+) <(.+)> (\S+))?")
    if debug:
        print(displaymatch(parser2.match(line2)),file=outfd)
    match=parser2.match(line2)
    g=match.groups()
    assert(len(g)==6)
    if g[0] is None:
        vol2=0
    else:
        vol2=float(g[0])
    units=g[1]
    if units=='nl':
        vol2=vol2/1000.0
    lc=g[2]
    std=g[3]
    volset=g[4]
    ptype=g[5]
    if op=="mix":
        op="%s%d"%(op,nmix)
    msg1="tip=%d, op=%s, vol=%.2f/%.2f, wellx=%d, welly=%d, rack=%s, grid=%d, pos=%d, lc=%s, pytpe=%s"%(tip,op,vol,vol2,wellx,welly,rack,grid,pos,lc,ptype)
    #msg2="tip=%d, wellx=%d, welly=%d, rack=%s, grid=%d, pos=%d, lc=%s"%(tip,wellx,welly,rack,grid,pos,lc)
    if debug:
        print("XFR",msg1,file=outfd)
    dl.logop(op,tip,vol,wellx,welly,rack,grid,pos,lc,std,volset,ptype=='Multi')
    
def fwparse(dev,send,reply,error,lasttime,outfd):
    global lnum, sbl, sml, tipSelect, ldpending, zadd
    if debug:
        if error:
            print("\tSEND:%s  ERROR:%s"%(str(send),str(reply)),file=outfd)
        else:
            print("\tSEND:%s  REPLY:%s"%(str(send),str(reply)),file=outfd)
    if  reply[0].isdigit():
        replyecode=int(reply[0])
    else:
        print("First reply argument is not an integer: %s"%reply[0],file=outfd)
        replyecode=-1
    reply=reply[1:]
    op=send[0]
    args=send[1:]
    if dev in devnames:
        devname=devnames[dev][0]
        cmds=devnames[dev][1]
        if op in cmds:
              cmd=cmds[op]
        else:
              cmd=['UNKNOWN',[],[]]
    else:
       devname='UNKNOWN(%s)'%dev
       cmd=['UNKNOWN',[],[]]

    print("  %s %s (%s) "%(devname,op,cmd[0]), end=' ',file=outfd)
    for i in range(len(args)):
        if i<len(cmd[1]):
            print("%s=%s, "%(cmd[1][i],args[i]), end=' ',file=outfd)
        else:
            print("?=%s, "%args[i], end=' ',file=outfd)
    print(" ->  ecode=%d, "%replyecode, end=' ',file=outfd)
    for i in range(len(reply)):
        if i<len(cmd[2]):
            print("%s=%s, "%(cmd[2][i],reply[i]), end=' ',file=outfd)
        else:
            print("?=%s, "%reply[i], end=' ',file=outfd)
    print(flush=True,file=outfd)
    if error or replyecode!=0:
        if replyecode in errors:
            emsg=errors[replyecode]
        elif devname[0:3]=='LiH' and replyecode in errorsA:
            emsg=errorsA[replyecode]
        elif devname[0:3]=='RoM' and replyecode in errorsR:
            emsg=errorsR[replyecode]
        elif devname=='System' and replyecode in errorsM:
            emsg=errorsM[replyecode]
        else:
            emsg='Unknown error: <%s>'%replyecode
        print("**** Error message: %s"%emsg,file=outfd)
    if op=='SBL':
        sbl=[int(r) if len(r)>0 else 0 for r in args]
        #print "TIPS SBL=",sbl
    if op=='SML':
        sml=[int(r) if len(r)>0 else 0 for r in args]
    if op=='MET' or op=='MDT':
        if len(args[1])>0:
            sbl=[int(args[1]) for _ in [0,1,2,3]]
        if len(args[3])>0:
            sml=[int(args[3]) for _ in [0,1,2,3]]
        zadd=[int(x) for x in args[4:8]]
        tipSelect=int(args[0])
        ldpending=True
        # if replyecode==0:
        #     ldpending=True
        #else:
            # heights=[-1,-1,-1,-1]
            # for i in range(len(heights)):
            #     if 1<<i & tipSelect != 0:
            #         print("TIPS %d %s "%(lnum,op),heights[i],sbl[i],sml[i],heights[i]+sbl[i]-sml[i],file=outfd)
            #         dl.logmeasure(i+1,heights[i],sbl[i],sml[i],zadd[i],lasttime)
            #         logdb.lastmeasure(i+1,lnum,heights[i],sbl[i],sml[i],zadd[i],lasttime)
    elif ldpending and (op=='RPZ' or op=='RVZ') and int(args[0])==0:
        heights=[int(r) for r in reply]
        assert(len(heights)==len(sbl))
        for i in range(len(heights)):
            if 1<<i & tipSelect != 0:
                print("TIPS %d  " % lnum, heights[i], sbl[i], sml[i], heights[i] + sbl[i] - sml[i],file=outfd)
                dl.logmeasure(i+1,heights[i],sbl[i],sml[i],zadd[i],lasttime)
                logdb.lastmeasure(i+1,lnum,heights[i] if heights[i]!=sml[i] else None, sbl[i], sml[i], zadd[i], lasttime)
        ldpending=False
    elif op == 'REE' or op=='RVZ':
        pass
    elif ldpending:
        print("**** Parser error:  got op %s without a RPZ while ldpending"%op,file=outfd)
        #assert(False)
        ldpending=False

        
import sys
import argparse
from Experiment.config import Config
from Experiment import globals

def main():
    parser = argparse.ArgumentParser(description="parselog")
    parser.add_argument('-v', '--verbose', help='Enable verbose output', default=False, action="store_true")
    parser.add_argument('-f', '--follow', help='Wait for more output', default=False, action="store_true")
    parser.add_argument('-p', '--password', type=str, help='DB Password')
    parser.add_argument('-N', '--nodb', help='No DB logging', default=False, action="store_true")
    parser.add_argument('-d','--dirscan', type=str, help='Directory to continuously scan as daemon')
    parser.add_argument("logfile",nargs='?',default=None)

    args = parser.parse_args()
    globals.verbose=args.verbose

    # Turn on DB access if needed
    Config.usedb = not args.nodb
    if args.password is not None:
        Config.password = args.password

    sys.stdout = codecs.getwriter("latin-1")(sys.stdout.detach())

    if args.dirscan is not None:
        dirscan(args.dirscan,args.follow)
    elif args.logfile is not None:
        parselog(args.logfile,args.logfile.replace('.LOG','.TXT'),follow=args.follow)
    else:
        parselog(None)   # stdin -> stdout

def dirscan(dirname: str, follow: bool=False):
    import os
    import datetime as dt

    print('dirscan of ', dirname)

    now = dt.datetime.now()
    ago = now - dt.timedelta(days=30)
    db = DB()
    db.connect()

    while True:
        for fname in os.listdir(dirname):
            if re.match('LOG[0-9]*\.LOG',fname):
                path = os.path.join(dirname, fname)
                st = os.stat(path)
                mtime = dt.datetime.fromtimestamp(st.st_mtime)
                if mtime > ago:
                    if b'@log_startrun' in open(path,'rb').read():
                        print('%s Contains log_startrun, modified %s' % (path, mtime))
                        runstatus=db.findlog(fname)
                        print("runstatus=%d"%runstatus)
                        if runstatus!=2:
                            try:
                                parselog(path,path.replace('.LOG','.TXT'),follow=follow)
                            except Exception as exc:
                                print("Failed parse of %s: "%path,exc)
                                import traceback
                                traceback.print_exc()
            else:
                pass # print("Ignoring %s"%fname)
        print('Done processing files in %s'%dirname,flush=True)
        if not follow:
            break
        ago=now
        print('Sleeping...',end='',flush=True)
        time.sleep(30)
        print('done',flush=True)
        now=dt.datetime.now()

def parselog(filename: str, outfile:str=None, follow=False):
    global logdb, lnum

    if filename is not None:
          fd=open(filename,'rb')
    else:
          fd=sys.stdin

    if outfile is not None:
        outfd=open(outfile,'w')
    else:
        outfd=sys.stdout

    csum=fd.readline()
    hdr=fd.readline()
    version=fd.readline()
    prevcode='?'
    prevtime='?'
    send={}
    error=False
    lastgeminicmd=None
    geminicmdtimes={}
    geminicmdcnt={}
    tipcmd=""
    lasttime=datetime.datetime.strptime(hdr[:15].decode('latin-1'),'%Y%m%d_%H%M%S')
    print("Header time: %s"%str(lasttime),file=outfd)
    shakePlate=None   # Plate on shaker
    logdb=LogDB(filename)
    # Handle high-bit characters in stdout (since .log contains 0xb5 (\micro) charactures
    sleeping=False

    while True:
        bline=fd.readline()
        if not bline:
            if follow:
                if not sleeping:
                    logdb.flush()
                    print("sleeping at line %d of %s..."%(lnum,filename),end='',flush=True)
                    sleeping=True
                time.sleep(10)
                continue
            else:
                break
        if sleeping:
            print("done")
            sleeping=False
        while len(bline)>0 and (bline[-1]==13 or bline[-1]==10):
            bline=bline[:-1]
        #line=line.rstrip('\r\n')
        if len(bline)==0:
            continue

        line=bline.decode('latin-1')
        code=line[0]
        gtime=line[2:10]
        cmd=line[11:]
        if debug:
            print("\tcode=%s(%d),time=%s,cmd=%s"%(code,ord(code[0]),gtime,cmd),file=outfd)
        if code[0]==' ':
              if prevcode[0]!='D':
                    # print "Copying previous code: %c"%prevcode
                    code=prevcode
              else:
                    print("Blank code, previous=D, assuming new one is F",file=outfd)
                    code='F'
        if len(gtime)<1 or gtime[0]==' ':
            gtime=prevtime
        prevcode=code
        prevtime=gtime
        if code[0]=='F':
            spcmd=cmd[1:].split(',')
            dev=spcmd[0][1:]
            spcmd=spcmd[1:]
            if len(cmd)<1:
                print("Empty cmd",file=outfd)
            elif cmd[0]=='>':
                if dev in send:
                    print("Double cmd to %s: %s AND %s"%(dev,send[dev],str(spcmd)),file=outfd)
                send[dev]=[spcmd[0][0:3],spcmd[0][3:]]+spcmd[1:]
            elif cmd[0]=='-' or cmd[0]=='*':
                if dev not in send:
                    print("Missing cmd when received reply from %s: %s"%(dev,str(spcmd)),file=outfd)
                    exit(1)
                error=cmd[0]=='*'
                fwparse(dev,send[dev],spcmd,error,lasttime,outfd)
                send.pop(dev)
            else:
                print("Bad cmd: %s"%cmd)
        else:
              if cmd.find('detected_volume_')==-1 or cmd.find('= -1')==-1:
                    print("Gemini %s %s"%(gtime,cmd),file=outfd)
                    if cmd[0:3]=='tip':
                        tipcmd=cmd
                    else:
                        if  len(tipcmd)>0 and cmd[0:3]=='   ':
                            gemtip(tipcmd,cmd,outfd)
                        tipcmd=""

              if cmd.find("setShakeTargetSpeed")!=-1:
                    pos=cmd.find("setShakeTargetSpeed")
                    speed=int(cmd[pos+19:])
                    print("SPEED %d"%speed,file=outfd)
                    dl.logspeed(shakePlate,speed)

              if cmd.startswith("moveplate") and cmd.find("Shaker")!=-1:
                    pos=cmd.find("Shaker")
                    shakePlate=cmd[10:pos-1]
                    print("SHAKEPLATE %s"%shakePlate,file=outfd)

              if cmd.startswith('Line'):
                    colon=cmd.find(':')
                    cname=cmd[(colon+2):]
                    lnum=int(cmd[4:(colon-1)])
                    logdb.setline(lnum)
                    #print "cname=",cname
                    t=datetime.datetime.combine(lasttime.date(),datetime.datetime.strptime(gtime,'%H:%M:%S').time())
                    if (t-lasttime).total_seconds()<0:
                        t=t+datetime.timedelta(1)   # Wrapped around
                        logging.notice("Gemini time wrapped from %s to %s"%(lasttime,t))

                    if lastgeminicmd is not None:
                        if (t-lasttime).total_seconds() > 30:
                            print("Skipping long pause of %s for %s"%(str(t-lasttime),lastgeminicmd),file=outfd)
                        elif t<lasttime:
                            assert False # Shouldn't happen
                            print("Skipping negative elapsed time of %d seconds for %s"%((t-lasttime).total_seconds(),lastgeminicmd),file=outfd)
                        elif lastgeminicmd in list(geminicmdtimes.keys()):
                            geminicmdtimes[lastgeminicmd]+=(t-lasttime).total_seconds()
                            geminicmdcnt[lastgeminicmd]+=1
                        else:
                            geminicmdtimes[lastgeminicmd]=(t-lasttime).total_seconds()
                            geminicmdcnt[lastgeminicmd]=1
                    lastgeminicmd=cname
                    lasttime=t
              if cmd.startswith('@'):
                  print("PYTHON: %s" % cmd[1:],file=outfd)
                  eval("logdb." + cmd[1:])
                  if cmd.startswith('@log_endrun'):
                      # Done processing file
                      break
              if cmd.find('closing log-file') != -1:
                  # End of log (in case we're in -f mode)
                  print("Found closing log-file message; exiting",file=outfd)
                  break

    logdb.flush()
    #print "log=",dl
    dl.printallsamples(fd=outfd)  # This 'sys.stdout' (modified above) seems different from the default one that Samples.print* would use

    for cmd in list(geminicmdtimes.keys()):
          print("%s: %.0f seconds for %.0f occurrences:   %.2f second/call"%(cmd,geminicmdtimes[cmd],geminicmdcnt[cmd], geminicmdtimes[cmd]*1.0/geminicmdcnt[cmd]),file=outfd)


main()