from __future__ import print_function

import math

from ..Experiment import reagents, clock, worklist
from ..Experiment.concentration import Concentration
from ..Experiment.sample import Sample
from .QSetup import QSetup
from .TRP import TRP
from . import trplayout

reagents.add("BT5310", well="D1", conc=Concentration(20, 20, "pM"))
reagents.add("MKapa", well='A1', conc=Concentration(2.5, 1, 'x'), extraVol=30,
             ingredients={'glycerol': 1, 'Water': 39})
reagents.add("MConstrict", well='A6', conc=Concentration(100.0 / 98.0, 1, 'x'), extraVol=30,
             ingredients={'glycerol': 1, 'Water': 97})
reagents.add("P-End", well="C1", conc=4)


class Constrict(TRP):
    # Mix constriction inputs, constrict, PCR, remove barcodes
    pcreff = 1.98

    def __init__(self, inputs, nmolecules, nconstrict, vol):
        super(Constrict, self).__init__()

        self.inputs = inputs
        self.nmolecules = nmolecules
        self.nconstrict = nconstrict

        self.qconc = 20e-12  # Target qPCR concentration
        self.qprimers = ["End"]

        self.mix_conc = 100e-9  # Concentration of mixdown

        self.con_dilvol = 100  # Volume to use for constriction dilutions
        self.con_maxdilperstage = 100 / 3.0  # Maximum dilution/stage
        self.con_pcr1vol = 100
        self.con_pcr1inputvol = 2
        self.con_pcr1tgtconc = self.qconc * 4  # Enough to take qPCR without dilutiojn
        self.con_pcr2dil = 4
        self.con_pcr2vol = 50
        self.con_pcr2tgtconc = 10e-9

        self.regen_predilvol = 100
        self.regen_predil = 25
        self.regen_dil = 25
        self.regen_vol = 100
        self.regen_cycles = 10

        self.rsrc = [reagents.add("%s-%s-%s" % (inputs[i]['name'], inputs[i]['left'], inputs[i]['right']),
                                  trplayout.SAMPLEPLATE,
                                  well=inputs[i]['well'] if 'well' in inputs[i] else None,
                                  conc=Concentration(stock=inputs[i]['bconc'], units="nM"),
                                  initVol=vol, extraVol=0)
                     for i in range(len(inputs))]
        self.q = None  # Defined in pgm()

    def pgm(self):
        self.q = QSetup(self, maxdil=16, debug=False, mindilvol=60)

        #  Don't start idler (to minimize tip cross-contamination); last PCR allows plenty of time for doing dilutions without any effect on run time
        # Will start after first constriction PCR is running
        #self.q.debug = True
        # self.e.addIdleProgram(self.q.idler)

        self.q.addReferences(dstep=10, primers=self.qprimers, ref=reagents.getsample("BT5310"),nreplicates=2)

        samps=[r.getsample() for r in self.rsrc]
        for s in samps:
            self.q.addSamples([s],needDil=max(10,s.conc.stock*1e-9/self.qconc),primers=self.qprimers)
        print("### Mixdown #### (%.0f min)" % (clock.elapsed() / 60.0))
        if len(samps)>1:
            mixdown = self.mix(samps, [x['weight'] for x in self.inputs])
        else:
            mixdown=samps[0]
        self.q.addSamples(mixdown, needDil=max(1.0,mixdown.conc.stock * 1e-9 / self.qconc), primers=self.qprimers)
        print("Mixdown final concentration = %.0f pM" % (mixdown.conc.stock * 1000))
        print("### Constriction #### (%.1f min)" % (clock.elapsed() / 60.0))
        constricted = self.constrict(mixdown, mixdown.conc.stock * 1e-9)
        print("### Regeneration #### (%.0f min)" % (clock.elapsed() / 60.0))
        prefixes = set([x['left'][0] for x in self.inputs])
        self.regenerate(constricted * len(prefixes), [p for p in prefixes for _ in constricted])
        print("### qPCR #### (%.0f min)" % (clock.elapsed() / 60.0))
        self.q.run(confirm=False, enzName='EvaGreen', waitForPTC=True)
        print("### qPCR Done #### (%.0f min)" % (clock.elapsed() / 60.0))
        worklist.userprompt("qPCR done -- only need to complete final PCR", 300)
        self.e.waitpgm()
        print("### Final PCR Done #### (%.0f min)" % (clock.elapsed() / 60.0))

    def mix(self, inp, weights,mixvol=100,tgtconc=None,maxinpvol=20):
        """Mix given inputs according to weights (by moles -- use conc.stock of each input)"""
        vol = [weights[i] *1.0 / inp[i].conc.stock for i in range(len(inp))]
        scale = mixvol / sum(vol)
        conc=sum([inp[i].conc.stock * scale * vol[i] for i in range(len(inp))]) / mixvol

        if tgtconc is not None and conc>tgtconc:
            scale*=tgtconc*1.0/conc
        if max(vol)*scale<4.0:
            scale=4.1/max(vol)   # At least one input with 4ul input
        vol = [x * scale for x in vol]  # Mix to make planned total without water

        for i in range(len(vol)):
            # Check if this would require more than available of any input
            newscale= min(maxinpvol,inp[i].volume-inp[i].plate.unusableVolume()-2)/vol[i]
            if newscale<1:
                vol = [x * 1.0 * newscale for x in vol]
                if tgtconc is not None:
                    mixvol *= newscale   # Maintain same target concentration by reducing total volume
                    
        if min(vol) < 4.0:
            # Some components are too small; split mixing
            lowvol=[i for i in range(len(inp)) if vol[i]<4.0]
            highvol=[i for i in range(len(inp)) if i not in lowvol]
            assert len(highvol)>0
            assert len(lowvol)>0
            lowtgtconc=sum([inp[i].conc.stock *1.0/ weights[i] for i in highvol])/len(highvol)*sum([weights[i] for i in lowvol])
            print("Running premix of samples "+",".join(["%d"%ind for ind in lowvol])+" with target concentration of %.4f"%lowtgtconc)
            mix1=self.mix([inp[i] for i in lowvol],[weights[i] for i in lowvol],tgtconc=lowtgtconc,mixvol=mixvol,maxinpvol=maxinpvol)
            wt1=sum([weights[i] for i in lowvol])
            mix2=self.mix([inp[i] for i in highvol]+[mix1],[weights[i] for i in highvol]+[wt1],tgtconc=tgtconc,mixvol=mixvol,maxinpvol=maxinpvol)
            return mix2


        print("Mixing into %.0ful with tgtconc of %s, dil=%.2f"%(mixvol,"None" if tgtconc is None else "%.4f"%tgtconc,mixvol/sum(vol)))
        for i in range(len(inp)):
            print("%-30.30s %6.3fnM wt=%5.2f v=%5.2ful"%(inp[i].name,inp[i].conc.stock,weights[i],vol[i]))

        watervol = mixvol - sum(vol)
        #print "Mixdown: vols=[", ",".join(["%.2f " % v for v in vol]), "], water=", watervol, ", total=", mixvol, " ul"
        mixdown = Sample('mixdown', plate=trplayout.SAMPLEPLATE)

        if watervol < -0.1:
            print("Total mixdown is %.1f ul, more than planned %.0f ul" % (sum(vol), mixvol))
            assert False
        elif watervol >= 4.0:   # Omit if too small
            self.e.transfer(watervol, trplayout.WATER, mixdown, (False, False))
        else:
            pass
        ordering=sorted(list(range(len(inp))),key=lambda i: vol[i],reverse=True)
        for i in ordering:
            inp[i].conc.final = inp[i].conc.stock * vol[i] / mixvol  # Avoid warnings about concentrations not adding up
            self.e.transfer(vol[i], inp[i], mixdown, (False, False))
        self.e.shakeSamples([mixdown])
        if not mixdown.wellMixed:
            self.e.mix(mixdown)
        mixdown.conc = Concentration(stock=sum([inp[i].conc.stock * vol[i] for i in range(len(inp))]) / mixvol,
                                     final=None, units='nM')
        print("Mix product, %s, is in well %s with %.1ful @ %.2f nM"%(mixdown.name,mixdown.plate.wellname(mixdown.well),mixdown.volume,mixdown.conc.stock))
        print("----------")
        return mixdown

    def constrict(self, constrictin, conc):
        """Constrict sample with concentration given by conc (in M)"""
        # noinspection PyPep8Naming
        AN = 6.022e23

        dil = conc * (self.con_pcr1inputvol * 1e-6) * AN / self.nmolecules
        nstages = int(math.ceil(math.log(dil) / math.log(self.con_maxdilperstage)))
        dilperstage = math.pow(dil, 1.0 / nstages)
        print("Diluting by %.0fx in %.0f stages of %.1f" % (dil, nstages, dilperstage))

        s = [trplayout.WATER] + [constrictin] * self.nconstrict + [trplayout.SSDDIL]
        self.e.sanitize(3, 50)  # Heavy sanitize

        for j in range(nstages):
            print("Stage ", j, ", conc=", conc)
            if conc <= self.qconc * 1e-9:
                self.q.addSamples(s, needDil=1.0, primers=self.qprimers, save=False)
            s = self.runQPCRDIL(s, self.con_dilvol, dilperstage, dilPlate=True)
            conc /= dilperstage

        cycles = int(
            math.log(self.con_pcr1tgtconc / conc * self.con_pcr1vol / self.con_pcr1inputvol) / math.log(self.pcreff) + 0.5)
        pcr1finalconc = conc * self.con_pcr1inputvol / self.con_pcr1vol * self.pcreff ** cycles
        print("Running %d cycle PCR1 -> %.1f pM" % (cycles, pcr1finalconc * 1e12))
        s = s + [trplayout.WATER]  # Extra control of just water added to PCR mix
        pcr = self.runPCR(primers=None, src=s, vol=self.con_pcr1vol,
                          srcdil=self.con_pcr1vol * 1.0 / self.con_pcr1inputvol,
                          ncycles=cycles, master="MConstrict", kapa=True)
        for p in pcr:
            p.conc = Concentration(stock=pcr1finalconc * 1e9, final=pcr1finalconc / self.con_pcr2dil, units='nM')
        self.e.addIdleProgram(self.q.idler)  # Now that constriction is done, can start on qPCR setup

        needDil = max(4, pcr1finalconc / self.qconc)
        print("Running qPCR of PCR1 products using %.1fx dilution" % needDil)
        self.q.addSamples(pcr, needDil=needDil, primers=self.qprimers, save=True)
        pcr = pcr[1:-2]  # Remove negative controls
        cycles2 = int(math.log(self.con_pcr2tgtconc / pcr1finalconc * self.con_pcr2dil) / math.log(self.pcreff) + 0.5)
        pcr2finalconc = pcr1finalconc / self.con_pcr2dil * self.pcreff ** cycles2

        if cycles2 > 0:
            print("Running %d cycle PCR2 -> %.1f nM" % (cycles2, pcr2finalconc * 1e9))

            pcr2 = self.runPCR(primers="End", src=pcr, vol=self.con_pcr2vol, srcdil=self.con_pcr2dil,
                               ncycles=cycles2, master="MKapa", kapa=True)
            self.q.addSamples(pcr2, needDil=pcr2finalconc / self.qconc, primers=self.qprimers, save=True)
            for p in pcr2:
                p.conc = Concentration(stock=pcr2finalconc * 1e9, units='nM')
            self.e.waitpgm()
            return pcr2
        else:
            return pcr

    def regenerate(self, inp, prefix):
        """Regenerate T7 templates without barcodes with each of the given prefixes"""
        print("Regen Predilute: %.1f nM by %.1fx to %.2f nM" % (
            inp[0].conc.stock, self.regen_predil, inp[0].conc.stock / self.regen_predil))
        d1 = self.runQPCRDIL(inp, self.regen_predilvol, self.regen_predil, dilPlate=True)
        inconc = inp[0].conc.stock / self.regen_predil / self.regen_dil
        print("Regen PCR:  %.3f nM with %d cycles -> %.1f nM" % (
            inconc, self.regen_cycles, inconc * self.pcreff ** self.regen_cycles))
        res = self.runPCR(src=d1, srcdil=self.regen_dil, vol=self.regen_vol,
                          ncycles=self.regen_cycles,
                          primers=["T7%sX" % p for p in prefix], fastCycling=False, master="MKapa", kapa=True)
        return res
