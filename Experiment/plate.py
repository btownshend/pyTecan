import math

_Plate__allplates=[]

"An object representing a microplate or other container on the deck"
class Plate(object):
    "A plate object which includes a name, location, and size"
    def __init__(self,name, grid, pos, nx=12, ny=8,pierce=False,unusableVolume=5,maxVolume=200,zmax=None,angle=None,r1=None,h1=None,v0=None,vectorName=None):
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
        self.zmax=zmax
        if angle==None:
            self.angle=None
        else:
            self.angle=angle*math.pi/180
        self.r1=r1
        self.h1=h1
        self.v0=v0
        self.vectorName=vectorName		# Name of vector used for RoMa to pickup plate
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
        if self.angle==None:
            if not self.warned:
                print "No liquid height equation for plate %s"%self.name
                self.warned=True
            return None

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
        if self.angle==None:
            return None
        
        h0=self.h1-self.r1/math.tan(self.angle/2);
        v1=math.pi/3*(self.h1-h0)*self.r1*self.r1-self.v0;
        if height>self.h1:
            volume=(height-self.h1)*math.pi*self.r1*self.r1+v1
        else:
            volume=(height-h0)**3*math.pi/3*(self.r1/(self.h1-h0))**2-self.v0
        #print "h0=",h0,", v1=",v1,", h=",height,", vol=",volume,", h=",self.getliquidheight(volume)
        return volume
    
    def getmixspeeds(self,minvol,maxvol):
        'Get shaker speed range for given well volume'
        # Recommended speeds (from http://www.qinstruments.com/en/applications/optimization-of-mixing-parameters.html )
        #  10% fill:  1800-2200, 25%: 1600-2000, 50%: 1400-1800, 75%: 1200-1600
        # At 1600, 150ul is ok, but 200ul spills out
        # Based on tests run 10/12/15 on blue plates, max speed at various volumes is:
        # 200:
        # 150: 1600 RPM (shaketest2)
        # 100: 1900 RPM (shaketest3)
        #   50:            RPM (shaketest4)
        # Check volumes on plate
        # Compute max speed based on maximum fill volume
        fillvols=            [  200,  150,  100,     50,     20,       0]
        #maxspeeds=[1400,1600,1800,2000,2200,2200]  # From website assuming 200ul max volume wells
        maxspeeds=  [1400,1600,1900,2000,2200,2200]   # From experimental runs

        for i in range(len(fillvols)):
            if maxvol>=fillvols[i]:
                if i==0:
                    print "WARNING: No shaker speed data for volumes > %.0f ul"%fillvols[0]
                    maxspeed=maxspeeds[0]
                else:
                    maxspeed=(maxvol-fillvols[i-1])/(fillvols[i]-fillvols[i-1])*(maxspeeds[i]-maxspeeds[i-1])+maxspeeds[i-1]
                break

        # Theoretical minimum mixing speed
        # From: http://www.qinstruments.com/en/applications/optimization-of-mixing-parameters.html
        surftension=71.97  	# Surface tension mN/m
        welldiam=self.r1*2	# mm - use widest part for conservative estimate (smaller region will mix at lower RPM)
        density=1e-3		    # g/ul
        d0=2			 				# mixing diameter (mm)
        minspeed=60*math.sqrt(surftension*welldiam/(4*math.pi*minvol*density*d0))
        # Units will be sqrt(mN/m * mm / ul*(mg/ul)*mm) = sqrt(mN/(m*mg)) = s^-1 * 60 = min^-1
        print "mix(%.0f,%.0f) = [%.0f, %.0f]"%(minvol,maxvol,minspeed,maxspeed)
        return (minspeed,maxspeed)
    
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
        
