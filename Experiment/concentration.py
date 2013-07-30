class Concentration(object):
    def __init__(self,stock,final=1.0,units='x'):
        self.stock=stock
        self.final=final
        self.units=units
    def __str__(self):
        if self.stock==None:
            return "None"
        elif self.final==None or (self.final==1.0 and self.units=='x'):
            return "%.2f%s"%(self.stock,self.units)
        else:
            return "%.2f%s->%.2f%s"%(self.stock,self.units,self.final,self.units)
    def dilute(self,factor):
        if self.stock==None:
            return Concentration(None,None,'x')
        else:
            return Concentration(self.stock/factor,self.final,self.units)
    def dilutionneeded(self):
        'Return dilution factor needed to dilute from stock to final'
        return self.stock*1.0/self.final
