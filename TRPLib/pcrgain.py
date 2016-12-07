def pcrgain(tconc,pconc,cycles):
    gain=1
    for i in range(cycles-1):		# First cycle just makes double-stranded
        duplex=min(pconc/2,pconc/(tconc+pconc)*tconc)   # Rough estimate of how much template:primer duplex will form
        #print "tconc=%.1f, pconc=%.1f, duplex=%.1f"%(tconc,pconc,duplex)
        gain*=(1+duplex/tconc)
        tconc+=duplex
        pconc-=duplex
    return gain
