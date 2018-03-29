"""Module for generating a worklist from a set of commands"""
from __future__ import print_function

import math
import string
import sys
import shutil
from zlib import crc32

from . import clock
from . import logging
from .plate import Plate

WASHLOC=Plate("Wash",1,2,1,8,False,0)    # Duplicate of what's in decklayout.py -- but don't want to include all those dependencies...
QPCRLOC=Plate("qPCR",4,1,12,8,False,0)    # Duplicate of what's in decklayout.py -- but don't want to include all those dependencies...

DITI200=0
DITI10=2
OPEN=0
CLOSE=1
DONOTMOVE=2
SAFETOEND=0
ENDTOSAFE=1

lnum=0
debug=False
wlist=[]
volumes={}
diticnt=[0,0,0,0]   # Indexed by DiTi Type
delayEnabled=False
opQueue=[]
hashCodes={}
#tipHash=[crc32("tip1"),crc32("tip2"),crc32("tip3"),crc32("tip4")]
# Don't care if different tips are used:
tipHash=[0,0,0,0]
#print "tipHash=[%06x,%06x,%06x,%06x]"%(tipHash[0],tipHash[1],tipHash[2],tipHash[3])
timerstart=None
nloops=0

def reset():
    global hashCodes, lnum,volumes,opQueue, hashCodes,tipHash,wlist, nloops
    hashCodes={}
    lnum=0
    volumes={}
    opQueue=[]
    hashCodes={}
    tipHash=[0,0,0,0]
    wlist=[]
    nloops=0   # Gemini crashes if more than 100 loops

def setOptimization(onoff):
    global delayEnabled
    if onoff:
        comment("*Optimization on")
    else:
        flushQueue()
        comment("*Optimization off")
    delayEnabled=onoff

def wellSelection(nx,ny,pos):
    """Build a well selection string"""
    s="%02x%02x"%(nx,ny)
    vals=[0] * (7*((nx*ny+6)/7))
    for i in pos:
        vals[i]=1
    bitCounter=0
    bitMask=0
    for i in range(len(vals)):
        if vals[i]:
            bitMask=bitMask | (1<<bitCounter)
        bitCounter=bitCounter+1
        if bitCounter>6:
            s=s+chr(0x30+bitMask)
            bitCounter=0
            bitMask=0
    if bitCounter>0:
        s=s+chr(0x30+bitMask)
    return s

def getline():
    return len(wlist)+1

def moveliha( loc):
    """Move LiHa to specified location"""
    flushQueue()
    tipMask=15
    speed=10   # 0.1-400 (mm/s)
    #comment('*MoveLiha to '+str(loc))
    wlist.append( 'MoveLiha(%d,%d,%d,1,"0104?",0,4,0,%.1f,0)'%(tipMask,loc.grid,loc.pos-1,speed))
    clock.pipetting+=0.89

def optimizeQueue():
    """Optimize operations in queue"""
    global opQueue
    optimizeDebug=False

    if optimizeDebug:
        print("Optimizing queue with %d entries"%len(opQueue))
    # Assign IDs
    for i in range(len(opQueue)):
        opQueue[i].append([i])

    # Queue entries are
    # 0:op
    # 1:tipMask
    # 2:wells
    # 3:liquidClass
    # 4:volume
    # 5:loc
    # 6:cycles
    # 7:id number

    # Build dependency list
    dependencies=[]
    for i in range(len(opQueue)):
        d=opQueue[i]
        dependencies.append(set())
        for j in range(i):
            dp=opQueue[j]
            if d[5].grid==dp[5].grid and d[5].pos==dp[5].pos and d[2]==dp[2]: # and d[0]!=dp[0]:
                # Multiple operations from same location (NOT ok to reorder multiple aspirates or dispenses from same location)
                dependencies[i] |= dependencies[j]
                dependencies[i].add(j)
#                    if optimizeDebug:
#                       print "%d,%d: same location"%(i,j)
            elif d[1]==dp[1]:
                # Same tip
                dependencies[i] |= dependencies[j]
                dependencies[i].add(j)
