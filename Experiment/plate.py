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
        
    def wellname(self,well):
        if well==None:
            return "None"
        col=int(well/self.ny)
        row=well-col*self.ny
        return "%c%d"%(chr(65+row),col+1)
    
    def __str__(self):
        return self.name
    #return "%s(%s,%s)"%(self.name,self.grid,self.pos)
        
