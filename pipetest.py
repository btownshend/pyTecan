from win32file import *
from win32pipe import *
import string

debug=True

class IOException(BaseException):
    pass
class CmdError(BaseException):
    pass

errorDescs = [ 'No Error', 'Invalid command','Unexpected error','Invalid number of operands','Invalid operand','RSP error reported in answer string','RSP not initialized','ROMA-vector not defined','ROMA-vector for this site is not defined','RSP still active','RSP not active','RSP not active(11)','Cancel was pressed','Script could not be loaded/saved','Variable not defined','Advanced version of Gemini required','No rack gripped by ROMA','Device not found','Timeout','Worklist already loaded']

def execute(cmd):
    try:
        WriteFile(hPipe,cmd)
        (hr,str)=ReadFile(hPipe,1024)
    except:
        print "Error during I/O"
        raise IOException()
    if debug:
        print "cmd=%s, hr=%d, str=%s"%(cmd,hr,str)
    if str[len(str)-1]=='\0':
        str=str[0:len(str)-1]
    res=string.splitfields(string.strip(str),';')
    ecode=int(res[0])
    if ecode!=0:
        print "Error executing command <%s>: %s (%d)"%(cmd,errorDescs[ecode],ecode)
        raise CmdError(ecode)
    return res[1:]

def getvar(name):
    try:
        resp=execute('GET_VARIABLE;%s'%name)
    except CmdError, ecode:
        print "caught, ecode=",ecode
        if ecode==14:
            print "Variable not found: ",name
            return None
        else:
            print "unexpected error: %d"%ecode
            raise CmdError(ecode)
    return float(resp[0])

pipeName= "\\\\.\\pipe\\gemini"
while True:
    print "Attempting to open %s"%pipeName
    hPipe = CreateFile(pipeName, GENERIC_READ | GENERIC_WRITE,0, None,OPEN_EXISTING,0,None)
    # Break if the pipe handle is valid.
    if hPipe != INVALID_HANDLE_VALUE:
        print "CreateFile succeeded"
        break
    # Exit if an error other than ERROR_PIPE_BUSY occurs.
    if GetLastError() != ERROR_PIPE_BUSY:
        print "Could not open pipe"
        exit(-1)
    # All pipe instances are busy, so wait for 2 seconds.
    print "Waiting for pipe...",
    if  not WaitNamedPipe(pipeName, 2000):
        print "WaitNamedPipe failed"
        exit(-1)
    print "done"

# The pipe connected; change to message-read mode.
try:
    SetNamedPipeHandleState(hPipe,PIPE_READMODE_MESSAGE,None,None)
except:
    print "Error in SetNamedPipeHandleState"
    exit(-1)
print "Pipe ready"
status=execute("GET_STATUS")
print "STATUS=",status
nvar=execute("GET_MAX_VARIABLES")
print "Num variables=",nvar
nvar=int(nvar[0])
for i in range(0,nvar):
    nm=execute('GET_VARIABLE_NAME;%d'%i)
    val=getvar(nm[0])
    print nm,"=",val
    


    
    
