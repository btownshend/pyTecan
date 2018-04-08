rm robot.dbs
sqlite3 << xx
.open robot.dbs
.read setup.sql
xx
python db.py startrun 'TEST' '2018-02-26 04:06:11' 350d f4e5f14 6
python db.py tick 0.949667 184.527167 28
python db.py setvol Reagents A1 123.45 1 38 339.54
python db.py setvol Reagents A1 123.45 1 51 339.54
python db.py setvol Reagents A1 123.45 1 61 339.54
python db.py setvol Samples B1 123.45 1 90 19.95
python db.py setvol Samples C1 123.45 2 90 19.95
python db.py setvol Samples D1 123.45 3 90 19.95
python db.py setvol Samples E1 123.45 4 90 19.95
python db.py tick 2.507833 182.969000 116
python db.py setvol Samples F1 123.45 1 137 19.95
python db.py setvol Samples G1 123.45 2 137 19.95
python db.py setvol Samples H1 123.45 3 137 19.95
python db.py setvol Samples A2 123.45 4 158 19.95
python db.py tick 4.091833 181.385000 169
python db.py setvol Samples B2 123.45 1 193 19.95
python db.py setvol Samples C2 123.45 2 193 19.95
python db.py setvol Samples D2 123.45 3 193 19.95
python db.py setvol Samples E2 123.45 4 193 19.95
python db.py tick 5.565833 179.911000 219
python db.py setvol Samples F2 123.45 1 240 19.95
python db.py setvol Samples G2 123.45 2 240 19.95
python db.py setvol Samples H2 123.45 3 240 19.95
python db.py setvol Samples A3 123.45 4 261 19.95
python db.py tick 7.149833 178.327000 272
python db.py setvol Samples B3 123.45 1 296 19.95
python db.py setvol Samples C3 123.45 2 296 19.95
python db.py setvol Samples D3 123.45 3 296 19.95
python db.py setvol Samples E3 123.45 4 296 19.95
python db.py setflag xx 0
python db.py getflag xx; echo Exit status=$?
python db.py setflag xx 1
python db.py getflag xx; echo Exit status=$?
python db.py getflag xy; echo Exit status=$?
python db.py endrun 6
#python db.py push
sqlite3 <<EOF
.open test.dbs
.headers on
.mode column
select * from runs;
select * from flags;
select * from vols;
select * from ticks;
EOF


       
