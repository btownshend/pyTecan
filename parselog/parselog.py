'Parse a GEMINI log file'
debug=False

cmds={
      'AGT':'Get a disposable tip',
      'ALO':'Activate door lock output',
      'AST':'Spash free discard tip',
      'MAX':'Position absolute slow speed for X axis',
      'MAY':'Position absolute slow speed for Y axis',
      'MAZ':'Position absolute slow speed for Z axis',
      'MDT':'Move tip, detect liquid, submerge',
      'MET':'Move tip, detect liquid, submerge (staty at Z-max on error)',
      'MRX':'Position relative slow speed for X axis',
      'MRY':'Position relative slow speed for Y axis',
      'MRY':'Position relative slow speed for Z axis',
      'MTR':'UNDOCUMENTED (?aspirate in units of 1/12 ul)',
      'PAA':'Position absolute for all axis',
      'PPA':'UNDOCUMENTED',
      'PPR':'UNDOCUMENTED',
      'PRX':'Positive relative for X axis',
      'PRY':'Positive relative for Y axis',
      'PRZ':'Positive relative for Z axis',
      'PVL':'UNDOCUMENTED',
      'RDZ':'Report diagnotic functions Z-Axis',
      'REE':'Report extended error code',
      'RPP':'UNDOCUMENTED',
      'RPX':'Report current parameter for X-axis',
      'RPY':'Report current parameter for Y-axis',
      'RPZ':'Report current parameter for Z-axis',
      'RPR':'Report current parameter for rotator-axis',
      'RTS':'Report tip status DiTi',
      'RSL':'UNDOCUMENTED',
      'SBL':'Set individual submerge for liquid search command',
      'SDL':'Set individual save detection retract distance for liquid search command',
      'SDM':'Set liquid detection mode',
      'SEP':'UNDOCUMENTED',
      'SHZ':'Set individual Z-travel height',
      'SML':'Set individual z-max for liquid search command',
      'STL':'Set individual z-start for liquid search command',
      'SPN':'UNDOCUMENTED',
      'SPP':'UNDOCUMENTED',
      'SPS':'Set pierce speed for piercing commands',
      'SSL':'Set search speed for liquid search commands',
      'SSZ':'Set slow speed for z-axis',
      'STZ':'UNDOCUMENTED',
      }
errors={1:'Initialization Error',
        2:'Invalid Command',
        3:'Invalid Operand',
        4:'Invalid Cmd Sequence',
        5:'Device no implement',
        6:'Time-out Error',
        7:'Device not initialized',
        8:'Command overflow of CU',
        15:'Command overflow of subdevice',
        # ROMA Errors (R)
        9:'Plate not fetched',
        10:'Drive no load',
        16:'Power fail circuit error',
        17:'Arm collision avoided with LiHa',
        # #M errors
        13:'No access to serial EEPROM',
        18:'Door lock 1 failed',
        19:'Door lock 2 failed',
        20:'No new device node detected',
        21:'Device node already defined'
        }
def fwparse(send,reply,error):
    if debug:
        if error:
            print "\tSEND:%s  ERROR:%s"%(send,reply)
        else:
            print "\tSEND:%s  REPLY:%s"%(send,reply)
    cmd=send.split(',')
    reply=reply.split(',')
    replydev=reply[0]
    replyecode=int(reply[1])
    reply=reply[2:]
    dev=cmd[0]
    op=cmd[1]
    args=cmd[2:]
    if len(op)>3:
        args.insert(0,op[3:])
        op=op[0:3]
    if op not in cmds:
        cmds[op]='UNKNOWN'
    print "%s %s (%s) "%(dev,op,cmds[op]),args," -> ",replyecode,reply
    if error or replyecode!=0:
        if replyecode not in errors:
            print 'Unknown error: <%s>'%replyecode
            errors[replyecode]='Unknown error'
        print "Error message: %s"%errors[replyecode]
        
import sys
if len(sys.argv)!=2:
    print "Usage: %s logfile"%sys.argv[0]
    exit(1)
fd=open(sys.argv[1],'r')
csum=fd.readline()
hdr=fd.readline()
version=fd.readline()
prevcode='?'
prevtime='?'
send=""
reply=""
error=False
while True:
    line=fd.readline()
    if len(line)==0:
        break
    line=line.rstrip('\r\n')
    if len(line)==0:
        continue
    code=line[0]
    time=line[2:9]
    cmd=line[11:]
    if debug:
        print "\tcode=%s(%d),time=%s,cmd=%s"%(code,ord(code[0]),time,cmd)
    if code[0]==' ':
        code=prevcode
    if len(time)<1 or time[0]==' ':
        time=prevtime
    prevcode=code
    prevtime=time
    if code[0]=='F':
        if cmd[0]=='>':
            if send!="":
                print "Double cmd: %s AND %s"%(send, cmd[1:])
            send=cmd[2:]
        elif cmd[0]=='-' or cmd[0]=='*':
            if reply!="":
                print "Double reply: %s AND %s"%(reply, cmd[1:])
                exit(1)
            if send=="":
                print "Missing cmd when received reply: %s"%cmd[1:]
                exit(1)
            if cmd[0]=='*':
                error=True
            reply=reply+cmd[2:]
        else:
            print "Bad cmd: %s"%cmd
            exit(1)
        if reply!="":
            fwparse(send,reply,error)
            send=''
            reply=''
            error=False
    else:
        print "%s %s"%(time,cmd)
        

    