#                    if optimizeDebug:
#                        print "%d,%d: same tip"%(i,j)

    # Compute all possible merges
    mergeable=[]
    for i in range(len(opQueue)):
        d1=opQueue[i]
        mergeable.append(set())
        for j in range(len(opQueue)):
            d2=opQueue[j]
            if d1[0]==d2[0]  and d1[1]!=d2[1] and d1[5]==d2[5]:
                if optimizeDebug:
                    print("  CHECK %s %s:\tTip %d, Loc (%d,%d) Wells %s"%(d1[7],d1[0],d1[1],d1[5].grid,d1[5].pos,str(d1[2])))
                    print("   WITH %s %s:\tTip %d, Loc (%d,%d) Wells %s"%(d2[7],d2[0],d2[1],d2[5].grid,d2[5].pos,str(d2[2])), end=' ')
                tipdiff=math.log(d2[1],2)-math.floor(math.log(d1[1],2))
                welldiff=d2[2][0]-max(d1[2])
                if tipdiff!=welldiff:
                    if optimizeDebug:
                        print("  tipdiff (%d) != welldiff(%d)"%(tipdiff,welldiff))
                elif d1[2][0]/d1[5].ny != d2[2][0]/d2[5].ny:
                    if optimizeDebug:
                        print("  wells in different columns of %d-row plate"%d1[5].ny)
                elif d1[3].name!=d2[3].name:
                    if optimizeDebug:
                        print("  liquid classes different",d1[3],d2[3])
                elif d1[6]!=d2[6]:
                    if optimizeDebug:
                        print("  mix cycles different")
                else:
                    if optimizeDebug:
                        print("  can merge")
                    mergeable[i].add(j)

    if optimizeDebug:
        for i in range(len(opQueue)):
            d=opQueue[i]
            print("PRE-OPT %s:  %s:\tTip %d, Loc (%d,%d) Wells %s, Vol %s, depends on %s, merges with %s"%(d[7],d[0],d[1],d[5].grid,d[5].pos,str(d[2]),d[4],dependencies[i],mergeable[i]))

    # Try to combine multiple operations into one command
    todelete=[]
    newQueue=[]
    while len(opQueue)>len(todelete):
        #print "%d entries left to process"%(len(opQueue)-len(todelete))
        # Find 2 nodes that are mergeable and have no dependencies
        for i in range(len(opQueue)):
            if i in todelete or len(dependencies[i])>0:
                continue
            #print "Attempt to merge %s with one of %s"%(opQueue[i][7],mergeable[i])
            m=set()
            m.update(mergeable[i])
            for j in m:
                if j in todelete or len(dependencies[j])>0:
                    continue
                d1=opQueue[i]
                d2=opQueue[j]
                merge=[d1[0],d1[1]|d2[1],d1[2]+d2[2],d1[3],d1[4]+d2[4],d1[5],d1[6],d1[7]+d2[7]]
                # Reorder based on well order
                ordering=sorted(list(range(len(merge[2]))), key=lambda x: merge[2][x])
                merge[2]=[merge[2][k] for k in ordering]
                merge[4]=[merge[4][k] for k in ordering]
                merge[7]=[merge[7][k] for k in ordering]
                opQueue[i]=merge
                todelete.append(j)
                # Redirect dependencies
                for k in range(len(dependencies)):
                    if j in dependencies[k]:
                        dependencies[k].add(i)
                        dependencies[k].remove(j)
                # Other mergeables
                mergeable[i] &= mergeable[j]
                #comment("Merged operations")
                if optimizeDebug:
                    print("MERGED %s %s:\tTip %d, Loc (%d,%d) Wells %s depends on %s, merges with %s, vol=%s "%(merge[7],merge[0],merge[1],merge[5].grid,merge[5].pos,str(merge[2]),dependencies[i],mergeable[i],merge[4]))

        # Finished doing all the merges we can do with the current set of operations that don't depend on any prior operations
        # Find something to emit/delete
        emitted=False
        for maxMergeable in range(len(opQueue)):
            for i in range(len(opQueue)):
                if i in todelete or len(dependencies[i])>0 or len(mergeable[i])>maxMergeable:
                    continue
                # Emit i
                #print "Emit %s"%opQueue[i][7]
                emitted=True
                newQueue.append(opQueue[i])
                todelete.append(i)
                # Remove all dependencies on deleted entries
                for k in range(len(dependencies)):
                    dependencies[k].discard(i)
                break
            if emitted:
                break

    opQueue=newQueue
    for i in range(len(opQueue)):
        d=opQueue[i]
        if optimizeDebug:
            print("POST-OPT %s:  %s:\tTip %d, Loc (%d,%d) Wells %s"%(d[7],d[0],d[1],d[5].grid,d[5].pos,str(d[2])))

