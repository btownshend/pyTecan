# Get status of the various parts of the thermocycler and store in Gemini using named pipes interface
import ptc
import gemini

try:
    p=ptc.PTC()
    p.open()
    g=gemini.Gemini()
    g.open()

    g.setvar('ptcstatus',p.status())
    bstat=p.blockstatus()
    g.setvar('ptcBSR',bstat[0])
    g.setvar('ptcBER',bstat[1])
    g.setvar('ptclidstatus',p.lidstatus())
except:
    print "Error in ptcgetstatus"
    exit(1)
finally:
    g.close()
    p.close()
    
exit(0)
