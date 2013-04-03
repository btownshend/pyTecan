import gemini

g=gemini.Gemini()
g.open()
status=g.getstatus()
print "STATUS=",status
try:
    g.setvar('testvar',4.5)
except:
    print "Failed setting variable, continuing..."
    
g.flush()
status=g.getstatus()
print "STATUS=",status
nvar=g.execute("GET_MAX_VARIABLES")
print "Num variables=",nvar
nvar=int(nvar[0])
for i in range(0,nvar):
    nm=g.execute('GET_VARIABLE_NAME;%d'%i)
    val=g.getvar(nm[0])
    print nm,"=",val
