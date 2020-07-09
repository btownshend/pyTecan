# Handle Tecan Gemini gem file
# Loads data from beginning of gem file (CFG part)

import click

from Experiment.plate import Plate
from TRPLib import trplayout
import pprint
from Misc.carrier import Carrier


class GemFile(object):
    def __init__(self):
        self.checksum=None
        self.timestamp=None
        self.username=None
        self.layout=[]

    def print(self, verbose=False):
        print(f"Checksum: {self.checksum}, Timestamp: {self.timestamp}, User: {self.username}")
        print(f"Data999: {self.data999}")
        print(f"Resline: {self.resline}")
        for r in self.layout:
            print("---------")
            print(f"grid {r['grid']}: carrier:{r['carrier']['name']}")
            for p in r['racks']:
                print(p)
                print(f"\t{p['pos']}\t{p['name']}\t{p['rack']['name']}")
            if verbose:
                pprint.pprint(r)


    def save(self, filename):
        """Save as .gem file up to part where we put in actual program commands """
        with open(filename,"w") as fd:
            fd.write(f"{self.checksum}\r\n")
            fd.write(f"{'%-32.32s'%self.timestamp}\r\n")
            fd.write(f"{'%-128.128s'%''}\r\n")
            fd.write(f"{'%-128.128s'%self.username}\r\n")
            fd.write("--{ RES }--\r\n")
            fd.write(f"{self.resline}\r\n")
            fd.write("--{ CFG }--\r\n")
            fd.write(f"999;{';'.join(['%s'%d for d in self.data999])};\r\n")
            carrierList=[-1 if c is None else c["id"] for c in self.carriers]
            fd.write(f"14;{';'.join(['%s'%c for c in carrierList])};\r\n")
            for grid in range(len(carrierList)):
                racks=None
                for l in self.layout:
                    if l["grid"]==grid:
                        racks=l["racks"]
                if racks is not None:
                    fd.write(f"998;{len(racks)};{';'.join([r['rack']['name'] for r in racks])};\r\n")
                    fd.write(f"998;{';'.join([r['name'] for r in racks])};\r\n")
                else:
                    fd.write("998;0;\r\n")
            fd.write("--{ RPG }--\r\n")


    def load(self, filename, carrier):
        with open(filename,"r") as fd:
            self.checksum = fd.readline().strip()
            self.timestamp = fd.readline().strip()
            assert(fd.readline().strip()=="")  # Blank?
            self.username = fd.readline().strip()
            assert(fd.readline().strip()=="--{ RES }--")
            self.resline = fd.readline().strip()
            assert(fd.readline().strip()=="--{ CFG }--")

            lineno=7
            gridpos=0
            for line in fd:
                lineno+=1
                line=line.strip()
                if line=='--{ RPG }--':
                    break
                #print(f"line: {line}")
                fields=line.split(";")
                if fields[-1]=="":
                    fields=fields[:-1]
                #print(f"{fields[0]}: {fields[1]} {len(fields)-2}")
                if fields[0]=="999":
                    self.data999=fields[1:]
                elif fields[0]=="14":  # Carrier list
                    self.carriers=[carrier.getcarrier(int(f)) if int(f)!=-1 else None for f in fields[1:] ]
                elif fields[0]=="998":  # Contents of each grid pos
                    if int(fields[1])>0:
                        racks=[carrier.findrack(f) for f in fields[2:]]
                        assert(len(racks)==int(fields[1]))
                        line2=fd.readline().strip()
                        names=line2.split(';')[1:]
                        assert(all([n=='' for n in names[len(racks):]]))  # Sometime get blank names at end
                        names=names[:len(racks)]
                        self.layout.append({'grid':gridpos, 'racks':[{'pos':(i+1),'rack':r,'name':names[i]} for i,r in enumerate(racks)],'carrier':self.carriers[gridpos]})
                    gridpos += 1
                else:
                    print(f"Unknown field code {fields[0]} at line {lineno}")

    def deckcompare(self, carrier: Carrier):
        print("Compare decklayout with Carrier/GemFile")
        for plate in Plate.allPlates():
            print('\n-------------')
            print(f"Plate: {plate}, Type: {plate.plateType}, Loc: {plate.location.carrierName}")
            r = carrier.findrack(plate.plateType.name)
            c = carrier.findcarrier(plate.location.carrierName)
            print(f"\tCarrier: {c}")
            print(f"\tRack:    {r}")
            print(f"zoffset (from deck):")
            zoffset1=(2100 - plate.getzmax()) / 10.0
            print(f"\tdecklayout.py:{plate.getzmax()} -> {zoffset1}")
            coffsets = [c['refoffset'][2], c['sites'][plate.location.pos - 1]['zoffset']]
            print(f"\tcarrier:ref:{coffsets[0]},pos[{plate.location.pos}]:{coffsets[1]}", end='')
            roffset = r['zcoords']['max']
            print(f" + rack:{roffset}", end='')
            tipoffset = 39
            print(f" + tip:{tipoffset}", end='')
            print(f" -> {coffsets[0] + coffsets[1] + roffset + tipoffset}")
            if coffsets[0]+coffsets[1]+roffset+tipoffset != zoffset1:
                print(f"**** Z-Offset mismatch: carrier: {2100-10*(coffsets[0]+coffsets[1]+roffset+tipoffset)}, decklayout: {2100-10*zoffset1}")
            if r['area'] != plate.plateType.gemArea:
                print(f"**** GEM Area mismatch: carrier: {r['area']}, decklayout: {plate.plateType.gemArea}")
            if r['depth'] != plate.plateType.gemDepth:
                print(f"**** GEM Depth mismatch: carrier: {r['depth']}, decklayout: {plate.plateType.gemDepth}")
            print(f"Location:")
            print(f"\tdecklayout.py: {plate.location.grid},{plate.location.pos}")
            for l in self.layout:
                if l["grid"]==plate.location.grid:
                    for lr in l["racks"]:
                        if lr["pos"]==plate.location.pos:
                            print(f"Found gemfile entry: carrier: {l['carrier']['name']}, rack: {lr['rack']['name']}")
                            if l['carrier']!=c:
                                print("**** Carrier mismatch!")
                            if lr['rack'] != r:
                                print("**** Rack mismatch!")




@click.command()
@click.option('--filename','-f',help="File to load")
@click.option('--output','-o',help="File to write")
@click.option('--cfilename','-c',help="Carrier.cfg filename")
@click.option('--dump','-d',is_flag=True,help="Dump contents")
@click.option('--verbose', '-v', is_flag=True, help="Dump contents")
@click.option('--compare', '-C', is_flag=True, help="Compare to decklayout")
def main(filename,cfilename,compare,dump,verbose,output):
    carrier = Carrier()
    carrier.loadCFG(cfilename)
    gem = GemFile()
    gem.load(filename,carrier)
    if dump:
        gem.print(verbose)
    if compare:
        gem.deckcompare(carrier)
    if output != None:
        gem.save(output)

if __name__ == '__main__':
    main()
