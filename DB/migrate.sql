.open robot.dbs
select * from flags;

alter table flags rename to flags_old;
create table flags(
       flag integer primary key, 
       run text not null, 
       name text not null, 
       value integer, 
       lastupdate datetime not null, 
       synctime datetime,  -- Time this record was last pushed to master
       foreign key(run) references runs(run) on delete cascade
);
insert into flags(run,name,value,lastupdate,synctime) select run,name,value,lastupdate,synctime from flags_old;

select * from flags;

alter table runs add pgm_id integer;
