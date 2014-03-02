import ptc
import time
import logging

p=ptc.PTC()
logging.info( "PTC Version=%s",p.version())
logging.info( "Status=%s",p.getstatus())
logging.info( "Lid status=%s",p.getlidstatus())

