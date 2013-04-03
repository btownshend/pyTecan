import sitecustomize
from worklist import *

REAGENT_PLATE=Location(4,1)
SOURCE_PLATE=Location(4,1)
SAMPLE_PLATE=Location(4,2)
WATERLOC=Location(3,1)
PTCPOS=Location(25,1)
LC="Water"   # Liquid class to use
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
	w.multitransfer(LC, watervol, WATERLOC, samplewells)

    w.comment("Adding %s ul of reagents from wells %s to each sample well"%(str(reagentvols),str(reagentwells)))
    for i in range(len(reagentwells)):
	w.multitransfer(LC,reagentvols[i], reagentwells[i],samplewells)

    for i in range(len(samplewells)):
	w.comment( "Adding %.1f ul of template from %s to well %s"%(volume/templateconc, templatewells[i], samplewells[i]))
	if len(templatewells)==1:
	    src=templatewells[0]
	else:
	    src=templatewells[i]
	w.transfer(LC, v, src, samplewells[i], True)

    # move to thermocycler
    w.execute("ptc200exec LID OPEN")
    w.vector("sample",SAMPLE_PLATE,w.SAFETOEND,True,w.DONOTMOVE,w.CLOSE)
    w.vector("ptc200",PTCPOS,w.SAFETOEND,True,w.DONOTMOVE,w.OPEN)
    w.execute("ptc200exec LID CLOSE")
    w.romahome()

    w.execute('ptc200exec RUN "30-15MIN"')
    w.execute('ptc200wait')

w=WorkList()
w.setWaste(WASTE)
t7(w,REAGENT_PLATE.wloc(['A1','B1']),[2,3],SOURCE_PLATE.wloc(['C1','D1','E1']),10,SAMPLE_PLATE.wloc(['A1','B1','C1']),10,30)
w.dump()


