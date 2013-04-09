'A liquid class'

class LC(object):
    def __init__(self,name,singletag=5,multicond=0,multiexcess=0):
        self.name=name
        self.multicond=multicond
        self.multiexcess=multiexcess
        self.singletag=singletag

    def __str__(self):
        return "%s(%d,%d,%d)"%(self.name,self.singletag,self.multicond,self.multiexcess)

LCDefault = LC("Water",5,2,2)
