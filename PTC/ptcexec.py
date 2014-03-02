import ptc
import sys
import logging

p=ptc.PTC()
logging.info( "Status=",p.getstatus())
res=p.execute(" ".join(sys.argv[1:]))
logging.info( "Result=",res)

