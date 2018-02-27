rm test.dbs
sqlite3 < setup.sql
python db.py startrun 'TEST' '2018-02-26 04:06:11' 350d f4e5f14
python db.py tick 3.4  56.4
python db.py tick 10.4  51.4
python db.py setflag xx 0
python db.py getflag xx; echo Exit status=$?
python db.py setflag xx 1
python db.py getflag xx; echo Exit status=$?
python db.py getflag xy; echo Exit status=$?
python db.py setvol T7 Reagents A4 10 11.2
python db.py getvol Reagents A4; echo Exit status=$?
python db.py setvol T7B Reagents A4 20 20.4
python db.py getvol Reagents A4; echo Exit status=$?
python db.py setvol RT Samples A5 100 100.1
python db.py getvol Samples A5; echo Exit status=$?
python db.py endrun TEST
#python db.py push
sqlite3 <<EOF
.open test.dbs
.headers on
.mode column
select * from runs;
select * from flags;
select * from sampnames;
select * from vols;
select * from ticks;
EOF


       
