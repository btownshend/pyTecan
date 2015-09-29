import math

"An object representing a microplate or other container on the deck"
class Plate(object):
    "A plate object which includes a name, location, and size"
    def __init__(self,name, grid, pos, nx=12, ny=8,pierce=False,unusableVolume=5,maxVolume=200):
        self.name=name
        self.grid=grid
        self.pos=pos
        self.unusableVolume=unusableVolume
        self.homegrid=grid
        self.homepos=pos
        self.homeUnusableVolume=unusableVolume
        self.nx=nx
        self.ny=ny
        self.pierce=pierce
        self.maxVolume=maxVolume
        self.warned=False
        self.curloc="Home"

    def movetoloc(self,dest,newloc=None):
        self.curloc=dest
        if  dest=="Home":
            self.grid=self.homegrid
            self.pos=self.homepos
            self.unusableVolume=self.homeUnusableVolume
        else:
            assert(newloc!=None)
            self.grid=newloc.grid
            self.pos=newloc.pos
            self.unusableVolume=newloc.unusableVolume
            
    def getliquidheight(self,volume):
        'Get liquid height in mm above ZMax'
        angle=17.5*math.pi/180;
        # Use data from Robot/Calibration/20150302-LiquidHeights
        if self.name=="Samples" or self.name=="Dilutions":
            if volume<20 and not self.warned:
                print "%s plate liquid heights not validated for <20 ul (attempted to measure %.1f ul)"%(self.name,volume)
                self.warned=True
            r1=2.77
            if self.name=="Samples":
                h1=10.04
                v0=10.8
            else:
                h1=9.76
                v0=11.9
        elif self.name=="Reagents":
            h1=17.71
            r1=4.05
            v0=12.9
        elif self.name=="Eppendorfs":
            h1=17.56
            r1=4.42
            v0=29.6
        elif self.name=="qPCR":
            if volume<110 and not self.warned:
                print "%s plate liquid heights not validated for <110 ul"%self.name
                self.warned=True
            h1=10.31
            r1=2.65
            v0=7.5
        else:
            print "No liquid height equation for plate %s"%self.name
            return None

        h0=h1-r1/math.tan(angle/2);
        v1=math.pi/3*(h1-h0)*r1*r1-v0;
        if volume>=v1:
            height=(volume-v1)/(math.pi*r1*r1)+h1
        else:
            height=((volume+v0)*(3/math.pi)*((h1-h0)/r1)**2)**(1.0/3)+h0
            #        print "%s,vol=%.1f, height=%.1f"%(self.name,volume,height)
        return height
    
    def wellname(self,well):
        if well==None:
            return "None"
        col=int(well/self.ny)
        row=well-col*self.ny
        return "%c%d"%(chr(65+row),col+1)

    def wellnumber(self,wellname):
        'Convert a wellname, such as "A3" to a well index -- inverse of wellname()'
        for i in range(self.nx*self.ny):
            if self.wellname(i)==wellname:
                return i
        print "Illegal well name, %s, for plate %s"%(wellname, self.name)
        assert(False)
    
    def __str__(self):
        return self.name
    #return "%s(%s,%s)"%(self.name,self.grid,self.pos)
        
