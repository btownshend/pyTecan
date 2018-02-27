-- Make database on gcloud mysql for robot data
-- Almost identical to SQLLITE database (since it will be synced from there)

create database robot;

use robot;

alter table runs drop column synctime;
create table runs(
       run varchar(36), primary key(run), 
       program varchar(50), 
       starttime datetime,
       gentime datetime,
       checksum varchar(8),
       gitlabel varchar(8),
       endtime datetime
);
drop table sampnames;
create table sampnames(
       run varchar(36), foreign key(run) references runs(run) on delete cascade,
       plate varchar(20),
       well varchar(3),
       name varchar(50),
       primary key(run,plate,well)
);
drop table vols;
create table vols(
       run varchar(36), 
       vol integer, primary key(run,vol), 
       plate varchar(20), 
       well varchar(3),
       gemvolume float,	  -- Volume as reported by Gemini
       volume float,   -- gemvolume converted to true volume
       expected float,   -- expected true volume
       measured datetime,	-- when was measurement made
       foreign key(run) references runs(run) on delete cascade
);
delete from runs where run > '0';
select * from runs;
select * from sampnames;
select * from vols;
