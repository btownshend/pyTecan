.open test.dbs
pragma foreign_keys = ON;
create table runs(
       run text primary key, 
       program text not null, 
       starttime datetime not null,
       gentime datetime not null,
       checksum text not null,
       gitlabel text not null,
       endtime datetime,
       synctime datetime
);
create table ticks(
       tick integer primary key, 
       run text not null, 
       elapsed float not null, 
       remaining float, 
       time datetime not null,
       foreign key(run) references runs(run) on delete cascade
);
create table flags(
       flag integer primary key, 
       run text not null, 
       name text not null, 
       value integer, 
       lastupdate datetime not null, 
       unique(run,name),
       foreign key(run) references runs(run) on delete cascade
);
create table sampnames(
       run text not null,
       plate text not null,
       well text not null,
       name text not null,
       foreign key(run) references runs(run)  on delete cascade,
       primary key(run,plate,well)
);
create table vols(
       vol integer primary key, 
       run text not null, 
       plate text not null, 
       well text not null,
       gemvolume float not null,	  -- Volume as reported by Gemini
       volume float,   -- gemvolume converted to true volume
       expected float,   -- expected true volume
       measured datetime not null,	-- when was measurement made
       foreign key(run) references runs(run) on delete cascade
);
