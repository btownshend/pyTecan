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
        
    def movetoloc(self,otherplate):
        self.grid=otherplate.grid
        self.pos=otherplate.pos
        self.unusableVolume=otherplate.unusableVolume

    def getliquidheight(self,volume):
        'Get liquid height in mm above ZMax'
        if self.name=="Samples":
            if volume>50:
                height=4.4+.049*volume
            else:
                height=6.9*volume/50
        elif self.name=="Reagents":
            h0=-10.01
            h1=16.91
            r1=4.00
            v0=21.8
            v1=math.pi/3*(h1-h0)*r1*r1-v0;
            if volume>=v1:
                height=(volume-v1)/(math.pi*r1*r1)+h1
            else:
                height=((volume+v0)*(3/math.pi)*((h1-h0)/r1)**2)**(1.0/3)+h0
            print "vol=%.1f, height=%.1f"%(volume,height)
        else:
            print "No liquid height equation for plate %s"%self.name
            assert(0)
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
        
