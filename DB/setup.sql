.open robot.dbs
pragma foreign_keys = ON;
-- Header for a run
-- Inserted,updated on robot only, read-only on master
create table runs(
       run text primary key, 
       program text not null, 
       starttime datetime not null,
       gentime datetime not null,
       checksum text not null,
       gitlabel text not null,
       endtime datetime,
       synctime datetime  -- Time this record was last pushed to master, or NULL if never;  still needs sync if endtime>synctime
);
-- Ticks for a run
-- Inserted on robot only, read-only on master, never updated (except synctime)
create table ticks(
       tick integer primary key, 
       run text not null, 
       elapsed float not null, 
       remaining float, 
       time datetime not null,
       synctime datetime,  -- Time this record was last pushed to master
       foreign key(run) references runs(run) on delete cascade
);
-- Flags for a run
-- Inserted on either robot or master, never updated (except synctime)
create table flags(
       flag integer primary key, 
       run text not null, 
       name text not null, 
       value integer, 
       lastupdate datetime not null, 
       synctime datetime,  -- Time this record was last pushed to master
       foreign key(run) references runs(run) on delete cascade
);
-- Sample names for a run
-- Inserted on robot only, read-only on master, never updated (except synctime)
create table sampnames(
       sampname integer primary key,
       run text not null,
       plate text not null,
       well text not null,
       name text not null,
       synctime datetime,  -- Time this record was last pushed to master
       foreign key(run) references runs(run)  on delete cascade,
       unique(run,plate,well)
);

-- Vols for a run
-- Inserted on robot only, read-only on master, never updated (except synctime)
create table vols(
       vol integer primary key, 
       run text not null, 
       plate text not null, 
       well text not null,
       gemvolume float not null,	  -- Volume as reported by Gemini
       volume float,   -- gemvolume converted to true volume
       expected float,   -- expected true volume
       measured datetime not null,	-- when was measurement made
       synctime datetime,  -- Time this record was last pushed to master
       foreign key(run) references runs(run) on delete cascade
);
