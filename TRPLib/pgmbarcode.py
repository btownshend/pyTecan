"""Barcoding"""
import logging
import numpy as np

from Experiment import reagents, worklist, decklayout, clock
from Experiment.concentration import Concentration
from Experiment.sample import Sample
from TRPLib.QSetup import QSetup
from TRPLib.TRP import TRP
from TRPLib.mixsplit import mixsplit

reagents.add("MPCR1", well="A1", conc=30.0 / 18.0,
             ingredients={'Kapa': 3.33 / 2, 'USER': 1.67 / 2, 'glycerol': 2.5, 'Water': 95})
reagents.add("MPCR2", well="B1", conc=10.0 / 9.0, ingredients={'Kapa': 2.22 / 2, 'glycerol': 2.22 / 2, 'Water': 97.78},extraVol=100)
reagents.add("P-End", well="C1", conc=4)
reagents.add("BT5310", well="D1", conc=Concentration(20, 20, "pM"))


class Barcoding(TRP):
    """Barcode multiple samples, mix them"""

    def __init__(self, inputs, pcr1inputconc=0.05, used=None,doqpcr=True,inputPlate=decklayout.SAMPLEPLATE):
        super(Barcoding, self).__init__()
        if used is None:
            used = []
        self.inputs = inputs

        self.qconc = 50e-12  # Target qPCR concentration
        self.qprimers = ["End"]
        self.doqpcr=doqpcr
        
        self.bc1_inputvol = 4  # ul of input samples
        self.mix_conc = 100e-9  # Concentration of mixdown
        self.pcr1inputconc = pcr1inputconc

        for inp in inputs:
            bc = "%s-%s" % (inp['left'], inp['right'])
            if bc in used:
                logging.error("Barcode %s is being reused for %s" % (bc, inp['name']))
            used.append(bc)

        for x in inputs:
            if not reagents.isReagent(x['name']):
                reagents.add(x['name'], inputPlate, well=x['well'] if 'well' in x else None,
                             conc=Concentration(stock=x['conc'], units="nM"),
                             initVol=self.bc1_inputvol, extraVol=0)
            else:
                r = reagents.getsample(x['name'])
                if r.conc.stock != x['conc']:
                    logging.error('Input %s has conflicting concentrations set:  %f and %f', x['name'], r.conc.stock,
                                  x['conc'])
                    assert False

        self.q = None  # Defined in pgm()

    def pgm(self):
        self.q = QSetup(self, maxdil=16, debug=False, mindilvol=100)
        self.e.addIdleProgram(self.q.idler)

        if self.doqpcr:
            self.q.addReferences(dstep=10, primers=self.qprimers, ref=reagents.getsample("BT5310"))

        print "### Barcoding #### (%.0f min)" % (clock.elapsed() / 60.0)
        bcout = self.barcoding(names=[x['name'] for x in self.inputs], left=[x['left'] for x in self.inputs],
                               right=[x['right'] for x in self.inputs])

        for i in range(len(self.inputs)):
            x = self.inputs[i]
            if 'bconc' in x and x['bconc'] is not None:
                print "Resetting concentration of %s from expected %.1f to bconc setting of %.1f nM" % \
                      (x['name'], bcout[i].conc.stock, x['bconc'])
                bcout[i].conc.stock = x['bconc']

        print "### qPCR #### (%.0f min)" % (clock.elapsed() / 60.0)
        self.q.run(confirm=False, enzName='EvaGreen')
        print "### qPCR Done #### (%.0f min)" % (clock.elapsed() / 60.0)
        print "### Final PCR Done #### (%.0f min)" % (clock.elapsed() / 60.0)
        worklist.flushQueue()

        if all(['bconc' in x and x['bconc'] is not None for x in self.inputs]):
            print "### Mixdown #### (%.0f min)" % (clock.elapsed() / 60.0)
            worklist.flushQueue()
            worklist.comment('Start mixdown only at this point')
            self.e.sanitize(force=True)
            # mixdown = self.mix(bcout, [x['weight'] for x in self.inputs])
            # Set default mix number to 1
            for x in self.inputs:
                if 'mix' not in x:
                    x['mix']=1
            mixes=set([x['mix'] for x in self.inputs])
            for m in mixes:
                sel=[ i for i in range(len(self.inputs)) if self.inputs[i]['mix']==m] 
                print "sel=",sel
                mixdown = self.mix([bcout[i] for i in sel], [self.inputs[i]['weight'] for i in sel],prefix="Mix%d_"%m)
                mixdown.name="Mix%d_Final"%m
            # self.q.addSamples(mixdown, needDil=mixdown.conc.stock * 1e-9 / self.qconc, primers=self.qprimers,nreplicates=3)
        else:
            print "### Not doing mixdown as bconc not set in all inputs"

    def mix(self, inp, weights, tgtdil=1.0, maxusefrac=0.75, prefix="Mix"):
        """Mix given inputs according to weights (by moles -- use conc.stock of each input)"""
        print "Mix: tgtdil=%.2f, inp=" % tgtdil, ",".join(
            ["%s@%.2f" % (inp[i].name, weights[i]) for i in range(len(inp))])
        mixvol = 100.0
        relvol = [weights[i] * 1.0 / inp[i].conc.stock for i in range(len(inp))]
        stages=mixsplit(vols=relvol,samps=inp,avail=[(i.volume-15.0)*maxusefrac-1.4 for i in inp],minvol=4.0,minmix=100,maxmix=100.0,plate=decklayout.SAMPLEPLATE,debug=False,prefix=prefix)
        for s in stages:
            dest=s[0]
            moles=0
            for i in range(len(s[1])-1,-1,-1):
                src=s[1][i]
                vol=s[2][i]
                self.e.transfer(vol,src,dest,(True,False))
                if src.conc is not None:
                    moles+=src.conc.stock*vol
            newconc=moles/sum(s[2])
            print "Adjusting concentration of %s from %s to %.2f nM"%(dest.name,str(dest.conc) if dest.conc is not None else -1,newconc)
            dest.conc=Concentration(newconc,newconc,units='nM')
            print s[0].name,'\n =',"\n + ".join(['%5.1fuL %5.2f %s %s'%(s[2][i],s[1][i].conc.stock if s[1][i].conc is not None else 0,s[1][i].conc.units if s[1][i].conc is not None else "  ",s[1][i].name) for i in range(len(s[1]))]),"\n-> %5.1ful %5.2f %s %s"%(dest.volume,dest.conc.stock,dest.conc.units,dest.name)
        print
        return dest

    def oldmix(self, inp, weights, tgtdil=1.0):
        """Mix given inputs according to weights (by moles -- use conc.stock of each input)"""
        print "Mix: tgtdil=%.2f, inp=" % tgtdil, ",".join(
            ["%s@%.2f" % (inp[i].name, weights[i]) for i in range(len(inp))])
        mixvol = 100.0
        if len(inp) == 1:
            if tgtdil > 1.0:
                vol = [mixvol / tgtdil]
                if vol[0] < 4.0:
                    vol[0] = 4.0
            else:
                # Special case, just dilute 10x
                vol = [mixvol / 10]
        else:
            relvol = [weights[i] * 1.0 / inp[i].conc.stock for i in range(len(inp))]
            scale = mixvol / sum(relvol)
            for i in range(len(inp)):
                if relvol[i] * scale > inp[i].volume - 16.4:
                    scale = (inp[i].volume - 16.4) / relvol[i]
            vol = [x * scale for x in relvol]
            if min(vol) > 4.0 and tgtdil > 1.0:
                scale = max(1.0 / tgtdil, 4.0 / min(vol))
                print "Rescale volumes by %.2f to get closer to target dilution of %.2f" % (scale, tgtdil)
                vol = [x * scale for x in vol]

        print "Mix1: vols=[", ",".join(["%.3f" % v for v in vol]), "]"
        if min(vol) < 4.0:
            logging.info("Minimum volume into mixing would be only %.2f ul - staging..." % min(vol))
            if max(vol) < 4.0:
                # All volumes are low, just too much
                # Split into 2 stages
                sel = range(int(len(inp) / 2))
                nsel = range(int(len(inp) / 2), len(inp))
            else:
                # Choose a splitting threshold
                mindilution = 4.0 / min(vol)
                thresh = np.median(vol)
                while mixvol / sum([v for v in vol if v < thresh]) < mindilution:
                    thresh = thresh * 0.8
                print "Using %.2f as threshold to split mixdown" % thresh
                sel = [i for i in range(len(inp)) if vol[i] < thresh]
                nsel = [i for i in range(len(inp)) if vol[i] >= thresh]
            print "Mixing ", ",".join([inp[i].name for i in sel]), " with vols [", ",".join(
                ["%.2f" % vol[i] for i in sel]), "] in separate stage."
            tgtdil = float(np.median([vol[i] for i in nsel]) / sum([vol[i] for i in sel]))
            print "tgtdil=%.2f" % tgtdil
            mix1 = self.mix([inp[i] for i in sel], [weights[i] for i in sel], tgtdil)
            mix2 = self.mix([inp[i] for i in nsel] + [mix1],
                            [weights[i] for i in nsel] + [sum([weights[i] for i in sel])])
            return mix2
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
        print "Mixdown final concentration = %.1f nM" % mixdown.conc.stock
        return mixdown

    def barcoding(self, names, left, right):
        """Perform barcoding of the given inputs;  rsrsc,left,right should all be equal length"""
        pcrcycles = [8, 18]
        pcr1inputdil = 10
        pcr1vol = 30
        pcr1postdil = 100.0 / pcr1vol

        pcr2dil = 50
        pcr2vol = 40.0

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
            dil = s.conc.stock / self.pcr1inputconc / pcr1inputdil
            if dil < 1.0:
                logging.error("Input %s requires dilution of %.2f" % (s.name, dil))
            elif dil > 1.0:
                dilvol = s.volume * dil
                if dilvol > 150.0:
                    maxdil = 150.0 / s.volume
                    logging.info(
                        "Dilution of input %s (%.1f ul) by %.2f would require %.1f ul -- only diluting by %.1fx" % (
                            s.name, s.volume, dil, dilvol, maxdil))
                    dil = maxdil
                self.diluteInPlace(tgt=[s], dil=dil)
                print "Diluting %s by %.1f" % (s.name, dil)

        print "### PCR1 #### (%.0f min)" % (clock.elapsed() / 60.0)

        pcr1 = self.runPCR(src=samps, srcdil=[s.conc.stock / self.pcr1inputconc for s in samps], ncycles=pcrcycles[0],
                           vol=pcr1vol,
                           primers=[[left[i], right[i]] for i in range(len(left))], usertime=30, fastCycling=False,
                           inPlace=False, master="MPCR1", kapa=True, annealTemp=62)

        pcr1finalconc = self.pcr1inputconc * 2 ** pcrcycles[0]
        print "PCR1 output concentration = %.1f nM" % pcr1finalconc

        if pcr1postdil > 1:
            pcr1finalconc /= pcr1postdil
            print "Post dilute PCR1 by %.2fx to %.3f nM " % (pcr1postdil, pcr1finalconc)
            self.diluteInPlace(tgt=pcr1, dil=pcr1postdil)

        for x in pcr1:
            x.conc = Concentration(stock=pcr1finalconc, units='nM')

        if len(pcrcycles) > 1:
            # Second PCR with 235p/236p on mixture (use at least 4ul of prior)
            print "### PCR2 #### (%.0f min)" % (clock.elapsed() / 60.0)

            pcr2 = self.runPCR(src=pcr1, srcdil=pcr2dil / pcr1postdil, vol=pcr2vol, ncycles=pcrcycles[1],
                               primers=None, fastCycling=False, master="MPCR2", kapa=True, annealTemp=62)

            pcr2finalconc = pcr1finalconc / (pcr2dil / pcr1postdil) * 2 ** pcrcycles[1]
            print "PCR2 final conc = %.1f nM" % pcr2finalconc
            if pcr2finalconc > 200:
                print "Capping at 200nM"
                pcr2finalconc = 200

            for x in pcr2:
                x.conc = Concentration(stock=pcr2finalconc, units='nM')

            if self.doqpcr:
                self.q.addSamples(src=pcr2, needDil=pcr2finalconc * 1e-9 / self.qconc, primers=self.qprimers)
            res = pcr2
        else:
            self.q.addSamples(src=pcr1, needDil=pcr1finalconc / (self.qconc * 1e9), primers=self.qprimers, save=True,
                              nreplicates=1)
            res = pcr1

        return res
