function [heights,meanoffset]=heights(logfile,vol,zmax,offsets,usex,vrange,angle)
if nargin<7
  angle=17.5;
end
x=loadtipdetect(logfile);
if nargin>=4 && length(usex)>0
  x=x(:,usex);
end
heights=zmax/10-x;	% Convert to height relative to zmax, -ve is up

clf;
subplot(411);
plot(vol,heights,'o-');
xlabel('Volume (ul)');
ylabel('Height above ZMax (mm)');
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
meanheights=nanmean(heights);
legend('Tip 1','Tip 2','Tip 3','Tip 4','Location','NorthWest');
title(sprintf('Raw measurements relative to ZMax (%.0f)',zmax));

% Check tip offset
offset=[];
for i=1:4
  offset(i,:)=heights(i,:)-meanheights;
end
meanoffset=nanmean(offset');
subplot(412);
h=plot(vol,offset');
hold on;
c=axis;
for i=1:4
  plot(c(1:2),meanoffset(i)*[1,1],':','Color',get(h(i),'Color'));
end
xlabel('Volume (ul)');
ylabel('Offset from mean (mm)');
legend('Tip 1','Tip 2','Tip 3','Tip 4');
title('Offsets');

fprintf('Tip offset (distance higher than mean): %s mm\n', sprintf('%.2f ',meanoffset));
fprintf('  -> should set LIHA Tip Offsets to [%s]\n',sprintf('%.0f ',390+meanoffset*10));
if isempty(offsets)
  offsets=meanoffset*10+390;
else
  fprintf('     currently are [%s]\n', sprintf('%.0f ',offsets));
end
adjheights=heights;
for i=1:4
  adjheights(i,:)=adjheights(i,:)-(offsets(i)/10-39);
end
subplot(413);
adjheights(:,end+1)=0;
[fit,angle]=fitheights([vol,0],adjheights,angle);
title('Offset-corrected Fit');

subplot(414);
% Match gemini to above model over 15-150ul range
hsteps=0:0.05:20;
vsteps=calcvol(hsteps,angle,fit(1),fit(2),fit(3));
fprintf('Matching Gemini model over range of %.1f-%.1f ul\n', vrange);
sel=vsteps>=vrange(1) & vsteps<=vrange(2);
hsteps=hsteps(sel);
vsteps=vsteps(sel);
geminifit(vsteps, hsteps);
title('Gemini Fit');
