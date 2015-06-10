class Concentration(object):
    def __init__(self,stock,final=1.0,units='x'):
        self.stock=stock
        self.final=final
        self.units=units

    @staticmethod
    def conctostr(conc,units):
        if conc<1 and units=='nM':
            conc=conc*1000
            units='pM'
        if conc<1 and units=='pM':
            conc=conc*1000
            units='fM'
        if conc>1000 and units=='pM':
            conc=conc/1000
            units='nM'
        return "%.3g%s"%(conc,units)

    def __str__(self):
        if self.stock==None:
            return "None"
        elif self.final==None or (self.final==1.0 and self.units=='x'):
            if self.stock==0  or self.stock >=0.1:
                return self.conctostr(self.stock,self.units)
            else:
                return self.conctostr(self.stock,self.units)
        else:
            return self.conctostr(self.stock,self.units)+"->"+self.conctostr(self.final,self.units)

    def dilute(self,factor):
        if self.stock==None:
            return Concentration(None,None,'x')
        else:
            return Concentration(self.stock/factor,self.final,self.units)
    def dilutionneeded(self):
        'Return dilution factor needed to dilute from stock to final'
        return self.stock*1.0/self.final
        
