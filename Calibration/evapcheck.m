% Check levels in an evapcheck run
function evapcheck(runs)
db=struct('host','35.203.151.202','user','robot','password','cdsrobot','db','robot');
mysql('closeall');
mysql('open',db.host,db.user,db.password);
mysql('use',db.db);
runlist=strjoin(arrayfun(@(z) sprintf('%d',z), runs,'UniformOutput',false),',');
[run,wellnames,tip,estvol,volchange,obsvol,heights,zmax,gemvolume,cmd,submerge,op,measured]=mysql(sprintf('select run,well,tip,estvol,volchange,obsvol,height,zmax,gemvolume,cmd,submerge,op,measured from robot.v_vols where run in (%s) order by run,lineno,tip',runlist));

initial=nan(8,12);
final=nan(8,12);
dur=nan(8,12);
for row=1:8
  for col=1:12
    well=sprintf('%c%d',(row+'A'-1),col);
    sel=strcmp(wellnames,well) & isfinite(obsvol);
    vols=obsvol(sel);
    when=measured(sel);
    if length(vols)>=3
      initial(row,col)=vols(2);
      final(row,col)=vols(end);
      dur(row,col)=datenum(when{end})-datenum(when{1});
    end
  end
end
change=final-initial;

fprintf('Average Change: %.2f ul (%.1f%%) over %.0f minutes\n', nanmean(change(:)), nanmean(change(:)./initial(:))*100,nanmean(dur(:))*24*60);

setfig('Evap');clf;
change(end+1,:)=nan;
change(:,end+1)=nan;
pcolor(change);
colorbar;
xlabel('Col');
ylabel('Row');
axis ij;
set(gca,'XTick',(1:12)+0.5);
set(gca,'XTickLabel',arrayfun(@(z) sprintf('%.0f',z), 1:12,'UniformOutput',false));
set(gca,'YTick',(1:8)+0.5);
set(gca,'YTickLabel',{'A','B','C','D','E','F','G','H'});

keyboard;

  
