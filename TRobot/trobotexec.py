import logging
import sys

import trobot

p=trobot.TRobot()
#logging.info( "Status=",p.getstatus())
res=p.execute(" ".join(sys.argv[1:]))
logging.info( "Result=\n<"+res+">\n")

