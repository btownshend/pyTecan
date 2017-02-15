import debughook
import trobot
import sys
import logging

p=trobot.TRobot()
#logging.info( "Status=",p.getstatus())
res=p.execute(" ".join(sys.argv[1:]))
logging.info( "Result=\n<"+res+">\n")

