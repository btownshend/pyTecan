import worklist

REAGENTPLATE=(4,1,12,8)
SOURCEPLATE=(4,1,12,8)
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

def t7(w,reagentwells,reagentconcs,templatewells,templateconc,samplewells,volume,time):
    # Add water to sample wells as needed (multi)
    # Pipette reagents into sample wells (multi)
    # Pipette templates into sample wells
    # Concs are in x (>=1)
    assert(len(reagentwells)==len(reagentconcs))
    assert(volume>0)
    assert(time>0)
    volume=float(volume)
    reagentvols=[volume/x for x in reagentconcs]
    templatevol=volume/templateconc
    watervol=volume-sum(reagentvols)-templatevol
    assert(watervol>=0)
    if watervol>0:
	w.comment("Adding %.1f ul of water to each sample well"%watervol)
        multitransfer(w,LC,watervol,WATERLOC,0,SAMPLEPLATE,samplewells)

    for i in range(len(reagentwells)):
	w.comment("Adding %.1f ul of reagent %d from well %s to each sample well"%(reagentvols[i],i,reagentwells[i]))
        multitransfer(w,LC,reagentvols[i],REAGENTPLATE,reagentwells[i],SAMPLEPLATE,samplewells)

        v=volume/templateconc
    	for i in range(len(samplewells)):
	    w.comment( "Adding %.1f ul of template from %s to well %s"%(volume/templateconc, templatewells[i], samplewells[i]))
            transfer(w,LC,volume/templateconc,SOURCEPLATE,templatewells[i],SAMPLEPLATE,samplewells[i])

    # move to thermocycler
    w.execute("ptc200exec LID OPEN")
    w.vector("sample",SAMPLEPLATE,w.SAFETOEND,True,w.DONOTMOVE,w.CLOSE)
    w.vector("ptc200",PTCPOS,w.SAFETOEND,True,w.DONOTMOVE,w.OPEN)
    w.execute("ptc200exec LID CLOSE")
    w.romahome()

    w.execute('ptc200exec RUN "30-15MIN"')
    w.execute('ptc200wait')

w=worklist.WorkList()
t7(w,['A1','A2'],[2,3],['A3','A4','A5'],10,['A1','A2','A3'],10,30)
w.dump()
