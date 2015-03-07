class Concentration(object):
    def __init__(self,stock,final=1.0,units='x'):
        self.stock=stock
        self.final=final
        self.units=units
    def __str__(self):
        if self.stock==None:
            return "None"
        elif self.final==None or (self.final==1.0 and self.units=='x'):
            if self.stock==0  or self.stock >=0.1:
                return "%.2f%s"%(self.stock,self.units)
            else:
                return "%.2g%s"%(self.stock,self.units)
        else:
            if (self.stock==0  or self.stock >=0.1) and (self.final==0 or self.final>=0.1):
                return "%.2f%s->%.2f%s"%(self.stock,self.units,self.final,self.units)
            else:
                return "%.2g%s->%.2g%s"%(self.stock,self.units,self.final,self.units)
    def dilute(self,factor):
        if self.stock==None:
            return Concentration(None,None,'x')
        else:
            return Concentration(self.stock/factor,self.final,self.units)
    def dilutionneeded(self):
        'Return dilution factor needed to dilute from stock to final'
        return self.stock*1.0/self.final
