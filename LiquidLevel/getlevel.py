# Module to interface to RIC
from liquidlevel import LiquidLevel

x=LiquidLevel()
x.open()
val=x.getlevel()
print("got:%d"%val)
