from ..Experiment import decklayout as dl
from ..Experiment import liquidclass
from ..Experiment.plate import Plate
from ..Experiment.sample import Sample

WATERTROUGH=Plate(name="Water",plateType=dl.TROUGH, plateLocation=dl.TROUGH2)
BLEACHTROUGH=Plate(name="Bleach",plateType=dl.TROUGH, plateLocation=dl.TROUGH3)
SSDTROUGH=Plate(name="SSDDil",plateType=dl.TROUGH, plateLocation=dl.TROUGH1)

SAMPLEPLATE=Plate(name="Samples",plateType=dl.EPPLOWBIND,plateLocation=dl.SAMPLELOC)
DILPLATE=Plate(name="Dilutions",plateType=dl.EPPLOWBIND,plateLocation=dl.DILUTIONLOC,backupPlate=SAMPLEPLATE)
EPPENDORFS=Plate(name="Eppendorfs",plateType=dl.EPPRACK,plateLocation=dl.EPPLOC)
REAGENTPLATE=Plate(name="Reagents",plateType=dl.RICBLOCK, plateLocation=dl.RICLOC)
QPCRPLATE=Plate(name="QPCR",plateType=dl.WHITEQPCR, plateLocation=dl.QPCRLOC)
PRODUCTPLATE=Plate(name="Products",plateType=dl.EPPLOWBIND,plateLocation=dl.PRODUCTLOC)


############ Well-known samples  #############
WATER=None
SSDDIL=None
BLEACH=None


def initWellKnownSamples():
    global WATER, SSDDIL, BLEACH

    WATER=Sample("Water",WATERTROUGH,-1,None,100000)
    WATER.inliquidLC=liquidclass.LCTrough    # Faster liquid detect
    SSDDIL=Sample("SSDDil",SSDTROUGH,-1,None,100000)
    SSDDIL.inliquidLC=liquidclass.LCTrough  # Faster liquid detect
    BLEACH=Sample("Bleach",BLEACHTROUGH,-1,None,100000,mixLC=liquidclass.LCBleachMix)