def flushQueue():
    global delayEnabled,opQueue
    if not delayEnabled or len(opQueue)==0:
        return
    #comment('*Flush queue')
    optimizeQueue()
    for d in opQueue:
        aspirateDispense(d[0],d[1],d[2],d[3],d[4],d[5],d[6],False)
    opQueue=[]

#def aspirate(tipMask, liquidClass, volume, loc, spacing, ws):
def aspirate(tipMask,wells, liquidClass, volume, loc):
    aspirateDispense('Aspirate',tipMask,wells, liquidClass, volume, loc)

# aspirate without manual conditioning
# NOTE: This results in using single instead of multi pipetting and is thus affected by the diluter calibration in Gemini
def aspirateNC(tipMask,wells, liquidClass, volume, loc):
    aspirateDispense('AspirateNC',tipMask,wells, liquidClass, volume, loc)

def dispense(tipMask,wells, liquidClass, volume, loc):
    aspirateDispense('Dispense',tipMask,wells, liquidClass, volume, loc)

def mix(tipMask,wells, liquidClass, volume, loc, cycles=3, allowDelay=True):
    aspirateDispense('Mix',tipMask,wells, liquidClass, volume, loc, cycles, allowDelay)

def detectLiquid(tipMask,wells,liquidClass,loc):
    aspirateDispense('Detect_Liquid',tipMask,wells, liquidClass, [0.0 for _ in wells], loc,allowDelay=False)

def aspirateDispense(op,tipMask,wells, liquidClass, volume, loc, cycles=None,allowDelay=True):
    """Execute or queue liquid handling operation"""
    assert isinstance(loc,Plate)

    if loc.pos==0 or loc.grid>=25:
        # Attempting to use LiHa in ROMA-Only area
        logging.error("Attempt to %s to/from %s at position (%d,%d), which is in ROMA-only area not accessible to LiHa"%(op,loc.name,loc.grid,loc.pos))

    liquidClass.markUsed(op)

    if type(volume)!=type([]):
        volume=[volume]*len(wells)

    if delayEnabled and allowDelay:
        opQueue.append([op,tipMask,wells,liquidClass,volume,loc,cycles])
