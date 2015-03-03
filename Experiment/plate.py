import math

"An object representing a microplate or other container on the deck"
class Plate(object):
    "A plate object which includes a name, location, and size"
    def __init__(self,name, grid, pos, nx=12, ny=8,pierce=False,unusableVolume=5,maxVolume=200):
        self.name=name
        self.grid=grid
        self.pos=pos
        self.nx=nx
        self.ny=ny
        self.pierce=pierce
        self.unusableVolume=unusableVolume
        self.maxVolume=maxVolume
        self.warned=False
        
    def movetoloc(self,otherplate):
        self.grid=otherplate.grid
        self.pos=otherplate.pos
        self.unusableVolume=otherplate.unusableVolume

    def getliquidheight(self,volume):
        'Get liquid height in mm above ZMax'
        angle=17.5*math.pi/180;
        # Use data from Robot/Calibration/20150302-LiquidHeights
        if self.name=="Samples":
            if volume<60 and not self.warned:
                print "%s plate liquid heights not validated for <60 ul"%self.name
                self.warned=True
            r1=2.56;
            h1=9.64;
            v0=9.9;
        elif self.name=="Reagents":
            h1=16.69
            r1=3.99
            v0=14.7
        elif self.name=="qPCR":
            if volume<110 and not self.warned:
                print "%s plate liquid heights not validated for <110 ul"%self.name
                self.warned=True
            h1=10.31
            r1=2.65
            v0=7.5
        else:
            print "No liquid height equation for plate %s"%self.name
            assert(0)
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
    
    def __str__(self):
        return self.name
    #return "%s(%s,%s)"%(self.name,self.grid,self.pos)
        
