import inspect
import globals

def callhistory(includeLibs=False):
    h=[]
    frames=inspect.stack()
    for i in range(len(frames)-1):
        if i==0:
            continue
        f=frames[-i]
        nm=f[1].split("/")
        if includeLibs:
            h.append("%s:%d"%(nm[-1],f[2]))
        elif len(nm)==1:
            h=["%s:%d"%(nm[-1],f[2])]
    return h

def notice(msg):
    if globals.verbose:
        print "NOTICE: %s [%s]"%(msg,"->".join(callhistory()))

def warning(msg):
    print "WARNING: %s [%s]"%(msg,"->".join(callhistory(globals.verbose)))

def error(msg,fatal=True):
    print "ERROR: %s [%s]"%(msg,"->".join(callhistory(True)))
    if fatal:
        assert False



