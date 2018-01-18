from Experiment.sample import Sample
from Experiment import decklayout

# Test splitting of mixdowns
def mixsplit(vols, samps=None, avail=None, minvol=4, minmix=0, maxmix=100, nextmixnum=1, dilute=1, debug=False, plate=None):
    """"mimix is minimum volume needed (prior to any dilution) """
    assert(nextmixnum<10)
    if samps is None:
        assert(plate is not None)
        samps=[Sample("S%d" % i, plate=plate) for i in range(len(vols))]
    if avail is None:
        avail=[20 for v in vols]
    sortord=sorted(range(len(vols)), key=lambda k: vols[k])
    samps=[samps[i] for i in sortord]
    vols=[vols[i] for i in sortord]
    avail=[avail[i] for i in sortord]
    vols=[v*minvol/min(vols) for v in vols]
    if sum(vols)<minmix:
        maxrescale=min([avail[i]/vols[i]*0.99 for i in range(len(vols))])
        rescale=min(maxrescale,minmix/sum(vols))
        if rescale>1:
            if debug:
                print "Rescale by %.2f"%rescale
            vols=[v*rescale for v in vols]

    if dilute>1:
      water=min(maxmix-sum(vols),(dilute-1)*sum(vols))
      if water>0:
        vols.append(water)
        samps.append(decklayout.WATER)
        avail.append(99999)
      dilute=sum(vols)/sum(vols[:-1])

    if debug:
        print 'Mix%d, sum(vol)=%.1f, Dilute=%.2f, Minmix=%.2f'%(nextmixnum,sum(vols),dilute,minmix)
        for i in range(len(samps)):
            print '%-20.20s %.2f avail=%.2f'%(samps[i].name, vols[i], avail[i])
    if sum(vols)<=maxmix and all([vols[i]<=avail[i] for i in range(len(avail))]):
      stages=[(Sample('Mix%d' % nextmixnum,plate), samps, vols, dilute)]
      return stages
    for i in range(1,len(vols)):
      if sum(vols[:i+1])>maxmix or vols[i]>avail[i]:
        # Split at i-1
        if sum(vols[1:i])<vols[i]*minvol/avail[i]:
          dilute=vols[i]/sum(vols[:i])
        else:
          dilute=1
        minmix1=max(minvol,maxmix*sum(vols[:i])/sum(vols))+16.4
        stages=mixsplit(vols=vols[:i], samps=samps[:i], avail=avail[:i], minvol=minvol, minmix=minmix1, maxmix=maxmix, nextmixnum=nextmixnum, dilute=dilute, plate=plate, debug=debug)
        vv=vols[i:]
        vv.append(sum(vols[:i])*stages[-1][3])
        nn= samps[i:]
        nn.append(stages[-1][0])
        av=avail[i:]
        av.append(sum(stages[-1][2])-16.4)
        s2 = mixsplit(vols=vv, samps=nn, avail=av, minvol=minvol, minmix=minmix, maxmix=maxmix,
                      nextmixnum=nextmixnum + len(stages), plate=plate, debug=debug)
        print "stages=",stages
        print "s2=",s2
        stages.extend(s2)
        return stages

if __name__ == "__main__":
    tests=[[0.1,1,2,3], [ 25.950,0.762,4.966 ]]
    for t in tests:
        print "Test: ",t
        stages=mixsplit(t,plate=decklayout.SAMPLEPLATE,minmix=100,debug=True)
        for s in stages:
            print s[0].name,'\n =',"\n + ".join(['%4.1f: %s'%(s[2][i],s[1][i]) for i in range(len(s[1]))])
        print


