"""Module for generating a worklist from a set of commands"""
from __future__ import print_function

import math
import shutil
import sys
from zlib import crc32

from . import clock
from . import logging
from .plate import Plate
from .platelocation import PlateLocation
from .decklayout import QPCRLOC,WASHLOC
from .db import db
from .sample import MIXLOSS
from .liquidclass import LCWaterInLiquid

DITI200=0
DITI10=2
OPEN=0
CLOSE=1
DONOTMOVE=2
SAFETOEND=0
ENDTOSAFE=1

postldetect=True   # True to enable automatic liquid detect after each dispense
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
    vals=[0] * (7*((nx*ny+6)//7))
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
    # 5:plate
    # 6:cycles
    # 7:id number

    # Build dependency list
    dependencies=[]
    for i in range(len(opQueue)):
        d=opQueue[i]
        dependencies.append(set())
        for j in range(i):
            dp=opQueue[j]
            if d[5].location==dp[5].location and d[2]==dp[2]: # and d[0]!=dp[0]:
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
                    print("  CHECK %s %s:\tTip %d, Loc %s Wells %s"%(d1[7],d1[0],d1[1],d1[5].location,str(d1[2])))
                    print("   WITH %s %s:\tTip %d, Loc %s Wells %s"%(d2[7],d2[0],d2[1],d2[5].location,str(d2[2])), end=' ')
                tipdiff=math.log(d2[1],2)-math.floor(math.log(d1[1],2))
                welldiff=d2[2][0]-max(d1[2])
                wellspacing=welldiff*d2[5].plateType.yspacing   # Spacing between wells in mm
                tipspacing=wellspacing/tipdiff
                if tipspacing!=9:   # Although we could have spacing up to 38, it has to be uniform if more than 2 tips are used -- hard to enforce here
                    if optimizeDebug:
                        print("  out-of-range spacing: %.1f; wellspacing=%f, ny=%d, tipdiff=%f, welldiff=%f"%(tipspacing,wellspacing,d2[5].plateType.ny,tipdiff,welldiff))
                elif d1[2][0]//d1[5].plateType.ny != d2[2][0]//d2[5].plateType.ny:
                    if optimizeDebug:
                        print("  wells in different columns of %d-row plate"%d1[5].plateType.ny)
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
            print("PRE-OPT %s:  %s:\tTip %d, Loc %s Wells %s, Vol %s, depends on %s, merges with %s"%(d[7],d[0],d[1],d[5].location,str(d[2]),d[4],dependencies[i],mergeable[i]))

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
                    assert isinstance(merge[5], Plate)
                    # noinspection PyUnresolvedReferences,PyStringFormat
                    print("MERGED %s %s:\tTip %d, Loc %s Wells %s depends on %s, merges with %s, vol=%s "%(merge[7],merge[0],merge[1],merge[5].location,str(merge[2]),dependencies[i],mergeable[i],merge[4]))

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
            print("POST-OPT %s:  %s:\tTip %d, Loc %s Wells %s"%(d[7],d[0],d[1],d[5].location,str(d[2])))

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

def detectLiquid(tipMask,wells,liquidClass,loc,allowDelay=False):
    aspirateDispense('Detect_Liquid',tipMask,wells, liquidClass, [0.0 for _ in wells], loc,allowDelay=allowDelay)

def aspirateDispense(op,tipMask,wells, liquidClass, volume, plate, cycles=None,allowDelay=True):
    """Execute or queue liquid handling operation"""
    assert isinstance(plate,Plate)
    loc=plate.location
    
    if loc.pos==0 or loc.grid>=25:
        # Attempting to use LiHa in ROMA-Only area
        logging.error("Attempt to %s to/from %s at position %s, which is in ROMA-only area not accessible to LiHa"%(op,loc.name,loc))

    liquidClass.markUsed(op)

    if type(volume)!=type([]):
        volume=[volume]*len(wells)

    if delayEnabled and allowDelay:
        opQueue.append([op,tipMask,wells,liquidClass,volume,plate,cycles])
#            comment("*Queued: %s tip=%d well=%s.%s vol=%s lc=%s"%(op,tipMask,str(loc),str(wells),str(volume),str(liquidClass)))
        return

    if op=='Mix':
        clock.pipetting+=13.22
    elif op=='Dispense':
        clock.pipetting+=3.97
    elif op=='Aspirate':
        clock.pipetting+=4.90
    elif op=='AspirateNC':
        clock.pipetting+=4.90
    elif op=='Detect_Liquid':
        clock.pipetting+=3.45

    comment("*%s tip=%d well=%s.%s vol=%s lc=%s"%(op,tipMask,str(plate),str(wells),str(volume),str(liquidClass)))
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

    # noinspection PyUnusedLocal
    spacing=1
    pos=[0] * len(wells)
    prevcol=None
    for i in range(len(wells)):
        well=wells[i]
        if isinstance(well,int):
            ival=int(well)
            (col,row)=divmod(ival,plate.plateType.ny)
            col=col+1
            row=row+1
        else:
            col=int(well[1:])
            row=ord(well[0])-ord('A')+1
        assert 1 <= row <= plate.plateType.ny and 1 <= col <= plate.plateType.nx
        pos[i]=(row-1)+plate.plateType.ny*(col-1)
        if i>0:
            assert col==prevcol
        prevcol=col

    # Build list of tip numbers used
    tips=[]
    tipTmp=tipMask
    tip=0
    while tipTmp != 0:
        while tipTmp&1 == 0:
            tipTmp=tipTmp>>1
            tip=tip+1
        tips.append(tip)
        tipTmp=tipTmp>>1
        tip+=1
        
    if len(tips) != len(wells):
        logging.error("Number of tips (mask=%d) != number of wells (%d)"%(tipMask, len(wells)))

    # Calculate spacing between tips (in # of wells)
    if len(pos)>1:
        spacing=(pos[-1]-pos[0])/(tips[-1]-tips[0])
        # Make sure spacing is uniform
        for i in range(1,len(pos)):
            assert(pos[i]-pos[0]==spacing*(tips[i]-tips[0]))
    else:
        spacing=1
        
    allvols=[0]*12
    for i in range(len(wells)):
        tip=tips[i]
        allvols[tip]=volume[i]
        if op!="Detect_Liquid":
            hashUpdate(op,tip,loc.grid,loc.pos-1,pos[i],allvols[tip])
        #comment("Hash(%d,%d,%d)=%06x"%(loc.grid,loc.pos,pos[i],getHashCode(loc.grid,loc.pos-1,pos[i])&0xffffff))

    if debug:
        print("allvols=",allvols)
        print("pos[0]=",pos[0])
        print("spacing=",spacing)

    ws=wellSelection(plate.plateType.nx,plate.plateType.ny,pos)
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
        db.wlistOp(op,getline()-1,tipMask,liquidClass,[-MIXLOSS for _ in volume],plate,pos)
    elif op=="AspirateNC":
        wlist.append( '%s(%d,"%s",%s,%d,%d,%d,"%s",0)'%("Aspirate",tipMask,liquidClass,volstr,loc.grid,loc.pos-1,spacing,ws))
        db.wlistOp("Aspirate",getline()-1,tipMask,liquidClass,[-v for v in volume],plate,pos)
    elif op=="Detect_Liquid":
        wlist.append( '%s(%d,"%s",%d,%d,%d,"%s",0)'%(op,tipMask,liquidClass,loc.grid,loc.pos-1,spacing,ws))
        db.wlistOp(op,getline()-1,tipMask,liquidClass,[0 for _ in volume],plate,pos)
    elif op=="Dispense":
        wlist.append( '%s(%d,"%s",%s,%d,%d,%d,"%s",0)'%(op,tipMask,liquidClass,volstr,loc.grid,loc.pos-1,spacing,ws))
        db.wlistOp(op,getline()-1,tipMask,liquidClass,volume,plate,pos)
    elif op=="Aspirate":
        wlist.append( '%s(%d,"%s",%s,%d,%d,%d,"%s",0)'%(op,tipMask,liquidClass,volstr,loc.grid,loc.pos-1,spacing,ws))
        db.wlistOp(op,getline()-1,tipMask,liquidClass,[-(v+2) for v in volume],plate,pos)
        # Return conditioning volume
        clock.pipetting+=3.97  # Extra for conditioning volume
        wlist.append( '%s(%d,"%s",%s,%d,%d,%d,"%s",0)'%("Dispense",tipMask,liquidClass,condvol,loc.grid,loc.pos-1,spacing,ws))
        db.wlistOp("Dispense",getline()-1,tipMask,liquidClass,[2 for _ in volume],plate,pos)
    else:
        logging.error("Bad operation: %s"%op)


    if postldetect and op!="Detect_Liquid" and op!="Aspirate" and (loc.grid!=QPCRLOC.grid or loc.pos!=QPCRLOC.pos) and loc.grid>3 and liquidClass.name!='Air' and liquidClass.name[0:3]!='Mix' and liquidClass.name[0:7]!='Blowout':
        # Do final liquid detect (but not on qPCR plate, since that doesn't work anyway)
        clock.pipetting+=3.45    # Unsure of this one
        wlist.append( 'Detect_Liquid(%d,"%s",%d,%d,%d,"%s",0)'%(tipMask,LCWaterInLiquid.name,loc.grid,loc.pos-1,spacing,ws))
        db.wlistOp("Detect_Liquid",getline()-1,tipMask,LCWaterInLiquid,[0 for _ in volume],plate,pos)

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
        hashCodes[key]=crc32(key.encode(encoding='utf8'))
    return hashCodes[key]

def hashUpdate(op,tip,grid,pos,well,vol):
    key=getHashKey(grid,pos,well)
    old=getHashCode(grid,pos,well)
    #oldTip=tipHash[tip]
    if op=="Dispense":
        hashCodes[key]=crc32(("%x"%tipHash[tip]).encode('utf8'),old)
        hashCodes[key]=crc32(("+%.1f"%vol).encode('utf8'),hashCodes[key])
    elif op=="Mix":
        hashCodes[key]=crc32(("M%.1f"%vol).encode('utf8'),old)
        tipHash[tip]=crc32("Mix".encode('utf8'), tipHash[tip])
    else:
        tipHash[tip]=old
        hashCodes[key]=crc32(("-%.1f"%vol).encode('utf8'),old)

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
    clock.pipetting+=15.87
    tip=0
    ntips=0
    tipTmp=tipMask
    while tipTmp>0:
        if tipTmp&1 != 0:
            tipHash[tip]=0
            ntips+=1
        tipTmp>>=1
        tip+=1

    #print "tipHash=[%06x,%06x,%06x,%06x]"%(tipHash[0],tipHash[1],tipHash[2],tipHash[3])
    db.wlistWash("Wash", tipMask)


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

def vector(vectorName, loc, direction, andBack, initialAction, finalAction, slow=False):
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
    if vectorName is None:
        vectorName=loc.vectorName
    wlist.append('Vector("%s",%d,%d,%d,%d,%d,%d,%d,0)' % (vectorName, loc.grid, loc.pos, direction, andBack, initialAction, finalAction, speed))
    clock.pipetting+=5.10

def romahome():
    #comment("*ROMA Home")
    wlist.append('ROMA(2,0,0,0,0,0,60,0,0)')
    clock.pipetting+=2.43

def email(dest,subject,body='',profile='cdsrobot',onerror=0,attachscreen=1):
    wlist.append('Notification(%d,"%s","%s","%s","%s",%d)'%(attachscreen,profile,dest,subject,body,onerror))

def condition(varname,cond,value,dest,flush=True):
    """Conditional - jump to given label (comment) if (variable cond value) is true"""
    if flush:
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

    if type(value)!=str:
        value="%f"%value

    wlist.append('If("%s",%d,"%s","%s")'%(varname,condval,value,dest))

def goto(dest):
    """Unconditional goto"""
    variable('dummy',0)
    condition('dummy','==',0,dest)
        
def comment(text: str):
    while len(text)>0:
        if len(text) > 200:
            line=text[0:197]+"..."
            text=text[197:]
        else:
            line=text
            text=''

        wlist.append('Comment("%s")'%line)

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

def userprompt( text,timeout=-1,flush=True):
    if flush:
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
        
def execute( command, wait=True, resultvar=None, flush=True):
    """Execute an external command"""
    if flush:
        flushQueue()
    flags=0
    if wait:
        flags=flags | 2
    if resultvar is not None and resultvar!= "":
        flags=flags | 4
    else:
        resultvar=""
    wlist.append('Execute("%s",%d,"%s")'%(command,flags,resultvar))
    clock.pipetting+=3.17   # Just overhead time, not actually time that command itself takes

def pyrun( cmd, version=3, flush=True):
    label=getlabel()
    if version==2:
        execute(r"C:\Python27\python.exe C:\cygwin\Home\Admin\%s"%cmd,resultvar="ecode",flush=flush)
    else:
        assert version==3
        execute(r"C:\Python3\python.exe C:\cygwin\Home\Admin\%s" % cmd, resultvar="ecode",flush=flush)

    condition("ecode","==","0",label,flush=flush)
    msg='Python%d command %s failed with ecode=~ecode~'%(version,cmd)
    email(dest='cdsrobot@gmail.com',subject=msg)
    userprompt(msg,flush=flush)
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
            print("%-14s\t%s\t%6.1f"%(str(loc),str(well),volumes[loc][well]))

def saveworklist(filename):
    """Save worklist in a file in format that Gemini can load as a worklist"""
    flushQueue()
    fd=open(filename,'w')
    for i in range(len(wlist)):
        print("B;%s"%(str(wlist[i]).replace('\n','\f\a')), file=fd)
    fd.close()

def savegem(headerfile,filename):
    """Save worklist in a file in format that Gemini can load as an experiment"""
    flushQueue()
    shutil.copy(headerfile,filename)
    fd=open(filename,'ab')
    for i in range(len(wlist)):
        # Worklist contains some binary data masquerading as ascii (in well position string), so need to hack the conversion to bytes
        if sys.version[0] == "2":
            b = wlist[i]    # Python 3 won't handle this as the result is a string and file write needs bytes (so requires an encode step)
        else:
            b = wlist[i].encode('latin-1')   # For some reason, python2 rejects this if any codes are >= 0x80
        fd.write(b)
        fd.write(b'\n')
        #print("%s"%(str(wlist[i]).replace('\n','\f\a')), file=fd)
    fd.close()
    # Also save another copy with line numbers, indent in a readable form in filename.gemtxt
    fd=open(filename+'txt','wb')
    for i in range(len(wlist)):
        s=wlist[i]
        if len(s)>512:
            print("Gemini command line too long (%d>512): %s"%(len(s),s))   # Gemini definitely breaks at 522, maybe overflowing a buffer before that
            sys.exit(1)
        if s.startswith('Comment'):
            s=s[9:-2]
            if s.startswith('*'):
                s='    '+s[1:]
        else:
            s='        '+s

        if sys.version[0] == "2":
            b = s
        else:
            b = s.encode('latin-1')
        fd.write(b)
        fd.write(b'\n')
        #print("%s" % s, file=fd)
    fd.close()