#            comment("*Queued: %s tip=%d well=%s.%s vol=%s lc=%s"%(op,tipMask,str(loc),str(wells),str(volume),str(liquidClass)))
        return

    if op=='Mix':
        clock.pipetting+=12.53
    elif op=='Dispense':
        clock.pipetting+=3.70
    elif op=='Aspirate':
        clock.pipetting+=5.14+3.70   # Extra for conditioning volume
    elif op=='AspirateNC':
        clock.pipetting+=5.14
    elif op=='Detect_Liquid':
        clock.pipetting+=2.90

    comment("*%s tip=%d well=%s.%s vol=%s lc=%s"%(op,tipMask,str(loc),str(wells),str(volume),str(liquidClass)))
    # Update volumes
    for i in range(len(wells)):
        well=wells[i]
        v=volume[i]
        if op=='Aspirate' or op=='AspirateNC':
            vincr=-v
        elif op=='Dispense':
            vincr=v
        else:
            vincr=0

        if vincr != 0:
            if loc not in volumes:
                volumes[loc]={}
            if well not in volumes[loc]:
                volumes[loc][well]=vincr
            else:
                volumes[loc][well]=volumes[loc][well]+vincr

    spacing=1
    pos=[0] * len(wells)
    prevcol=None
    for i in range(len(wells)):
        well=wells[i]
        if isinstance(well,int):
            ival=int(well)
            (col,row)=divmod(ival,loc.ny)
            col=col+1
            row=row+1
        else:
            col=int(well[1:])
            row=ord(well[0])-ord('A')+1
        assert 1 <= row <= loc.ny and 1 <= col <= loc.nx
        pos[i]=(row-1)+loc.ny*(col-1)
        if i>0:
            assert col==prevcol
        prevcol=col

    span=pos[len(pos)-1]-pos[0]
    if span<4:
        spacing=1
    else:
        spacing=2
    allvols=[0]*12
    tip=0
    tipTmp=tipMask
    for i in range(len(wells)):
        while tipTmp&1 == 0:
            tipTmp=tipTmp>>1
            tip=tip+1
        allvols[tip]=volume[i]
        hashUpdate(op,tip,loc.grid,loc.pos-1,pos[i],allvols[tip])
        #comment("Hash(%d,%d,%d)=%06x"%(loc.grid,loc.pos,pos[i],getHashCode(loc.grid,loc.pos-1,pos[i])&0xffffff))
        tipTmp = tipTmp>>1
        tip+=1

    if tipTmp!=0:
        logging.error("Number of tips (mask=%d) != number of wells (%d)"%(tipMask, len(wells)))

    if debug:
        print("allvols=",allvols)
        print("pos[0]=",pos[0])
        print("spacing=",spacing)

    ws=wellSelection(loc.nx,loc.ny,pos)
    condvol=""  # Initialize to avoid warnings below
    if op=='Aspirate':
        if allvols[0]>0:
            volstr="%.3f"%(allvols[0]+2)
            condvol="2"
        else:
            volstr="%.3f"%(allvols[0])
            condvol="0"
        for i in range(1,12):
            if allvols[i]>0:
                c=2
            else:
                c=0
            volstr="%s,%.3f"%(volstr,allvols[i]+c)
            condvol="%s,%.3f"%(condvol,c)
    else:
        volstr="%.3f"%allvols[0]
        for i in range(1,12):
            volstr="%s,%.3f"%(volstr,allvols[i])

    if op=="Mix":
        wlist.append( '%s(%d,"%s",%s,%d,%d,%d,"%s",%d,0)'%(op,tipMask,liquidClass,volstr,loc.grid,loc.pos-1,spacing,ws,cycles))
    elif op=="AspirateNC":
        wlist.append( '%s(%d,"%s",%s,%d,%d,%d,"%s",0)'%("Aspirate",tipMask,liquidClass,volstr,loc.grid,loc.pos-1,spacing,ws))
    elif op=="Detect_Liquid":
        wlist.append( '%s(%d,"%s",%d,%d,%d,"%s",0)'%(op,tipMask,liquidClass,loc.grid,loc.pos-1,spacing,ws))
    else:
        wlist.append( '%s(%d,"%s",%s,%d,%d,%d,"%s",0)'%(op,tipMask,liquidClass,volstr,loc.grid,loc.pos-1,spacing,ws))
    if op=="Aspirate":
        # Return conditioning volume
        wlist.append( '%s(%d,"%s",%s,%d,%d,%d,"%s",0)'%("Dispense",tipMask,liquidClass,condvol,loc.grid,loc.pos-1,spacing,ws))

    if op!="Detect_Liquid" and op!="Aspirate" and (loc.grid!=QPCRLOC.grid or loc.pos!=QPCRLOC.pos) and loc.grid>3 and liquidClass.name!='Air' and liquidClass.name[0:3]!='Mix' and liquidClass.name[0:7]!='Blowout':
        # Do final liquid detect (but not on qPCR plate, since that doesn't work anyway)
        wlist.append( 'Detect_Liquid(%d,"%s",%d,%d,%d,"%s",0)'%(tipMask,"Water-InLiquid",loc.grid,loc.pos-1,spacing,ws))
        clock.pipetting+=2.90    # Unsure of this one
        
    ptr=0
    for i in range(len(allvols)):
        if allvols[i]>0:
            SIM(i,op,allvols[i],loc,pos[ptr])
            ptr+=1

