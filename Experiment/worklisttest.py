from . import decklayout
from . import worklist

#aspirate(1,"LC",[1,3,4],1,2,3,"wells")
plate1=decklayout.SAMPLEPLATE
worklist.aspirate(7,['B3','D3','E3'],"Water",[10,20,30],plate1)
worklist.aspirate(7,['B4','D4','F4'],"Water",[10,20,30],plate1)
worklist.aspirate(1,['B1'],"Water",[10],plate1)
worklist.dispense(2,['B1'],"Water",[10],plate1)
worklist.mix(2,['B1'],"Water",[10],plate1,7)
worklist.vector("ROMAVector",plate1,worklist.SAFETOEND,True,worklist.OPEN,worklist.CLOSE)
worklist.execute("python test",True,"result")
worklist.userprompt("Script done")
worklist.dump()
