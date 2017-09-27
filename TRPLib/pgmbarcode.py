"""Barcoding"""
import logging

from Experiment import reagents, worklist, decklayout, clock
from Experiment.concentration import Concentration
from Experiment.sample import Sample
from TRPLib.QSetup import QSetup
from TRPLib.TRP import TRP

reagents.add("MPCR1", well="A1", conc=3.6,
             ingredients={'Kapa': 3, 'USER': 0.75, 'glycerol': 3.75, 'PK-ABE': 89.5, 'Water': 0})
reagents.add("MPCR2", well="B1", conc=3.85, ingredients={'Kapa': 3, 'glycerol': 3, 'PK-ABE': 89.5, 'Water': 4.5})
reagents.add("P-End", well="C1", conc=4)
reagents.add("BT5310", well="D1", conc=Concentration(20, 20, "pM"))


class Barcoding(TRP):
    """Barcode multiple samples, mix them"""

    def __init__(self, inputs):
        super(Barcoding, self).__init__()
        self.inputs = inputs

        self.qconc = 50e-12  # Target qPCR concentration
        self.qprimers = ["End"]

        self.bc1_inputvol = 4  # ul of input samples
        self.mix_conc = 100e-9  # Concentration of mixdown

        used = []
        for inp in inputs:
            bc = "%s-%s" % (inp['left'], inp['right'])
            if bc in used:
                logging.error("Barcode %s is being reused for %s" % (bc, inp['name']))
            used.append(bc)

        for x in inputs:
            if not reagents.isReagent(x['name']):
                reagents.add(x['name'], decklayout.SAMPLEPLATE, well=x['well'] if 'well' in x else None,
                             conc=Concentration(stock=x['conc'], units="nM"),
                             initVol=self.bc1_inputvol, extraVol=0)
        self.q = None  # Defined in pgm()

    def pgm(self):
        self.q = QSetup(self, maxdil=16, debug=False, mindilvol=60)
        self.e.addIdleProgram(self.q.idler)

        self.q.addReferences(dstep=10, primers=self.qprimers, ref=reagents.getsample("BT5310"))

        print "### Barcoding #### (%.0f min)" % (clock.elapsed() / 60.0)
        bcout = self.barcoding(names=[x['name'] for x in self.inputs], left=[x['left'] for x in self.inputs],
                               right=[x['right'] for x in self.inputs])

        print "### Mixdown #### (%.0f min)" % (clock.elapsed() / 60.0)
        self.mix(bcout, [x['weight'] for x in self.inputs])

        print "### qPCR #### (%.0f min)" % (clock.elapsed() / 60.0)
        self.q.run(confirm=False, enzName='EvaGreen', waitForPTC=False)
        print "### qPCR Done #### (%.0f min)" % (clock.elapsed() / 60.0)
        worklist.userprompt("qPCR done -- only need to complete final PCR", 300)
        self.e.waitpgm()
        print "### Final PCR Done #### (%.0f min)" % (clock.elapsed() / 60.0)

    def mix(self, inp, weights):
        """Mix given inputs according to weights (by moles -- use conc.stock of each input)"""
        mixvol = 100.0
        relvol = [weights[i] / inp[i].conc.stock for i in range(len(inp))]
        scale = mixvol / sum(relvol)
        minvol = min(relvol) * scale
        for i in range(len(inp)):
            if relvol[i] * scale > inp[i].volume - 16.4:
                scale = (inp[i].volume - 16.4) / relvol[i]

        if minvol < 4.0:
            logging.warning("Minimum volume into mixing is only %.2f ul" % minvol)
        vol = [x * scale for x in relvol]  # Mix to include 4ul in smallest
        if sum(vol) < mixvol:
            mixvol = max(50, sum(vol))
        watervol = mixvol - sum(vol)
        print "Mixdown: vols=[", ",".join(["%.2f " % v for v in vol]), "], water=", watervol, ", total=", mixvol, " ul"
        mixdown = Sample('mixdown', plate=decklayout.SAMPLEPLATE)

        if watervol < -0.1:
            print "Total mixdown is %.1f ul, more than planned %.0f ul" % (sum(vol), mixvol)
            assert False
        elif watervol > 0.0:
            self.e.transfer(watervol, decklayout.WATER, mixdown, (False, False))
        else:
            pass
        for i in range(len(inp)):
            inp[i].conc.final = inp[i].conc.stock * vol[i] / mixvol  # Avoid warnings about concentrations not adding up
            self.e.transfer(vol[i], inp[i], mixdown, (False, i == len(inp) - 1))
        self.e.shakeSamples([mixdown])
        mixdown.conc = Concentration(stock=sum([inp[i].conc.stock * vol[i] for i in range(len(inp))]) / mixvol,
                                     final=None, units='nM')
        print "Mixdown final concentration = %.0f nM" % mixdown.conc.stock
        self.q.addSamples(mixdown, needDil=mixdown.conc.stock * 1e-9 / self.qconc, primers=self.qprimers,nreplicates=3)
        return mixdown

    def barcoding(self, names, left, right):
        """Perform barcoding of the given inputs;  rsrsc,left,right should all be equal length"""
        pcrcycles = [4, 12]
        pcr1inputconc = 0.05  # PCR1 concentration final in reaction
        pcr1inputdil = 10
        pcr1vol = 30
        pcr1postdil = 100.0 / pcr1vol

        pcr2dil = 50
        pcr2vol = 50.0

        samps = [reagents.getsample(s) for s in names]
        print "Inputs:"
        for i in range(len(samps)):
            print "%2s %-10s %8s-%-8s  %s" % (
                samps[i].plate.wellname(samps[i].well), self.inputs[i]['name'], left[i], right[i], str(samps[i].conc))

        wellnum = 5
        for s in left + right:
            primer = "P-" + s
            if not reagents.isReagent(primer):
                reagents.add(primer, conc=Concentration(2.67, 0.4, 'uM'), extraVol=30, plate=decklayout.REAGENTPLATE,
                             well=decklayout.REAGENTPLATE.wellname(wellnum))
                wellnum += 1
        for s in samps:
            # Dilute down to desired conc
            dil = s.conc.stock / pcr1inputconc / pcr1inputdil
            if dil < 1.0:
                logging.error("Input %s requires dilution of %.2f" % (s.name, dil))
            elif dil > 1.0:
                dilvol = s.volume * dil
                if dilvol > 150.0:
                    logging.error("Dilution of input %s (%.1f ul) by %.2f would require %.1f ul" % (
                        s.name, s.volume, dil, dilvol))
                self.diluteInPlace(tgt=[s], dil=dil)
                print "Diluting %s by %.1f" % (s.name, dil)

        pcr1 = self.runPCR(src=samps, srcdil=pcr1inputdil, ncycles=pcrcycles[0], vol=pcr1vol,
                           primers=[[left[i], right[i]] for i in range(len(left))], usertime=0, fastCycling=False,
                           inPlace=False, master="MPCR1", kapa=True)

        pcr1finalconc = pcr1inputconc * 2 ** pcrcycles[0]
        print "PCR1 output concentration = %.1f nM" % pcr1finalconc

        if pcr1postdil > 1:
            pcr1finalconc /= pcr1postdil
            print "Post dilute PCR1 by %.2fx to %.3f nM " % (pcr1postdil, pcr1finalconc)
            self.diluteInPlace(tgt=pcr1, dil=pcr1postdil)

        for x in pcr1:
            x.conc = Concentration(stock=pcr1finalconc, units='nM')

        self.q.addSamples(src=pcr1, needDil=pcr1finalconc / (self.qconc * 1e9), primers=self.qprimers, save=True,
                          nreplicates=1)

        if len(pcrcycles) > 1:
            # Second PCR with 235p/236p on mixture (use at least 4ul of prior)
            pcr2 = self.runPCR(src=pcr1, srcdil=pcr2dil / pcr1postdil, vol=pcr2vol, ncycles=pcrcycles[1],
                               primers=None, fastCycling=False, master="MPCR2", kapa=True)

            pcr2finalconc = min(200, pcr1finalconc / (pcr2dil / pcr1postdil) * 2 ** pcrcycles[1])
            print "PCR2 final conc = %.1f nM" % pcr2finalconc

            for x in pcr2:
                x.conc = Concentration(stock=pcr2finalconc, units='nM')

            self.q.addSamples(src=pcr2, needDil=pcr2finalconc * 1e-9 / self.qconc, primers=self.qprimers)
            res = pcr2
        else:
            res = pcr1

        return res
