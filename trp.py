import worklist

REAGENTPLATE=(4,1,12,8)
SAMPLEPLATE=(4,2,12,8)
WATERLOC=(3,1,1,1)
PTCPOS=(25,1,1,1)
LC="Water"

WASTE=(1,1,1,1)
RPTEXTRA=0.2   # Extra amount when repeat pipetting

def multitransfer(w, liquidClass, volume, srcplate, srcwell, destplate, destwells):
    'Multi pipette from src to multiple dest'
    v=volume*len(destwells)*(1+RPTEXTRA)
    w.getDITI(1,v)
    w.aspirate([srcwell],liquidClass,v,srcplate)
    for d in destwells:
        w.dispense([d],liquidClass,volume,destplate)
    w.dropDITI(1,WASTE)

def transfer(w, liquidClass, volume, srcplate, srcwell, destplate, destwell):
    w.getDITI(1,volume)
    w.aspirate([srcwell],LC,volume,srcplate)
    w.dispense([destwell],LC,volume,destplate)
    w.mix([destwell],LC,volume*0.9,destplate,3)
    w.dropDITI(1,WASTE)

def stage(w,reagentwells,reagentconcs,sourceplate, sourcewells,sourceconc,samplewells,volume):
    # Add water to sample wells as needed (multi)
    # Pipette reagents into sample wells (multi)
    # Pipette sources into sample wells
    # Concs are in x (>=1)
    assert(len(reagentwells)==len(reagentconcs))
    assert(volume>0)
    volume=float(volume)
    reagentvols=[volume/x for x in reagentconcs]
    sourcevol=volume/sourceconc
    watervol=volume-sum(reagentvols)-sourcevol
    assert(watervol>=0)
    if watervol>0:
	w.comment("Adding %.1f ul of water to each sample well"%watervol)
        multitransfer(w,LC,watervol,WATERLOC,0,SAMPLEPLATE,samplewells)

    for i in range(len(reagentwells)):
	w.comment("Adding %.1f ul of reagent %d from well %s to each sample well"%(reagentvols[i],i,reagentwells[i]))
        multitransfer(w,LC,reagentvols[i],REAGENTPLATE,reagentwells[i],SAMPLEPLATE,samplewells)

        v=volume/sourceconc
    	for i in range(len(samplewells)):
	    w.comment( "Adding %.1f ul of source from %s to well %s"%(volume/sourceconc, sourcewells[i], samplewells[i]))
            transfer(w,LC,volume/sourceconc,sourceplate,sourcewells[i],SAMPLEPLATE,samplewells[i])

    # move to thermocycler
    w.execute("ptc200exec LID OPEN")
    w.vector("sample",SAMPLEPLATE,w.SAFETOEND,True,w.DONOTMOVE,w.CLOSE)
    w.vector("ptc200",PTCPOS,w.SAFETOEND,True,w.DONOTMOVE,w.OPEN)
    w.execute("ptc200exec LID CLOSE")
    w.romahome()


def t7(w,reagentwells,reagentconcs,templatewells,templateconc,samplewells,volume):
    stage(w,reagentwells,reagentconcs,REAGENTPLATE, templatewells,templateconc,samplewells,volume)
    w.execute('ptc200exec RUN "30-15MIN"')
    w.execute('ptc200wait')

def rt(w,reagentwells,reagentconcs,sourcewells,sourceconc,samplewells,volume):
    stage(w,reagentwells,reagentconcs,SAMPLEPLATE, sourcewells,sourceconc,samplewells,volume)
    w.execute('ptc200exec RUN "TRP-SS"')
    w.execute('ptc200wait')


w=worklist.WorkList()
w.comment('T7')
t7(w,[0,1],[2,3],[2,3,4],10,[0,1,2],10)
w.comment('RT')
rt(w,[5],[2],[0,1,2],2,[3,4,5],5)
w.dump()
w.dumpvols()
