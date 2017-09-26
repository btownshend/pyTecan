import math

from Experiment import decklayout, reagents, clock, logging, worklist
from Experiment.concentration import Concentration
from Experiment.sample import Sample
from TRPLib.QSetup import QSetup
from TRPLib.TRP import TRP

reagents.add("BT5310", well="D1", conc=Concentration(20, 20, "pM"))
reagents.add("MKapa", well='A1', conc=Concentration(2.5, 1, 'x'), extraVol=30,
             ingredients={'glycerol': 1, 'Water': 39})
reagents.add("MConstrict", well='A6', conc=Concentration(100.0 / 98.0, 1, 'x'), extraVol=30,
             ingredients={'glycerol': 1, 'Water': 97})
reagents.add("P-End", well="C1", conc=4)


class IDPrep(TRP):
    # Barcode multiple samples, mix them, constrict, PCR, remove barcodes
    def __init__(self, inputs, nmolecules, nconstrict):
        super(IDPrep, self).__init__()
        self.inputs = inputs
        self.nmolecules = nmolecules
        self.nconstrict = nconstrict

        self.qconc = 50e-12  # Target qPCR concentration
        self.qprimers = ["End"]

        self.bc1_inputvol = 2  # ul into PCR1

        self.mix_conc = 100e-9  # Concentration of mixdown

        self.con_dilvol = 100  # Volume to use for constriction dilutions
        self.con_maxdilperstage = 100 / 3.0  # Maximum dilution/stage
        self.con_pcr1vol = 100
        self.con_pcr1inputvol = 2
        self.con_pcr1tgtconc = self.qconc * 4  # Enough to take qPCR without dilutiojn
        self.con_pcr2dil = 4
        self.con_pcr2vol = 50
        self.con_pcr2tgtconc = 100e-9

        self.regen_predilvol = 100
        self.regen_predil = 25
        self.regen_dil = 25
        self.regen_vol = 100
        self.regen_cycles = 10

        used = []
        for inp in inputs:
            bc = "%s-%s" % (inp['left'], inp['right'])
            if bc in used:
                logging.error("Barcode %s is being reused for %s" % (bc, inp['name']))
            used.append(bc)

        self.rsrc = [reagents.add("%s-%s-%s" % (inputs[i]['name'], inputs[i]['left'], inputs[i]['right']),
                                  decklayout.SAMPLEPLATE,
                                  well=inputs[i]['well'] if 'well' in inputs[i] else None,
                                  conc=Concentration(stock=inputs[i]['conc'], units="nM"),
                                  initVol=self.bc1_inputvol, extraVol=0)
                     for i in range(len(inputs))]
        self.q = None  # Defined in pgm()

    def pgm(self):
        self.q = QSetup(self, maxdil=16, debug=False, mindilvol=60)

        #  Don't start idler (to minimize tip cross-contamination); last PCR allows plenty of time for doing dilutions without any effect on run time
        # Will start after first constriction PCR is running
        self.q.debug = True
        # self.e.addIdleProgram(self.q.idler)

        self.q.addReferences(dstep=10, primers=self.qprimers, ref=reagents.getsample("BT5310"))

        print "### Barcoding #### (%.0f min)" % (clock.elapsed() / 60.0)
        bcout = self.idbarcoding(self.rsrc, left=[x['left'] for x in self.inputs],
                                 right=[x['right'] for x in self.inputs])
        print "### Mixdown #### (%.0f min)" % (clock.elapsed() / 60.0)
        mixdown = self.mix(bcout, [x['weight'] for x in self.inputs])
        print "### Constriction #### (%.1f min)" % (clock.elapsed() / 60.0)
        constricted = self.constrict(mixdown, mixdown.conc.stock * 1e-9)
        print "### Regeneration #### (%.0f min)" % (clock.elapsed() / 60.0)
        prefixes = set([x['prefix'] for x in self.inputs])
        self.regenerate(constricted * len(prefixes), [p for p in prefixes for _ in constricted])
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
        if minvol > 4.0:
            scale *= 4.0 / minvol
        elif minvol < 4.0:
            logging.warning("Minimum volume into mixing is only %.2f ul" % minvol)
        vol = [x * scale for x in relvol]  # Mix to include 4ul in smallest
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
        self.q.addSamples(mixdown, needDil=mixdown.conc.stock * 1e-9 / self.qconc, primers=self.qprimers)
        print "Mixdown final concentration = %.0f pM" % (mixdown.conc.stock * 1000)
        return mixdown

    def idbarcoding(self, rsrc, left, right):
        """Perform barcoding of the given inputs;  rsrsc,left,right should all be equal length"""
        pcrcycles = [4]
        pcr1inputconc = 0.05  # PCR1 concentration final in reaction
        pcr1inputdil = 10
        pcr1vol = 30
        pcr1postdil = 100.0 / pcr1vol

        pcr2dil = 50
        pcr2minvol = 50.0

        samps = [s.getsample() for s in rsrc]
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
                           inPlace=False, master="MKapa", kapa=True)

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
            pcr2 = self.runPCR(src=pcr1, srcdil=pcr2dil / pcr1postdil, vol=max(pcr2minvol, pcr2dil / pcr1postdil * 4),
                               ncycles=pcrcycles[1],
                               primers="End", fastCycling=False, master="MKapa", kapa=True)

            pcr2finalconc = min(200, pcr1finalconc / (pcr2dil / pcr1postdil) * 2 ** pcrcycles[1])
            print "PCR2 final conc = %.1f nM" % pcr2finalconc

            d2 = min(4.0, 150.0 / max([p.volume for p in pcr2]))
            if d2 > 1:
                pcr2finalconc /= d2
                print "Post-dilute PCR2 by %.1fx to %.3fnM" % (d2, pcr2finalconc)
                self.diluteInPlace(tgt=pcr2, dil=d2)
                self.e.shakeSamples(pcr2)

            for x in pcr2:
                x.conc = Concentration(stock=pcr2finalconc, units='nM')

            self.q.addSamples(src=pcr2, needDil=pcr2finalconc / self.qconc, primers=self.qprimers, save=True,
                              nreplicates=2)
            res = pcr2
        else:
            res = pcr1

        return res

    def constrict(self, constrictin, conc):
        """Constrict sample with concentration given by conc (in M)"""
        # noinspection PyPep8Naming
        AN = 6.022e23

        dil = conc * (self.con_pcr1inputvol * 1e-6) * AN / self.nmolecules
        nstages = int(math.ceil(math.log(dil) / math.log(self.con_maxdilperstage)))
        dilperstage = math.pow(dil, 1.0 / nstages)
        print "Diluting by %.0fx in %.0f stages of %.1f" % (dil, nstages, dilperstage)

        s = [decklayout.WATER] + [constrictin] * self.nconstrict + [decklayout.SSDDIL]
        self.e.sanitize(3, 50)  # Heavy sanitize

        for j in range(nstages):
            print "Stage ", j, ", conc=", conc
            if conc <= self.qconc * 1e-9:
                self.q.addSamples(s, needDil=1.0, primers=self.qprimers, save=False)
            s = self.runQPCRDIL(s, self.con_dilvol, dilperstage, dilPlate=True)
            conc /= dilperstage

        cycles = int(
            math.log(self.con_pcr1tgtconc / conc * self.con_pcr1vol / self.con_pcr1inputvol) / math.log(2) + 0.5)
        pcr1finalconc = conc * self.con_pcr1inputvol / self.con_pcr1vol * 2 ** cycles
        print "Running %d cycle PCR1 -> %.1f pM" % (cycles, pcr1finalconc * 1e12)
        s = s + [decklayout.WATER]  # Extra control of just water added to PCR mix
        pcr = self.runPCR(primers=None, src=s, vol=self.con_pcr1vol,
                          srcdil=self.con_pcr1vol * 1.0 / self.con_pcr1inputvol,
                          ncycles=cycles, master="MConstrict", kapa=True)
        for p in pcr:
            p.conc = Concentration(stock=pcr1finalconc * 1e9, final=pcr1finalconc / self.con_pcr2dil, units='nM')
        self.e.addIdleProgram(self.q.idler)  # Now that constriction is done, can start on qPCR setup

        needDil = max(4, pcr1finalconc / self.qconc)
        print "Running qPCR of PCR1 products using %.1fx dilution" % needDil
        self.q.addSamples(pcr, needDil=needDil, primers=self.qprimers, save=True)
        pcr = pcr[1:-2]  # Remove negative controls
        cycles2 = int(math.log(self.con_pcr2tgtconc / pcr1finalconc * self.con_pcr2dil) / math.log(2) + 0.5)
        pcr2finalconc = pcr1finalconc / self.con_pcr2dil * 2 ** cycles2

        if cycles2 > 0:
            print "Running %d cycle PCR2 -> %.1f nM" % (cycles2, pcr2finalconc * 1e9)

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
        print "Regen Predilute: %.1f nM by %.1fx to %.2f nM" % (
            inp[0].conc.stock, self.regen_predil, inp[0].conc.stock / self.regen_predil)
        d1 = self.runQPCRDIL(inp, self.regen_predilvol, self.regen_predil, dilPlate=True)
        inconc = inp[0].conc.stock / self.regen_predil / self.regen_dil
        print "Regen PCR:  %.3f nM with %d cycles -> %.1f nM" % (
            inconc, self.regen_cycles, inconc * 2 ** self.regen_cycles)
        res = self.runPCR(src=d1, srcdil=self.regen_dil, vol=self.regen_vol,
                          ncycles=self.regen_cycles,
                          primers=["T7%sX" % p for p in prefix], fastCycling=False, master="MKapa", kapa=True)
        return res
