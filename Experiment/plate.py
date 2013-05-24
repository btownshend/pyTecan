"An object representing a microplate or other container on the deck"
class Plate(object):
    "A plate object which includes a name, location, and size"
    def __init__(self,name, grid, pos, nx=12, ny=8,pierce=False):
        self.name=name
        self.grid=grid
        self.pos=pos
        self.nx=nx
        self.ny=ny
        self.pierce=pierce

    def __str__(self):
        return "%s(%s,%s)"%(self.name,self.grid,self.pos)
        
