from __future__ import print_function

import debughook

from Experiment.sample import Sample, logging
from Experiment import decklayout

# Test splitting of mixdowns
def mixsplit(vols, samps=None, avail=None, minvol=4, minmix=0, maxmix=100, nextmixnum=1, dilute=1, debug=False, plate=None, prefix="Mix"):
    """"mimix is minimum volume needed (prior to any dilution) """
    if debug:
        print("mixsplit(",vols,",avail=",avail,", minmix=",minmix,")")
    if avail is not None:
        assert(all([a>=minvol for a in avail]))
    assert(nextmixnum<10)
    if samps is None:
        assert(plate is not None)
        samps=[Sample("%sIn_%d" % (prefix,i), plate=plate) for i in range(len(vols))]
    if avail is None:
        avail=[20 for v in vols]
    sortord=sorted(range(len(vols)), key=lambda k: vols[k])
    samps=[samps[i] for i in sortord]
    vols=[vols[i] for i in sortord]
    avail=[avail[i] for i in sortord]
    vols=[v*minvol/min(vols) for v in vols]
    if sum(vols)<minmix/dilute:
        maxrescale=min([avail[i]/vols[i]*0.99 for i in range(len(vols))])
        rescale=min(maxrescale,minmix/sum(vols)/dilute)
        if rescale>1:
            if debug:
                print("Rescale by %.2f"%rescale)
            vols=[v*rescale for v in vols]

    if debug:
        print('\nMaking %s%d, sum(vol)=%.1f, Dilute=%.2f, Minmix=%.2f'%(prefix,nextmixnum,sum(vols),dilute,minmix))
        for i in range(len(samps)):
            print('%-20.20s %.2f avail=%.2f'%(samps[i].name, vols[i], avail[i]))
    if sum(vols)<=maxmix and all([vols[i]<=avail[i] for i in range(len(avail))]):
      stages=[[Sample('%s%d' % (prefix,nextmixnum),plate), samps, vols, 1]]
    else:
      for i in range(1,len(vols)):
        if sum(vols[:i+1])>maxmix or vols[i]>avail[i]:
          # Split at i-1
          if sum(vols[1:i])<vols[i]*minvol/avail[i]:
            dilute1=vols[i]/sum(vols[:i])
          else:
            dilute1=1
          minmix1=max(minvol,maxmix*sum(vols[:i])*dilute1/sum(vols))+15+1.4+3.3   # Leave enough for residual+transfer loss+mixing loss
          stages=mixsplit(vols=vols[:i], samps=samps[:i], avail=avail[:i], minvol=minvol, minmix=minmix1, maxmix=maxmix, nextmixnum=nextmixnum, dilute=dilute1, plate=plate, debug=debug, prefix=prefix)
          # Update dilute based on dilution already done
          alreadydiluted=(sum(vols[:i])*stages[-1][3]+sum(vols[i:]))/sum(vols)
          dilute/=alreadydiluted
          vv=vols[i:]
          vv.append(sum(vols[:i])*stages[-1][3])
          nn= samps[i:]
          nn.append(stages[-1][0])
          av=avail[i:]
          av.append(sum(stages[-1][2])-16.4-3.3)
          s2 = mixsplit(vols=vv, samps=nn, avail=av, minvol=minvol, minmix=minmix, maxmix=maxmix,
                        nextmixnum=nextmixnum + len(stages), plate=plate, debug=debug, prefix=prefix)
          stages.extend(s2)
          break
        
    totalvol=sum(stages[-1][2])
    if totalvol*dilute<minmix:
        logging.warning("Not making enough of %s%d (only %.1ful, minmix=%.1ful)"%(prefix,nextmixnum,totalvol*dilute,minmix))
        dilute=minmix/sum(vols)*1.5  # 1.5 is a kludge factor;  if we dilute, we need more volume upstream, but not quite dilute times more since the 15+1.4+3.3 doesn't need to be scaled
    if dilute>1:
      water=min(maxmix-totalvol,(dilute-1)*totalvol)
      if water>0:
        stages[-1][1].append(decklayout.WATER)
        stages[-1][2].append(water)
        stages[-1][3]=(totalvol+water)/totalvol  # Dilution

    if debug:
        print("stages=",stages)
    return stages
    
if __name__ == "__main__":
    tests=[[0.1,1,2,3], [ 25.950,0.762,4.966 ], [0.10940919037199125, 0.06566850538481744, 0.019387359441644048, 0.06267234895963901, 0.07314218841427735, 0.060024009603841535, 0.4215851602023609, 0.08392077878482712, 0.027609055770292656, 0.09534706331045004, 0.04519978304104141, 0.06265664160401002, 0.7345739471106759, 0.38501026694045176, 0.05521607892218214, 0.28604118993135014, 0.3139388865634157, 0.2834467120181406, 0.36460865337870685, 0.3440366972477064, 0.3830439223697651, 0.5186721991701245, 0.3647859922178988, 0.13661202185792348] ]

    cntr=1
    for t in tests:
        print("Test: ",t)
        stages=mixsplit(t,plate=decklayout.SAMPLEPLATE,minmix=20,avail=[11.625 for i in t],debug=True,prefix="Test%d_"%cntr)
        cntr+=1
        for s in stages:
            print(s[0].name,'\n =',"\n + ".join(['%4.1f: %s'%(s[2][i],s[1][i]) for i in range(len(s[1]))]))
        print()


