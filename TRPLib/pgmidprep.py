from __future__ import print_function

from Experiment import reagents, clock, logging
from Experiment.concentration import Concentration
from TRPLib.QSetup import QSetup
from TRPLib.TRP import TRP
from TRPLib import trplayout

reagents.add("BT5310", well="D1", conc=Concentration(20, 20, "pM"))
reagents.add("MKapa", well='A1', conc=Concentration(2.5, 1, 'x'), extraVol=30,
             ingredients={'glycerol': 1, 'Water': 39})
reagents.add("P-End", well="C1", conc=4)


class IDPrep(TRP):
    # Barcode multiple samples
    pcreff = 1.98

    def __init__(self, inputs):
        super(IDPrep, self).__init__()
        self.inputs = inputs

        self.qconc = 0.020   # Target qPCR concentration in nM
        self.qprimers = ["End"]

        self.bc1_inputvol = 2  # ul into PCR1

        used = []
        for inp in inputs:
            bc = "%s-%s" % (inp['left'], inp['right'])
            if bc in used:
                logging.error("Barcode %s is being reused for %s" % (bc, inp['name']))
            used.append(bc)

        print("used=",used)
        self.rsrc = [reagents.add("%s-%s-%s" % (inputs[i]['name'], inputs[i]['left'], inputs[i]['right']),
                                  trplayout.SAMPLEPLATE,
                                  well=inputs[i]['well'] if 'well' in inputs[i] else None,
                                  conc=Concentration(stock=inputs[i]['conc'], units="nM"),
                                  initVol=self.bc1_inputvol, extraVol=0)
                     for i in range(len(inputs))]
        self.q = None  # Defined in pgm()

    def pgm(self):
        self.q = QSetup(self, maxdil=16, debug=False, mindilvol=60)

        self.q.debug = True
        self.q.addReferences(dstep=10, primers=self.qprimers, ref=reagents.getsample("BT5310"),nreplicates=2)

        print("### Barcoding #### (%.0f min)" % (clock.elapsed() / 60.0))
        self.idbarcoding(self.rsrc, left=[x['left'] for x in self.inputs],
                                 right=[x['right'] for x in self.inputs])
        print("### qPCR #### (%.0f min)" % (clock.elapsed() / 60.0))
        self.q.run(confirm=False, enzName='EvaGreen')

    def idbarcoding(self, rsrc, left, right):
        """Perform barcoding of the given inputs;  rsrsc,left,right should all be equal length"""
        pcrcycles = [4]   # Don't need 2nd PCR since this will go directly into constriction
        #pcr1inputconc = 0.05  # PCR1 concentration final in reaction
        pcr1inputdil = 10
        pcr1vol = 30
        pcr1postdil = 100.0 / pcr1vol

        pcr2dil = 50
        pcr2minvol = 50.0

        samps = [s.getsample() for s in rsrc]
        print("Inputs:")
        for i in range(len(samps)):
            print("%2s %-10s %8s-%-8s  %.1f%s" % (
                samps[i].plate.wellname(samps[i].well), self.inputs[i]['name'], left[i], right[i], samps[i].conc.stock,samps[i].conc.units))
        # Compute pcr1inputconc such that lowest concentration input ends up with at least 30ul after dilution
        pcr1inputconc=min([s.conc.stock*s.volume/30.0/pcr1inputdil for s in samps])
        print("Diluting inputs so PCR1 final template conc = %.0f pM"%(pcr1inputconc*1000))
        wellnum = 5
        for s in left + right:
            primer = "P-" + s
            if not reagents.isReagent(primer):
                reagents.add(primer, conc=Concentration(2.67, 0.4, 'uM'), extraVol=30, plate=trplayout.REAGENTPLATE,
                             well=trplayout.REAGENTPLATE.wellname(wellnum))
                wellnum += 1
        # Run first pass dilution where needed
        for i in range(len(samps)):
            # Dilute down to desired conc
            dil = samps[i].conc.stock / pcr1inputconc / pcr1inputdil
            dilvol = samps[i].volume * dil
            if dilvol > 100.0:
                logging.notice("Dilution of input %s (%.1f ul) by %.2f would require %.1f ul" % (
                    samps[i].name, samps[i].volume, dil, dilvol))
                # Do a first pass dilution into 150ul, then remove enough so second dilution can go into 100ul
                dil1 = 100.0 / samps[i].volume
                self.diluteInPlace(tgt=[samps[i]], dil=dil1)
                print("First pass dilution of %s by %.1f/%.1f (conc now %.3f nM)" % (samps[i].name, dil1, dil, samps[i].conc.stock))
                dil /=  dil1

        # Make sure they are all mixed
        self.e.shakeSamples(samps)

        # Final dilution
        for s in samps:
            # Dilute down to desired conc
            dil = s.conc.stock / pcr1inputconc / pcr1inputdil
            if dil < 1.0:
                logging.error("Input %s requires dilution of %.2f" % (s.name, dil))
            elif dil > 1.0:
                dilvol = s.volume * dil
                if dilvol>100:
                    toremove=s.volume-100.0/dil
                    print("Removing %.1f ul from %s to allow enough room for dilution"%(toremove,s.name))
                    self.e.dispose(toremove, s)
                self.diluteInPlace(tgt=[s], dil=dil)
                print("Diluting %s by %.1f" % (s.name, dil))

        pcr1 = self.runPCR(src=samps, srcdil=pcr1inputdil, ncycles=pcrcycles[0], vol=pcr1vol,
                           primers=[[left[i], right[i]] for i in range(len(left))], usertime=0, fastCycling=False,
                           inPlace=False, master="MKapa", kapa=True)

        pcr1finalconc = pcr1inputconc * self.pcreff ** pcrcycles[0]
        print("PCR1 output concentration = %.3f nM" % pcr1finalconc)

        if pcr1postdil > 1:
            pcr1finalconc /= pcr1postdil
            print("Post dilute PCR1 by %.2fx to %.3f nM " % (pcr1postdil, pcr1finalconc))
            self.diluteInPlace(tgt=pcr1, dil=pcr1postdil)

        for x in pcr1:
            x.conc = Concentration(stock=pcr1finalconc, units='nM')

        self.q.addSamples(src=pcr1, needDil=pcr1finalconc / self.qconc, primers=self.qprimers, save=True,
                          nreplicates=1)

        if len(pcrcycles) > 1:
            # Second PCR with 235p/236p on mixture (use at least 4ul of prior)
            pcr2 = self.runPCR(src=pcr1, srcdil=pcr2dil / pcr1postdil, vol=max(pcr2minvol, pcr2dil / pcr1postdil * 4),
                               ncycles=pcrcycles[1],
                               primers="End", fastCycling=False, master="MKapa", kapa=True)

            pcr2finalconc = min(200, pcr1finalconc / (pcr2dil / pcr1postdil) * self.pcreff ** pcrcycles[1])
            print("PCR2 final conc = %.1f nM" % pcr2finalconc)

            d2 = min(4.0, 150.0 / max([p.volume for p in pcr2]))
            if d2 > 1:
                pcr2finalconc /= d2
                print("Post-dilute PCR2 by %.1fx to %.3fnM" % (d2, pcr2finalconc))
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
