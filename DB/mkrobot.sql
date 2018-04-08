-- Make database on gcloud mysql for robot data
-- Almost identical to SQLLITE database (since it will be synced from there)
--   but:  doesn't include synctime columns used to drive movement from robot to master
--            flags supports sync from master back to robot
create database robot;

use robot;

-- Header for a run
-- Inserted,updated on robot only, read-only on master
create table runs(
       run varchar(36), primary key(run),
       program integer, foreign key(program) references programs(program),
       starttime timestamp not null default current_timestamp,
       endtime timestamp null
);


-- Ticks for a run
-- Inserted on robot only, read-only on master, never updated (except synctime)
create table ticks(
       tick integer primary key  auto_increment,
       run varchar(36) not null, 
       elapsed float not null, 
       remaining float,
       lineno integer not null,   -- Line number in GEM program
       time timestamp not null default current_timestamp,
       foreign key(run) references runs(run) on delete cascade
);

-- Flags for a run
-- Inserted on either robot or master, never updated (just add a later record instead)
create table flags(
       flag integer primary key  auto_increment, 
       run varchar(36)  not null, 
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
       run varchar(36),
       op integer, foreign key(op) references ops(op), -- not null
       gemvolume float not null,	  -- Volume as reported by Gemini
       volume float,   -- gemvolume converted to true volume
       measured timestamp not null default current_timestamp,	-- when was measurement made
       foreign key(run) references runs(run) on delete cascade
);

-- Programs
-- inserted during build of progam (generation time)
create table programs(
    program integer primary key auto_increment,
    name varchar(50) default null,
    gentime timestamp,
    checksum varchar(8) default null,
    gitlabel varchar(8) default null
);

create table samples (
       sample integer primary key auto_increment,
       program integer not null, foreign key(program) references programs(program) on delete cascade,
       initialVolume float not null,
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
       sample integer, foreign key(sample) references samples(sample) on delete cascade,
       cmd varchar(20) not null,
       lineno integer not null,  -- line number in program
       elapsed float not null,   -- elapsed time in program
       tip integer not null,   -- which tip was used (1..4)
       lc integer null, foreign key(lc) references liquidclasses(lc),
       volume float,   -- expected volume after operation (FIXME: not needed?)
       volchange float not null  -- increase/decrease in volume  (+ for dispense, -ve for aspirate, 0 for LD)
);

CREATE OR REPLACE VIEW v_ops AS
SELECT p.program,p.name pgmname,o.lineno,o.elapsed,o.op,s.name,s.plate,s.well,o.cmd,o.tip,lc.name lc,s.initialVolume,o.volchange,o.volume FROM ops o, samples s, liquidclasses lc, programs p WHERE o.sample=s.sample AND s.program=p.program AND o.lc=lc.lc order by o.lineno;

CREATE OR REPLACE VIEW v_vols AS
SELECT v.run, p.program, p.name pgmname,o.lineno,o.elapsed,v.measured,o.op,s.name,s.plate,s.well,o.cmd,o.tip,lc.name lc,o.volchange,o.volume expectvol, v.volume obsvol FROM vols v, ops o, samples s, liquidclasses lc, programs p WHERE v.op=o.op AND o.sample=s.sample AND s.program=p.program AND o.lc=lc.lc order by o.lineno;

CREATE OR REPLACE VIEW v_tips AS
SELECT * FROM v_ops ORDER BY tip,lineno;