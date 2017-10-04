import sys
import trobot

p=trobot.TRobot()
try:
    p.cancel()
except:
    sys.exit(1)
    
