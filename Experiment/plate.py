import math

_Plate__allplates=[]

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
        # Use data from Robot/Calibration/20150302-LiquidHeights
        if self.name=="Samples" or self.name=="Dilutions":
            self.angle=17.5*math.pi/180
            self.r1=2.77
            if self.name=="Samples":
                self.h1=10.04
                self.v0=10.8
            else:
                self.h1=9.76
                self.v0=11.9
        elif self.name=="Reagents":
            self.angle=17.5*math.pi/180
            self.h1=17.71
            self.r1=4.05
            self.v0=12.9
        elif self.name=="Eppendorfs":
            self.angle=17.5*math.pi/180
            self.h1=17.56
            self.r1=4.42
            self.v0=29.6
        elif self.name=="qPCR":
            self.angle=17.5*math.pi/180
            self.h1=10.31
            self.r1=2.65
            self.v0=7.5
        else:
            print "No liquid height equation for plate %s"%self.name

        __allplates.append(self)
        
    @classmethod
    def lookup(self,grid,pos):
        for p in __allplates:
            if p.grid==grid and p.pos==pos:
                return p
        return None
               
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
        if not hasattr(self,"angle"):
            print "No liquid height equation for plate %s"%self.name
            return None

        if self.name=="Samples" or self.name=="Dilutions":
            if volume<20 and not self.warned:
                print "%s plate liquid heights not validated for <20 ul (attempted to measure %.1f ul)"%(self.name,volume)
                self.warned=True
        elif self.name=="qPCR":
            if volume<110 and not self.warned:
                print "%s plate liquid heights not validated for <110 ul"%self.name
                self.warned=True

        h0=self.h1-self.r1/math.tan(self.angle/2);
        v1=math.pi/3*(self.h1-h0)*self.r1*self.r1-self.v0;
        if volume>=v1:
            height=(volume-v1)/(math.pi*self.r1*self.r1)+self.h1
        elif volume+self.v0<0:
            height=h0
        else:
             height=((volume+self.v0)*(3/math.pi)*((self.h1-h0)/self.r1)**2)**(1.0/3)+h0
            #        print "%s,vol=%.1f, height=%.1f"%(self.name,volume,height)
        return height

    def getliquidvolume(self,height):
        'Compute liquid volume given height above zmax in mm'
        if not hasattr(self,"angle"):
            return None
        
        h0=self.h1-self.r1/math.tan(self.angle/2);
        v1=math.pi/3*(self.h1-h0)*self.r1*self.r1-self.v0;
        if height>self.h1:
            volume=(height-self.h1)*math.pi*self.r1*self.r1+v1
        else:
            volume=(height-h0)**3*math.pi/3*(self.r1/(self.h1-h0))**2-self.v0
        #print "h0=",h0,", v1=",v1,", h=",height,", vol=",volume,", h=",self.getliquidheight(volume)
        return volume
    
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
        
