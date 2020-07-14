# Handle Tecan Gemini Carriers and Racks
# Loads data from Carriers.cfg
import pprint
import os
import click

class Carrier(object):
    instance = None

    def __init__(self):
        self.checksum=None
        self.timestamp=None
        self.username=None
        self.carriers=[]
        self.racks=[]
        self.vectors=[]
        self.data999=None

    @classmethod
    def cfg(cls):
        """Singleton instance of carriers """
        if Carrier.instance is None:
            modpath=os.path.dirname(__file__)
            Carrier.instance = Carrier()
            Carrier.instance.loadCFG(modpath+"/Carrier.cfg")
        return Carrier.instance

    def findrack(self,name):
        """Locate a rack by name"""
        for r in self.racks:
            if r["name"]==name:
                return r
        print(f"Rack with name {name} not found.")
        return None

    def findcarrier(self,name):
        """Locate a carrier by name"""
        for c in self.carriers:
            if c["name"]==name:
                return c
        print(f"Carrier with name {name} not found.")
        return None

    def getcarrier(self, carrierid):
        """Locate a carrier by id"""
        for c in self.carriers:
            if c["id"]==carrierid:
                return c
        print(f"Carrier with ID {carrierid} not found.")
        return None

    def print(self):
        print(f"Checksum: {self.checksum}, Timestamp: {self.timestamp}, User: {self.username}")
        print(f"Data999: {self.data999}")
        print("Carriers:")
        for c in self.carriers:
            pprint.pprint(c)

        print("\nRacks:")
        for r in self.racks:
            pprint.pprint(r)

        print("\nVectors:")
        for c in self.vectors:
            pprint.pprint(c)


    def loadCFG(self, filename):
        with open(filename,"r") as fd:
            self.checksum = fd.readline().strip()
            self.timestamp = fd.readline().strip()
            fd.readline()  # Blank?
            self.username = fd.readline().strip()
            lineno=4
            for line in fd:
                lineno+=1
                line=line.strip()
                #print(f"line: {line}")
                fields=line.split(";")
                if fields[-1]=="":
                    fields=fields[:-1]
                #print(f"{fields[0]}: {fields[1]} {len(fields)-2}")
                if fields[0]=="999":
                    cont=[]
                    self.data999=fields[1:]
                elif fields[0]=="13":  # Carriers
                    cont=[]
                    carrier = {"name":fields[1],
                               "id":int(fields[2].split("/")[0]),
                               "barcode": int(fields[2].split("/")[1]),
                               "refoffset": [float(f)/10 for f in fields[3].split("/")],
                               "dimensions": [float(f)/10 for f in fields[4].split("/")],
                               "nsites": int(fields[5]),
                               "other":fields[7:],
                               "cont":cont}
                    carrier["romaonly"]=(carrier["barcode"]==0)
                    typecode=int(fields[6])
                    if typecode==0:
                        carrier["type"]="Standard"
                    elif typecode==2:
                        carrier["type"]="Hidden"
                    elif typecode==-3:
                        carrier["type"]="ROMA"
                    elif typecode == 13:
                        carrier["type"] = "Carousel"
                    else:
                        print(f"Unknown carrier type code: {typecode} at line {lineno}")
                        carrier["type"]=typecode
                    self.carriers.append(carrier)
                elif fields[0]=="15":  # Racks
                    cont=[]
                    assert(int(fields[2])==0)  # Unknown what it is, but always zero
                    rack = {"name":fields[1],
                            #"unk1":int(fields[2]),
                            "wells":[int(f) for f in fields[3].split("/")],
                            "wellpos":[int(f) for f in fields[4].split("/")],
                            "zcoords":{k: (2100-int(f))/10.0 for k, f in zip(['max','start','dispense','travel'], fields[5].split("/"))},
                            "area":float(fields[6]),
                            "tipsperwell":int(fields[7]),
                            "tiptouchdist":float(fields[8]),
                            "piercing":[int(f) for f in fields[9].split("/")],
                            "type":int(fields[10]),
                            "diti":{"capacity":float(fields[11]),"offset":float(fields[12])}, # TODO: int?
                            "depth":float(fields[13]),
                            "precise":{"active":int(fields[14]),"xstart":int(fields[15]),"ystart":int(fields[16]),"speed":float(fields[17])},
                            "npos": int(fields[18]),
                            "other":fields[19:],
                            "cont":cont}
                    self.racks.append(rack)
                elif fields[0]=="17":  # ROMA Vector
                    cont=[]
                    vector = {"name":fields[1],
                              "grip": {"gripdist":float(fields[2].split("/")[0])/10,
                                       "reldist": float(fields[2].split("/")[1]) / 10,
                                       "force": float(fields[2].split("/")[2]),
                                       "speed": float(fields[2].split("/")[3]) / 10},
                              "xyzspeed": float(fields[3].split("/")[0])/10,
                              "rotspeed": float(fields[3].split("/")[1])/10,
                              "nsteps": int(fields[4]),
                              "carrierid": int(fields[5]),
                              "other":fields[6:],
                              "cont":cont}
                    self.vectors.append(vector)
                elif fields[0]=="20":
                    #print(f"{fields[0]}: {fields[1]} {len(fields)-2}")
                    cont=[]
                elif fields[0]=="998":
                    cont.append([int(fn) for f in fields[1:] for fn in f.split("/") ])
                else:
                    print(f"Unknown field code {fields[0]} at line {lineno}")
        # Clean up continutation lines
        for v in self.vectors:
            assert(v["nsteps"] == len(v["cont"]))
            v["steps"]=[{"x":d[0]/10.0,"y":d[1],"z":d[2]/10.0,"r":(d[3]%10000)/10.0,"abs":d[3]>=10000} for d in v["cont"]]
            del v["cont"]
            del v["nsteps"] # Redundant
        for c in self.carriers:
            assert(c["nsites"]+1 == len(c["cont"]))
            c["sites"]=[{"shape":d[0],"xsize":d[1]/10.0,"ysize":d[2]/10.0,"xoffset":d[3]/10.0,"yoffset":d[4]/10.0,"zoffset":d[5]/10.0} for d in c["cont"][:-1]]
            c["cont"]=c["cont"][-1]   # Unsure what this last line is for
            del c["nsites"]
        for r in self.racks:
            assert(r["npos"] == len(r["cont"]))
            r["allowed"]=[{"carrier":d[0],"positions":[p+1 for p in range(10) if d[1]&(1<<p)]} for d in r["cont"]]
            if r["npos"]>0:
                r["unk"]=r["cont"][-1][2]
            del r["npos"]
            del r["cont"]


@click.command()
@click.option('--filename','-f',help="File to load")
@click.option('--dump','-d',is_flag=True,help="Dump contents")
def main(filename,dump):
    carrier = Carrier()
    carrier.loadCFG(filename)
    if dump:
        carrier.print()

if __name__ == '__main__':
    main()
