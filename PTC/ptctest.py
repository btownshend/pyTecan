import logging

import ptc

p=ptc.PTC()
logging.info( "PTC Version=%s",p.version())
logging.info( "Status=%s",p.getstatus())
logging.info( "Lid status=%s",p.getlidstatus())

