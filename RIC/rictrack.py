import sys
sys.path.append("../elitech_datareader") 
import elitech
from elitech.msg import WorkStatus
import datetime
import ric
import math
import time

debug=False
interval=datetime.time(0, 5,00)   # Keep the interval long enough to run for a long time on the 16000 point memory (to avoid having to press play too often)
port = "/dev/tty.SLAB_USBtoUART"
device = elitech.Device(port)
device.debug = debug
device.init()


# get devinfo
devinfo = device.get_devinfo()
if debug:
    for k,v in vars(devinfo).items():
        print("{}={}".format(k, v))

if devinfo.rec_interval!=interval:
    # Only do this if needed as it has the side effect of clearing recording and stopping
    print("Setting record interval to ",interval)
    param_put = devinfo.to_param_put()  #convert devinfo to parameter
    param_put.rec_interval = interval
    param_put_res = device.update(param_put)    # update device
    devinfo = device.get_devinfo()


print("Current sample: %d, rec_interval=%s"%(devinfo.rec_count, devinfo.rec_interval))
device.set_clock(devinfo.station_no, datetime.datetime.now())

while True:
    try:
        # get data
        latest=device.get_latest()
    except Exception as err:
        print("Error in communicating with temp/RH probe: ",err)
        time.sleep(10)
        continue
    
    print("latest=",latest)
    if latest[0] is None:
        # Not recording, and no way to start it programmatically
        print("Need to start recording on data logger (long push on button until play symbols appears)")
        time.sleep(10)
        continue
    
    if latest[0]==16000:
        print("Logger full!")
        # Send an update command to device;  has the side effect of clearing the buffer and stopping recording (will need to press play button after this)
        param_put = devinfo.to_param_put()  #convart devinfo to parameter
        param_put.rec_interval = interval
        param_put_res = device.update(param_put)    # update device
        time.sleep(10)
        continue
    elapsed=(datetime.datetime.now()-latest[1]).total_seconds()
    print("elapsed=",elapsed)
    if elapsed>600:
        print("Logger is more than 10 minutes behind")
        break;
    temp=latest[2]
    RH=latest[3]
    gamma=math.log(RH/100)+18.678*temp/(257.14+temp)
    dewpoint=257.14*gamma/(18.678-gamma)
    settemp=dewpoint+2
    if settemp<4:
        settemp=4
    print("temp=%.1f, RH=%.1f, DP=%.1f,Set=%.1f"%(temp,RH,dewpoint,settemp))

    try:
        for i in range(2):
            r=ric.RIC()
            r.open(i)
            print("Status[%d] = %s"%(i,r.status()))
            r.settemp(settemp)
            print("Set temp[%d] to %.1f"%(i,settemp))
            ptemp=r.gettemp()
            print("Plate %d now at %.1f"%(i,ptemp))
            time.sleep(5)
            r.close()
    except Exception as err:
        print("Error in communicating with RIC: ",err)
        
    time.sleep(60)
    
