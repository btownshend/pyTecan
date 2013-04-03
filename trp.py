import worklist

REAGENTPLATE=(4,1)
SOURCEPLATE=(4,1)
SAMPLEPLATE=(4,2)
WATERLOC=(3,1)
PTCPOS=(25,1)

WASTE=(1,1)
RPTEXTRA=0.2   # Extra amount when repeat pipetting

def t7(w,reagentwells,reagentconcs,templatewells,templateconc,samplewells,volume,time):
    # Add water to sample wells as needed (multi)
    # Pipette reagents into sample wells (multi)
    # Pipette templates into sample wells
    # Concs are in x (>=1)
    assert(len(reagentwells)==len(reagentconcs))
    assert(volume>0)
    assert(time>0)
    volume=float(volume)
    nsamples=len(samplewells)
    reagentvols=[volume/x for x in reagentconcs]
    templatevol=volume/templateconc
    watervol=volume-sum(reagentvols)-templatevol
    assert(watervol>=0)
    if watervol>0:
	w.comment("Adding %.1f ul of water to each sample well"%watervol)
	v=watervol*nsamples*(1+RPTEXTRA)
	w.getDITI(1,v)
	w.aspirate([0],"Water",v,WATERLOC)
	for i in range(len(samplewells)):
	    w.dispense([samplewells[i]],"Water",watervol,SAMPLEPLATE)
	w.dropDITI(1,WASTE)

    for i in range(len(reagentwells)):
	w.comment("Adding %.1f ul of reagent %d from well %s to each sample well"%(reagentvols[i],i,reagentwells[i]))
	v=reagentvols[i]*nsamples*(1+RPTEXTRA)
	w.getDITI(1,v)

	w.aspirate([reagentwells[i]],"Water",v,REAGENTPLATE)
	for j in range(len(samplewells)):
	    w.dispense([samplewells[j]],"Water",reagentvols[i],SAMPLEPLATE)
	w.dropDITI(1,WASTE)

        v=volume/templateconc
    	for i in range(len(samplewells)):
	    w.comment( "Adding %.1f ul of template from %s to well %s"%(volume/templateconc, templatewells[i], samplewells[i]))
	    w.getDITI(1,v)
	    if len(templatewells)==1:
		w.aspirate([templatewells[0]],"Water",v,SOURCEPLATE)
	    else:
		w.aspirate([templatewells[i]],"Water",v,SOURCEPLATE)
	    w.dispense([samplewells[i]],"Water",v,SAMPLEPLATE)
	    w.mix([samplewells[i]],"Water",volume*0.9,SAMPLEPLATE,3)
	    w.dropDITI(1,WASTE)

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
