import bioshake
import sys
import logging
import time

p=bioshake.BioShake()
#logging.info( "Info=%s",p.info())
cmd=" ".join(sys.argv[1:])
for nattempts in range(3):
    res=p.execute(cmd)
    logging.info( "Result=%s",res)
    if res=="ok":
        sys.exit(0)
    time.sleep(1)
    logging.warning("Failed attempt %d",nattempts+1)

logging.error("Failed %s",cmd)
sys.exit(1)
    
