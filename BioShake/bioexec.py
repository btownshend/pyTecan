import bioshake
import sys
import logging

p=bioshake.BioShake()
logging.info( "Info=%s",p.info())
res=p.execute(" ".join(sys.argv[1:]))
logging.info( "Result=%s",res)

