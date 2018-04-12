function [heights,meanoffset]=heights3(run,plate,offsets,vrange,angle,slopemodel)
if nargin<6 || isempty(slopemodel)
  slopemodel=false;
end
if nargin<5 || isempty(angle)
  angle=17.5;
end
if nargin<4 || isempty(vrange)
  vrange=[15,100];   % Go for more accuracy at low end of range
end
if nargin<3 || isempty(offsets)
  offsets=[390,390,390,390];
end
db=struct('host','35.203.151.202','user','robot','password','cdsrobot','db','robot');
mysql('closeall');
mysql('open',db.host,db.user,db.password);
mysql('use',db.db);
runlist=strjoin(arrayfun(@(z) sprintf('%d',z), run,'UniformOutput',false),',');
if nargin<2 || isempty(plate)
  % Run on all plates that have enough data
  [plates,counts]=mysql(sprintf('select plate,count(distinct well) from robot.v_vols where run in (%s) and height is not null group by plate',runlist));
  for i=1:length(plates)
    if counts(i)>=10
      fprintf('Running on plate %s with %d wells of data\n', plates{i}, counts(i));
      heights3(run,plates{i},offsets,vrange,angle,slopemodel);
    end
  end
  return;
end
[wellnames,tip,vol,obsvol,heights,zmax,gemvolume]=mysql(sprintf('select well,tip,estvol,obsvol,height,zmax,gemvolume from robot.v_vols where run in (%s) and plate=''%s'' and cmd=''Detect_Liquid''',runlist,plate));
zmax=unique(zmax(isfinite(zmax)));
assert(length(zmax)==1);
heights=(heights-zmax)/10;	% Convert to height relative to zmax, -ve is up
wells=nan(length(wellnames),2);
for i=1:length(wellnames)
  wells(i,1)=(wellnames{i}(1)-'A')-3.5;
  wells(i,2)=str2num(wellnames{i}(2:end))-6.5;
end

ti=sprintf('Level Calibration - %s - Run %s',plate,runlist);
setfig(ti);
clf;
subplot(311);
leg={};
for i=1:4
  sel=tip==i;
  plot(vol(sel),heights(sel),'o');
  hold on;
  leg{i}=sprintf('Tip %d N=%d',i,sum(isfinite(heights(sel))));
end
xlabel('Volume (ul)');
ylabel('Height above ZMax (mm)');
legend(leg);
title(sprintf('Raw measurements relative to ZMax (%.0f)',zmax));

failvol=[]; goodvol=[];
for i=1:4
  ffind=find(tip==i & isnan(heights));
  if isempty(ffind)
    failvol(i)=0;
  else
    failvol(i)=max(vol(ffind));
  end
  gfind=find(tip==i & isfinite(heights));
  if isempty(gfind)
    goodvol(i)=nan;
  else
    goodvol(i)=min(vol(gfind));
  end
end
fprintf('Tip liquid detections fails at as much as [%s] ul, works at as little as [%s] ul\n', sprintf('%.0f ',failvol),sprintf('%.0f ',goodvol));
sel=isfinite(heights);
vol=vol(sel);
heights=heights(sel);
wells=wells(sel,:);
tip=tip(sel);
obsvol=obsvol(sel);
gemvolume=gemvolume(sel);
[fit,angle,expected]=fitheights2(vol,heights,wells,tip,angle,[],slopemodel);
meanoffset=-[0,fit(6:8)];
meanoffset=meanoffset-mean(meanoffset);
fprintf('Tip offset (distance higher than mean): %s mm\n', sprintf('%.2f ',meanoffset));
fprintf('  -> should set LIHA Tip Offsets to [%s]\n',sprintf('%.0f ',390+meanoffset*10));
fprintf('  or adjust firmware C5SOZ by [%s]\n',sprintf('%.0f ',-meanoffset*10));
if isempty(offsets)
  offsets=meanoffset*10+390;
else
  fprintf('     currently are [%s]\n', sprintf('%.0f ',offsets));
end

% Check effect of slope
maxheightdiff=abs(fit(4)*11)+abs(fit(5)*7);
maxvoldiff=pi*fit(1)^2*maxheightdiff;
fprintf('Plate slope results in maximum volume difference corner-to-corner of %.1f ul (height difference of %.1fmm)\n',maxvoldiff, maxheightdiff);


hsteps=0:0.05:40;
vsteps=calcvol2(hsteps,[],[],angle,fit(1),fit(2),fit(3),fit(4),fit(5),fit(6:8));

subplot(311);
hold on;
sel=vsteps<max(vol);
plot(vsteps(sel),hsteps(sel),'k-');

subplot(312);
for i=1:4
  plot(vol(tip==i),expected(tip==i)-obsvol(tip==i),'o');
  hold on;
end
xlabel('Volume (ul)');
ylabel('Error (ul)');
title('Measurement error using models in effect at run time');

subplot(313);
% Match gemini to above model over 15-150ul range
sel=vsteps>=vrange(1) & vsteps<=vrange(2);
hsteps=hsteps(sel);
vsteps=vsteps(sel);
r1=fit(1);
h1=fit(2);
v0=fit(3);
h0=h1-r1/tand(angle/2);
gdepth=h1+h0/2+3/2*v0/pi/r1^2;
%gmdl=geminifit(vsteps, hsteps, [], struct('depth',gdepth,'area',pi*fit(1)^2,'hoffset',0));
gmdl=geminifit(vsteps, hsteps);
hold on;
[vg,ord]=sort(gemvolume);
plot(vg,heights(ord),'r','LineWidth',2);
s=get(legend(),'String');
s{end}='During Run';
set(legend(),'String',s);
title('Gemini Fit');

suptitle(ti);
submergecheck(fit,angle,gmdl,200)

fprintf('zmax=%.0f,angle=%.1f,r1=%.3f,h1=%.2f,v0=%.2f,slopex=%.3f,slopey=%.3f,gemDepth=%.2f,gemArea=%.2f\n', zmax, angle, fit(1:5), gmdl.depth, gmdl.area);