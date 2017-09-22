import math

from Experiment import decklayout, reagents, clock
from Experiment.concentration import Concentration
from Experiment.sample import Sample
from TRPLib.QSetup import QSetup
from TRPLib.TRP import TRP

reagents.add("BT5310", well="D1", conc=Concentration(20, 20, "pM"))
reagents.add("MKapa", well='A1', conc=Concentration(2.5, 1, 'x'), extraVol=30,
             ingredients={'Taq': 0.5 * 1.5, 'USER': 0.5 * 1.5, 'glycerol': 0.5 * 10, 'TAQ-ABE': 95.5, 'Water': 1.5})
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
        self.bc_pcr2prodconc = 100e-9  # Estimated final concentration of PCR2
        self.bc_finalconc = None  # Filled in later

        self.mix_conc = 100e-9  # Concentration of mixdown

        self.con_dilvol = 100  # Volume to use for constriction dilutions
        self.con_maxdilperstage = 33  # Maximum dilution/stage
        self.con_pcr1vol = 100
        self.con_pcr1inputvol = 2
        self.con_pcr1tgtconc = 100e-12  # pM
        self.con_pcr2dil = 10
        self.con_pcr2vol = 50
        self.con_pcr2tgtconc = 200e-9

        self.regen_predilvol = 100
        self.regen_predil = 50
        self.regen_dil = 50
        self.regen_vol = 100
        self.regen_cycles = 12

        self.rsrc = [reagents.add("%s-%s-%s" % (inputs[i]['name'], inputs[i]['left'], inputs[i]['right']),
                                  decklayout.SAMPLEPLATE,
                                  well=inputs[i]['well'] if 'well' in inputs[i] else None,
                                  initVol=self.bc1_inputvol)
                     for i in range(len(inputs))]
        self.q = None  # Defined in pgm()

    def pgm(self):
        self.q = QSetup(self, maxdil=16, debug=False, mindilvol=60)
        self.q.addReferences(dstep=10, primers=self.qprimers, ref=reagents.getsample("BT5310"))

        print "### Barcoding #### (%.0f min)" % (clock.elapsed() / 60.0)
        bcout = self.idbarcoding(self.rsrc, left=[x['left'] for x in self.inputs],
                                 right=[x['right'] for x in self.inputs])
        print "### Mixdown #### (%.0f min)" % (clock.elapsed() / 60.0)
        mixdown = self.mix(bcout, [x['weight'] for x in self.inputs])
        print "### Constriction #### (%.1f min)" % (clock.elapsed() / 60.0)
        constricted = self.constrict(mixdown, mixdown.conc.stock * 1e-9)
        prefixes = set([x['prefix'] for x in self.inputs])
        print "### Regeneration #### (%.0f min)" % (clock.elapsed() / 60.0)
        self.regenerate(constricted * len(prefixes), [p for p in prefixes for _ in constricted])
        print "### qPCR #### (%.0f min)" % (clock.elapsed() / 60.0)
        # self.q.run(confirm=True, enzName='EvaGreen')
        print "***NOTE: Use EvaGreen, not EvaUSER for qPCR"

    def mix(self, inp, weights):
        """Mix given inputs according to weights (by moles -- use conc.stock of each input)"""
        mixvol = 100.0
        relvol = [weights[i] / inp[i].conc.stock for i in range(len(inp))]
        vol = [x * 4.0 / min(relvol) for x in relvol]  # Mix to include 4ul in smallest
        watervol = mixvol - sum(vol)
        mixdown = Sample('mixdown', plate=decklayout.SAMPLEPLATE)

        if watervol < -0.1:
            print "Total mixdown is %.1f ul, more than planned %.0f ul" % (sum(vol), mixvol)
            assert False
        elif watervol > 0.0:
            self.e.transfer(watervol, decklayout.WATER, mixdown, (False, False))
        else:
            pass
        for i in range(len(inp)):
            self.e.transfer(vol[i], inp[i], mixdown, (False, i == len(inp) - 1))
        self.e.shakeSamples([mixdown])
        mixdown.conc = Concentration(stock=sum([inp[i].conc.stock * vol[i] for i in range(len(inp))]) / mixvol,
                                     final=None, units='nM')
        print "Mixdown final concentration = %.2f nM" % mixdown.conc.stock
        return mixdown

    def idbarcoding(self, rsrc, left, right):
        """Perform barcoding of the given inputs;  rsrsc,left,right should all be equal length"""
        pcrcycles = [8, 15]
        inputdil = 10
        pcr2dil = 50
        pcr2minvol = 50.0
        qpcrdil = 10000

        samps = [s.getsample() for s in rsrc]

        wellnum = 5
        for s in left + right:
            primer = "P-" + s
            if not reagents.isReagent(primer):
                reagents.add(primer, conc=Concentration(2.67, 0.4, 'uM'), extraVol=30, plate=decklayout.REAGENTPLATE,
                             well=decklayout.REAGENTPLATE.wellname(wellnum))
                wellnum += 1
        # srcdil=[inp.conc.dilutionneeded() for inp in input]

        print "Inputs:"
        for i in range(len(samps)):
            print "%2s %-10s %8s-%-8s" % (
                samps[i].plate.wellname(samps[i].well), self.inputs[i]['name'], left[i], right[i])

        # Dilute all inputs inputdil/2
        pcr = self.runPCR(src=samps, srcdil=inputdil, ncycles=pcrcycles[0],
                          primers=[[left[i], right[i]] for i in range(len(left))], usertime=0, fastCycling=False,
                          inPlace=True, master="MKapa", kapa=True)

        # Dilute product
        pcrsrcdil2 = 1 / (1 - 1.0 / 4 - 1.0 / 4)
        d1 = min(pcr2dil / pcrsrcdil2, 150.0 / max([p.volume for p in pcr]))
        if d1 > 1:
            print "Post dilute PCR1 by %.2fx " % d1
            self.diluteInPlace(tgt=pcr, dil=d1)

        self.q.addSamples(src=pcr, needDil=qpcrdil / d1, primers=self.qprimers, save=True, nreplicates=1)

        # Second PCR with 235p/236p on mixture (use at least 4ul of prior)
        pcr2 = self.runPCR(src=pcr, srcdil=pcr2dil / d1, vol=max(pcr2minvol, pcr2dil / d1 * 4),
                           ncycles=pcrcycles[1],
                           primers="End", fastCycling=False, master="MKapa", kapa=True)

        d2 = min(4.0, 150.0 / max([p.volume for p in pcr2]))
        if d2 > 1:
            print "Post-dilute PCR2 by %.1fx" % d2
            self.diluteInPlace(tgt=pcr2, dil=d2)
            self.e.shakeSamples(pcr2)
        else:
            d2 = 1

        for x in pcr2:
            x.conc.stock = self.bc_pcr2prodconc * 1e9 / d2

        # self.q.addSamples(src=pcr2, needDil=qpcrdil / d2, primers=self.qprimers, save=False, nreplicates=2)
        print "Elapsed time for barcoding part = %d minutes" % (clock.elapsed() / 60)

        return pcr2

    def constrict(self, constrictin, conc):
        """Constrict sample with concentration given by conc (in M)"""
        # noinspection PyPep8Naming
        AN = 6.022e23

        dil = conc * (self.con_pcr1inputvol * 1e-6) * AN / self.nmolecules
        nstages = int(math.ceil(math.log(dil) / math.log(self.con_maxdilperstage)))
        dilperstage = math.pow(dil, 1.0 / nstages)
        print "Diluting by %.0fx in %.0f stages of %.1f" % (dil, nstages, dilperstage)

        s = [constrictin] * self.nconstrict + [decklayout.SSDDIL]

        self.q.addReferences(dstep=10, primers=self.qprimers, ref=reagents.getsample("BT5310"))
        qpcrdil = [x * max(1.0, conc * 1.0 / self.qconc) for x in [1, 10, 100]]

        for j in range(nstages):
            print "Stage ", j, ", qpcrdil=", qpcrdil
            for k in range(len(qpcrdil)):
                if qpcrdil[k] is not None and qpcrdil[k] < dilperstage * 2:
                    self.q.addSamples(constrictin, needDil=qpcrdil[k], primers=self.qprimers)
                    qpcrdil[k] = None

            tgt = self.runQPCRDIL(s, self.con_dilvol, dilperstage, dilPlate=True)
            qpcrdil = [x / dilperstage if x is not None else None for x in qpcrdil]
            s = tgt

        cycles = int(
            math.log(self.con_pcr1tgtconc / conc * dil * self.con_pcr1vol / self.con_pcr1inputvol) / math.log(2)) + 1
        print "Running %d cycle PCR1" % cycles
        pcr = self.runPCR(primers="End", src=s, vol=self.con_pcr1vol,
                          srcdil=self.con_pcr1vol * 1.0 / self.con_pcr1inputvol,
                          ncycles=cycles, master="MKapa", kapa=True)
        for i in range(len(pcr)):
            needDil = self.con_pcr1tgtconc / self.qconc
            print "Sample %d: dil=%f, needDil=%f" % (i, dil, needDil)
            # self.q.addSamples(pcr[i], needDil=max(2.0, needDil), primers=self.qprimers)
        cycles2 = int(math.log(self.con_pcr2tgtconc / self.con_pcr1tgtconc * self.con_pcr2dil / math.log(2))) + 1
        print "Running %d cycle PCR2" % cycles2

        if cycles2 > 0:
            pcr2 = self.runPCR(primers="End", src=pcr, vol=self.con_pcr2vol, srcdil=self.con_pcr2dil,
                               ncycles=cycles2, master="MKapa", kapa=True)
            self.e.waitpgm()
            return pcr2
        else:
            return pcr

    def regenerate(self, inp, prefix):
        """Regenerate T7 templates without barcodes with each of the given prefixes"""
        d1 = self.runQPCRDIL(inp, self.regen_predilvol, self.regen_predil, dilPlate=True)
        res = self.runPCR(src=d1, srcdil=self.regen_dil, vol=self.regen_vol,
                          ncycles=self.regen_cycles,
                          primers=["T7%sX" % p for p in prefix], fastCycling=False, master="MKapa", kapa=True)
        return res
