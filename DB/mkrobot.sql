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
       pgm_id integer, foreign key(pgm_id) references programs(program),
       program varchar(50) not null, 
       starttime timestamp not null default current_timestamp,
       gentime timestamp not null default current_timestamp,
       checksum varchar(8) not null,
       gitlabel varchar(8) not null,
       endtime timestamp null
);


-- Ticks for a run
-- Inserted on robot only, read-only on master, never updated (except synctime)
create table ticks(
       tick integer primary key  auto_increment,
       run varchar(36) not null, 
       elapsed float not null, 
       remaining float,
       lineno integer, -- not null,   -- Line number in GEM program
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

-- Sample names for a run
-- Inserted on robot only, read-only on master, never updated
create table sampnames(
       sampname integer primary key  auto_increment, 
       run varchar(36) not null, foreign key(run) references runs(run) on delete cascade,
       plate varchar(20) not null,
       well varchar(4) not null,
       name varchar(50) not null
);

-- Vols for a run
-- Inserted on robot only, read-only on master, never updated
-- Volume measurement occuring during a particular program operation
create table vols(
       vol integer primary key auto_increment,
       run varchar(36),
       pgm_op integer, foreign key(pgm_op) references pgm_ops(pgm_op), -- not null
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
    gentime timestamp default null,
    checksum varchar(8) default null,
    gitlabel varchar(8) default null
);

create table pgm_samples (
       pgm_sample integer primary key auto_increment,
       program integer not null, foreign key(program) references programs(program) on delete cascade,
       initialVolume float not null,
       plate varchar(20) not null,
       well varchar(4) not null,
       name varchar(50) not null,
       unique(program,plate,well)
);

create table pgm_ops (
       pgm_op integer primary key auto_increment,
       pgm_sample integer not null, foreign key(pgm_sample) references pgm_samples(pgm_sample) on delete cascade,
       op varchar(20), -- not null
       lineno integer, -- not null,  -- line number in program
       tip integer not null,   -- which tip was used (1..4)
       liquidClass varchar(20),
       volume float not null,   -- expected volume after operation (FIXME: not needed?)
       volchange float not null  -- increase/decrease in volume  (+ for dispense, -ve for aspirate, 0 for LD)
);

