function [heights,meanoffset]=heights2(logfile,vol,wells,zmax,offsets,usex,vrange,angle)
if nargin<7
  angle=17.5;
end
if iscell(logfile)
  x=[];
  for i=1:length(logfile)
    x=[x,loadtipdetect(logfile{i})];
  end
else
  x=loadtipdetect(logfile);
end
if nargin>=4 && length(usex)>0
  x=x(:,usex);
end
heights=zmax/10-x;	% Convert to height relative to zmax, -ve is up

clf;
subplot(311);
plot(vol,heights,'o');
xlabel('Volume (ul)');
ylabel('Height above ZMax (mm)');
legend('Tip 1','Tip 2','Tip 3','Tip 4','Location','NorthWest');
title(sprintf('Raw measurements relative to ZMax (%.0f)',zmax));

failvol=[]; goodvol=[];
for i=1:4
  ffind=find(isnan(heights(i,:)));
  if isempty(ffind)
    failvol(i)=0;
  else
    failvol(i)=max(vol(ffind));
  end
  gfind=find(isfinite(heights(i,:)));
  if isempty(gfind)
    goodvol(i)=nan;
  else
    goodvol(i)=min(vol(gfind));
  end
end
fprintf('Tip liquid detections fails at as much as [%s] ul, works at as little as [%s] ul\n', sprintf('%.0f ',failvol),sprintf('%.0f ',goodvol));

alltips=repmat(1:4,1,size(heights,2))';
allwells=[];
for i=1:size(wells,1)
  allwells(end+1,:)=wells(i,:);
  allwells(end+1,:)=wells(i,:)+[0,1];
  allwells(end+1,:)=wells(i,:)+[0,2];
  allwells(end+1,:)=wells(i,:)+[0,3];
end

allvol=repmat(vol,4,1);
allvol=allvol(:);
allheights=heights(:);
[fit,angle,expected]=fitheights2(allvol,allheights,allwells,alltips,angle);

meanoffset=-[0,fit(6:8)];
meanoffset=meanoffset-mean(meanoffset);
fprintf('Tip offset (distance higher than mean): %s mm\n', sprintf('%.2f ',meanoffset));
fprintf('  -> should set LIHA Tip Offsets to [%s]\n',sprintf('%.0f ',390+meanoffset*10));
if isempty(offsets)
  offsets=meanoffset*10+390;
else
  fprintf('     currently are [%s]\n', sprintf('%.0f ',offsets));
end

% Check effect of slope
maxheightdiff=abs(fit(4)*11)+abs(fit(5)*7);
maxvoldiff=pi*fit(1)^2*maxheightdiff;
fprintf('Plate slope results in maximum volume difference corner-to-corner of %.1f ul (height difference of %.1fmm)\n',maxvoldiff, maxheightdiff);


subplot(312);
for i=1:4
  plot(allvol(alltips==i),expected(alltips==i)-allvol(alltips==i),'o-');
  hold on;
end
xlabel('Volume (ul)');
ylabel('Error (ul)');
title('Fit error');

subplot(313);
% Match gemini to above model over 15-150ul range
hsteps=0:0.05:40;
vsteps=calcvol2(hsteps,[],[],angle,fit(1),fit(2),fit(3),fit(4),fit(5),fit(6:8));
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
title('Gemini Fit');

submergecheck
