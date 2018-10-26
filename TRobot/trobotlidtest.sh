#!/bin/sh
while true
do
    #python trobotsetpgm.py PCR7 99 TEMP@95,30 TEMP@57.0,30 TEMP@68.0,30 TEMP@25,2
    python trobotlid.py CLOSE
    #python trobotrun.py
    #python trobotwait.py
    python trobotlid.py OPEN
    sleep 10
    #python trobotsetpgm.py TRP37-30 38 TEMP@37,10 TEMP@25,2
    python trobotlid.py CLOSE
    #python trobotrun.py
    #python trobotwait.py
    python trobotlid.py OPEN
    sleep 10
done
    

