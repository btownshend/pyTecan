import worklist

w=worklist.WorkList()

#aspirate(1,"LC",[1,3,4],1,2,3,"wells")
plate1=(4,1)
waste=(1,1)
w.getDITI(15,1)
w.aspirate(['B3','D3','E3'],"Water",[10,20,30],plate1)
w.aspirate(['B4','D4','F4'],"Water",[10,20,30],plate1)
w.aspirate(['B1'],"Water",[10],plate1)
w.dispense(['B1'],"Water",[10],plate1)
w.mix(['B1'],"Water",[10],plate1,7)
w.dropDITI(5,waste)
w.vector("ROMAVector",plate1,w.SAFETOEND,True,w.OPEN,w.CLOSE)
w.execute("python test",True,"result")
w.userprompt("Script done")
w.dump()