def getHashKey(grid,pos,well):
    if well is None or grid==3: 	# Bleach, Water, SSDDil -- each is the same regardless of the source well -- id them as 1,2,3
        key="%d,%d"%(grid,pos)
    else:
        key="%d,%d,%d"%(grid,pos,well)
    return key

def getHashCode(grid,pos,well):
    key=getHashKey(grid,pos,well)
    if key not in hashCodes:
        hashCodes[key]=crc32(key)
    return hashCodes[key]

def hashUpdate(op,tip,grid,pos,well,vol):
    key=getHashKey(grid,pos,well)
    old=getHashCode(grid,pos,well)
    #oldTip=tipHash[tip]
    if op=="Dispense":
        hashCodes[key]=crc32("%x"%tipHash[tip],old)
        hashCodes[key]=crc32("+%.1f"%vol,hashCodes[key])
    elif op=="Mix":
        hashCodes[key]=crc32("M%.1f"%vol,old)
        tipHash[tip]=crc32("Mix",tipHash[tip])
    else:
        tipHash[tip]=old
        hashCodes[key]=crc32("-%.1f"%vol,old)

    #print "hashUpdate(%s,%s,%d,%d,%d,%d,%.1f) %06x,%06x -> %06x,%06x"%(key,op,tip,grid,pos,well,vol,old&0xffffff,oldTip&0xffffff,hashCodes[key]&0xffffff,tipHash[tip]&0xffffff)


# noinspection PyUnusedLocal
def SIM(tip,op,vol,loc,pos):
    #print "SIM",tip,op,vol,loc,pos
    pass

# Get DITI
def getDITI( tipMask, volume, retry=True):
    flushQueue()
    MAXVOL10=10
    MAXVOL200=200

    assert 1 <= tipMask <= 15
    assert 0 < volume <= MAXVOL200
    if retry:
        options=1
    else:
        options=0
    if volume<=MAXVOL10:
        tiptype=DITI10
    else:
        tiptype=DITI200

    wlist.append('GetDITI(%d,%d,%d)'%(tipMask,tiptype,options))
    clock.pipetting+=2
    if tipMask&1:
        diticnt[tiptype]+=1
    if tipMask&2:
        diticnt[tiptype]+=1
    if tipMask&4:
        diticnt[tiptype]+=1
    if tipMask&8:
        diticnt[tiptype]+=1

def getDITIcnt():
    return "10ul: %d, 200ul: %d"%(diticnt[DITI10],diticnt[DITI200])

def dropDITI( tipMask, loc, airgap=10, airgapSpeed=70):
    """Drop DITI, airgap is in ul, speed in ul/sec"""
    flushQueue()
    assert 1 <= tipMask <= 15
    assert 0 <= airgap <= 100
    assert 1 <= airgapSpeed < 1000
    wlist.append('DropDITI(%d,%d,%d,%f,%d)'%(tipMask,loc.grid,loc.pos-1,airgap,airgapSpeed))
    clock.pipetting+=2

def wash( tipMask,wasteVol=1,cleanerVol=2,deepClean=False):
    """Wash tips"""
    flushQueue()
    #comment("*Wash with tips=%d, wasteVol=%d, cleanerVol=%d, deep=%s"%(tipMask,wasteVol,cleanerVol,"Y" if deepClean else "N"))
    wasteLoc=(1,1)
    if deepClean:
        cleanerLoc=(1,2)
    else:
        cleanerLoc=(1,0)
    wasteDelay=500 # in msec
    cleanerDelay=500 # in msec
    airgap=10  # ul
    airgapSpeed=20 # ul/sec
    retractSpeed=30 # mm/sec
    fastWash=1
    lowVolume=0
    atFreq=1000  # Hz, For Active tip
    wlist.append('Wash(%d,%d,%d,%d,%d,%.1f,%d,%.1f,%d,%.1f,%d,%d,%d,%d,%d)'%(tipMask,wasteLoc[0],wasteLoc[1],cleanerLoc[0],cleanerLoc[1],wasteVol,wasteDelay,cleanerVol,cleanerDelay,airgap, airgapSpeed, retractSpeed, fastWash, lowVolume, atFreq))
    #print "Wash %d,%.1fml,%.1fml,deep="%(tipMask,wasteVol,cleanerVol),deepClean
    clock.pipetting+=19.00
    if tipMask&1:
        tipHash[0]=0
    if tipMask&2:
        tipHash[1]=0
    if tipMask&4:
        tipHash[2]=0
    if tipMask&8:
        tipHash[3]=0
    #print "tipHash=[%06x,%06x,%06x,%06x]"%(tipHash[0],tipHash[1],tipHash[2],tipHash[3])

