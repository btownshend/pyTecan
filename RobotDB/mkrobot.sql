-- Make database on gcloud mysql for robot data
-- Almost identical to SQLLITE database (since it will be synced from there)
--   but:  doesn't include synctime columns used to drive movement from robot to master
--            flags supports sync from master back to robot
create database robot;

use robot;
-- An experiment -- a pass through a particular program with a fixed set of plates
-- May be made up of multiple runs
create table expts (
       expt integer primary key auto_increment,
       complete boolean not null  -- True after run is complete (log_endrun processed)
);

-- Header for a run (which is actually a parse of one logfile -- multiple runs could make up a single experiment
-- Inserted,updated on robot only, read-only on master
create table runs(
       run integer primary key auto_increment,
       program integer not null, foreign key(program) references programs(program),
       logfile varchar(50),
       starttime timestamp not null default current_timestamp,
       endtime timestamp null,         -- time of last log entry (or null if not completely parsed)
       lineno integer default null,    -- last (or current) line processed in log
       firstline integer default null,   -- first line processed in log
       expt integer, foreign key(expt) references expts(expt),   -- which expt this run is part of
       logheader varchar(100) not null  -- message from beginning of log (program names, lines planned to execute)
       status varchar(50) default null  -- Message from last log_status
);


-- Flags for a run
-- Inserted on either robot or master, never updated (just add a later record instead)
create table flags(
       flag integer primary key  auto_increment, 
       run integer  not null,
       name varchar(50)  not null, 
       value integer, 
       lastupdate timestamp not null,
       pulltime timestamp null,  -- Time this record was last pulled to robot
       foreign key(run) references runs(run) on delete cascade
);

-- Measurements of Vols for a run
-- Inserted on robot only, read-only on master, never updated
-- Volume measurement occuring during a particular program operation
create table vols(
       vol integer primary key auto_increment,
       run integer not null,
       op integer not null, foreign key(op) references ops(op) on delete cascade, -- not null
       estvol float not null,   -- estimated volume based on prior operations and measurements
       gemvolume float,	  -- Volume as reported by Gemini
       volume float,   -- gemvolume converted to true volume
       height integer,  -- tip height as reported by Gemini (in native units of 1/10 mm)
       submerge integer, -- submerge depth
       zmax integer,  -- zmax - bottom of tube
       zadd integer,  -- zadd - extra height needed after submerge (to permit tracking during aspirate?)
       measured timestamp not null default current_timestamp,	-- when was measurement made
       foreign key(run) references runs(run) on delete cascade
);

-- Programs
-- inserted during build of progam (generation time)
create table programs(
    program integer primary key auto_increment,
    name varchar(50) not null,
    gentime not null timestamp,
    checksum varchar(8) not null,
    gitlabel varchar(8) not null,
    totaltime float default null, -- Total execution time estimate in minutes
    complete boolean not null,  -- True if all data for this program is in database
    unique(name,gentime)
);

create table samples (
       sample integer primary key auto_increment,
       program integer not null, foreign key(program) references programs(program) on delete cascade,
       plate varchar(20) not null,
       well varchar(4) not null,
       name varchar(50) not null,
       unique(program,plate,well)
);

create table liquidclasses (
    lc integer primary key auto_increment,
    name varchar(50) not null
);
-- Pippette operations
-- for washes: sample, lc, and volume are null
-- some denormalization as ops.program must be the same as ops.sample.program
create table ops (
       op integer primary key auto_increment,
       program integer not null, foreign key(program) references programs(program) on delete cascade,
       sample integer not null, foreign key(sample) references samples(sample) on delete cascade,
       cmd varchar(20) not null,
       lineno integer not null,  -- line number in program
       elapsed float not null,   -- elapsed time in program
       tip integer not null,   -- which tip was used (1..4)
       lc integer not null, foreign key(lc) references liquidclasses(lc),
       volchange float not null,  -- increase/decrease in volume  (+ for dispense, -ve for aspirate, 0 for LD)
       clean boolean
);

CREATE OR REPLACE VIEW v_ops AS
SELECT p.program,p.name pgmname,o.lineno,o.elapsed,o.op,s.sample, s.name,s.plate,s.well,o.cmd,o.tip,lc.name lc,o.volchange,o.clean
FROM ops o, samples s, liquidclasses lc, programs p
WHERE o.sample=s.sample AND s.program=p.program AND o.lc=lc.lc
order by o.lineno;

CREATE OR REPLACE VIEW v_vols AS
SELECT v.run, p.program, p.name pgmname,o.lineno,o.elapsed,v.measured,o.op,s.sample,s.name,s.plate,s.well,o.cmd,o.tip,lc.name lc,o.volchange, v.estvol, v.volume obsvol,v.gemvolume, v.height,v.submerge,v.zmax,v.zadd
FROM vols v, ops o, samples s, liquidclasses lc, programs p
WHERE v.op=o.op AND o.sample=s.sample AND s.program=p.program AND o.lc=lc.lc
order by o.lineno;

CREATE OR REPLACE VIEW v_tips AS
SELECT * FROM v_ops ORDER BY tip,lineno;

create or replace view v_history as
select r.run,s.program,s.sample,s.plate,s.well,s.name,o.op,o.cmd,o.lineno,o.tip,o.volchange,o.elapsed,v.vol,v.volume,v.measured,v.estvol
from runs r
JOIN samples s ON r.program=s.program
JOIN ops o ON s.sample=o.sample
left join vols v on v.op=o.op AND v.run=r.run
where (v.measured is not null or o.cmd!='Detect_Liquid')
order by r.run,s.plate, s.well, o.lineno;