def periodicWash(tipMask,period):
    wasteLoc=(1,1)
    cleanerLoc=(1,0)
    wasteVol=1  # in ml
    wasteDelay=500 # in msec
    cleanerVol=0.5 # in ml
    cleanerDelay=500 # in msec
    airgap=10  # ul
    airgapSpeed=20 # ul/sec
    retractSpeed=30 # mm/sec
    fastWash=1
    lowVolume=0
    atFreq=1000  # Hz, For Active tip
    wlist.append('Periodic_Wash(%d,%d,%d,%d,%d,%.1f,%d,%.1f,%d,%.1f,%d,%d,%d,%d,%d,%d)'%(tipMask,wasteLoc[0],wasteLoc[1],cleanerLoc[0],cleanerLoc[1],wasteVol,wasteDelay,cleanerVol,cleanerDelay,airgap, airgapSpeed, retractSpeed, fastWash, lowVolume, period, atFreq))

def vector(vec, loc, direction, andBack, initialAction, finalAction, slow=False):
    """Move ROMA.  Gripper actions=0 (open), 1 (close), 2 (do not move)."""
    #comment("*ROMA Vector %s"%vector)
    if slow:
        speed=1
    else:
        speed=0
    if andBack:
        andBack=1
    else:
        andBack=0
    wlist.append('Vector("%s",%d,%d,%d,%d,%d,%d,%d,0)' % (vec, loc.grid, loc.pos, direction, andBack, initialAction, finalAction, speed))
    clock.pipetting+=5.16

def romahome():
    #comment("*ROMA Home")
    wlist.append('ROMA(2,0,0,0,0,0,60,0,0)')
    clock.pipetting+=2.79

def email(dest,subject,body='',profile='cdsrobot',onerror=0,attachscreen=1):
    wlist.append('Notification(%d,"%s","%s","%s","%s",%d)'%(attachscreen,profile,dest,subject,body,onerror))

def condition(varname,cond,value,dest):
    """Conditional - jump to given label (comment) if (variable cond value) is true"""
    flushQueue()
    condval=None
    if cond=='==':
        condval=0
    elif cond=='!=':
        condval=1
    elif cond=='>':
        condval=2
    elif cond=='<':
        condval=3
    else:
        logging.error("Bad condition '%s' to condition()"%cond)

    wlist.append('If("%s",%d,"%s","%s")'%(varname,condval,value,dest))

def goto(dest):
    """Unconditional goto"""
    variable('dummy',0)
    condition('dummy','==',0,dest)
        
def comment( text,prepend=False):
    if len(text) > 200:
        text=text[0:197]+"..."
    if prepend:
        wlist.insert(0,'Comment("%s")'%text)
    else:
        wlist.append('Comment("%s")'%text)

def starttimer(timer=1):
    global timerstart
    flushQueue()
    if timer<1 or timer>100:
        logging.error("starttimer: Bad timer (%d); must be between 1 and 100"%timer)

    wlist.append('StartTimer("%d")'%timer)
    timerstart=clock.pipetting

def waittimer(duration,timer=1):
    flushQueue()
    if timer<1 or timer>100:
        logging.error("waittimer: Bad timer (%d); must be between 1 and 100"%timer)

    if duration<.02 or duration >86400:
        logging.error("waittimer: Bad duration (%f); must be between 0.02 and 86400 seconds"%duration)

    wlist.append('WaitTimer("%d","%f")'%(timer,duration))
    clock.pipetting=max(clock.pipetting,timerstart+duration)	# Assume the clock.pipetting time is the timer length

def userprompt( text,timeout=-1):
    flushQueue()
    cmd='UserPrompt("%s",0,%d)'%(text,timeout)
    wlist.append(cmd)
    if timeout>0:
        clock.pipetting+=timeout


# noinspection PyShadowingNames
def variable(varname,default,userprompt=None,minval=None,maxval=None):
    if minval is not None or maxval is not None:
        limitrange=1
    else:
        limitrange=0

    if userprompt is None:
        wlist.append('Variable(%s,"%s",0," ",0,0.0,0.0)'%(varname,default))
    else:
        wlist.append('Variable(%s,"%s",1,"%s",%d,%f,%f)'%(varname,default,userprompt,limitrange,minval,maxval))


# noinspection PyShadowingNames
def stringvariable(varname,default,userprompt=None):
    if userprompt is None:
        wlist.append('String-Variable(%s,"%s",0," ")'%(varname,default))
    else:
        wlist.append('String-Variable(%s,"%s",1,"%s")'%(varname,default,userprompt))

def beginloop(loopname,n):
    global nloops
    if nloops>=100:
        logging.error('Too many loops;  Gemini can only handle 100 (%s)'%loopname)
    nloops+=1
    wlist.append('BeginLoop("%d","%s")'%(n,loopname))

def endloop():
    wlist.append('EndLoop()')
        
def execute( command, wait=True, resultvar=None):
    """Execute an external command"""
    flushQueue()
    flags=0
    if wait:
        flags=flags | 2
    if resultvar is not None and resultvar!= "":
        flags=flags | 4
    else:
        resultvar=""
    wlist.append('Execute("%s",%d,"%s")'%(command,flags,resultvar))
    clock.pipetting+=2.15   # Just overhead time, not actually time that command itself takes

def pyrun( cmd):
    label=getlabel()
    execute(r"C:\Python27\python.exe C:\cygwin\Home\Admin\%s"%cmd,resultvar="ecode")
    condition("ecode","==","0",label)
    msg='Python command %s failed with ecode=~ecode~'%cmd
    email(dest='cdsrobot@gmail.com',subject=msg)
    userprompt(msg)
    comment(label)

def getlabel():
    global lnum
    label='L%d'%lnum
    lnum=lnum+1
    return label

def testvar(var,op,value,msg=None):
    """Test if a variable pass test"""
    label=getlabel()
    condition(var,op,value,label)
    if msg is None:
        msg='Failed %s (=~%s~)%s%s'%(var,var,op,value)
    moveliha(WASHLOC)	# Get LiHa out of the way
    email(dest='cdsrobot@gmail.com',subject=msg)
    userprompt(msg)
    comment(label)

def dump():
    """Dump current worklist"""
    flushQueue()
    for i in range(len(wlist)):
        print(wlist[i])

def dumpvols():
    """Dump final volumes"""
    for loc in volumes:
        for well in volumes[loc]:
            print "%-14s\t%s\t%6.1f"%(str(loc),str(well),volumes[loc][well])

def saveworklist(filename):
    """Save worklist in a file in format that Gemini can load as a worklist"""
    flushQueue()
    fd=open(filename,'w')
    for i in range(len(wlist)):
        print >>fd, "B;%s"%string.replace(str(wlist[i]),'\n','\f\a')
    fd.close()

def savegem(headerfile,filename):
    """Save worklist in a file in format that Gemini can load as an experiment"""
    flushQueue()
    shutil.copy(headerfile,filename)
    fd=open(filename,'a')
    for i in range(len(wlist)):
        print >>fd, "%s"%string.replace(str(wlist[i]),'\n','\f\a')
    fd.close()
    # Also save another copy with line numbers, indent in a readable form in filename.gemtxt
    fd=open(filename+'txt','w')
    for i in range(len(wlist)):
        s=str(wlist[i])
        if len(s)>512:
            print("Gemini command line too long (%d>512): %s"%(len(s),s))   # Gemini definitely breaks at 522, maybe overflowing a buffer before that
            sys.exit(1)
        if s.startswith('Comment'):
            s=s[9:-2]
            if s.startswith('*'):
                s='    '+s[1:]
        else:
            s='        '+s
        print("%s" % s, file=fd)
    fd.close()

