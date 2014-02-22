% Calculate liquid tracking error
function liquidtrackerror(initvol, aspvolume)
zmax=1519;
mdl(2)=struct('radius',sqrt(52.63/pi),'bottom',13.65,'flatradius',0);
%mdl(2)=struct('radius',sqrt(78.5/pi),'bottom',13,'flatradius',0);
mdl(1).vmeasured=[0,50,75,100,125,150,175,200:100:1100];
mdl(1).hmeasured=([1519,1565,1581,1594,1606,1616,1625,1633,1662,1684,1704,1723,1743,1762,1781,1800,1819]-zmax)/10;
vtest=[0,50,75,100,125,150,175,200:100:1100];
for i=1:length(vtest)
  h=vol2height(vtest(i),mdl(1));
  vv=height2vol(h,mdl(1));
  fprintf('%.2ful -> %.2fmm (%.0f) -> %.2ful\n', vtest(i), h,h*10+zmax,vv);
end
htrueinit=vol2height(initvol,mdl(1));
htruefinal=vol2height(initvol-aspvolume,mdl(1));
vestinit=height2vol(htrueinit,mdl(2));
hestfinal=vol2height(vestinit-aspvolume,mdl(2));
fprintf('Robot though initial volume was %.0f ul\n', vestinit);
fprintf('Aspiration moved liquid surface from h=%.1f (%.0f)  (vol=%.1f) to %.1f (%.0f) (vol=%.1f), but robot moved tip to %.1f (%.0f)\n', htrueinit, htrueinit*10+zmax, height2vol(htrueinit,mdl(1)), htruefinal, htruefinal*10+zmax, height2vol(htruefinal,mdl(1)), hestfinal, hestfinal*10+zmax);
fprintf(' Height error= %.2f mm\n', (hestfinal-htruefinal));

setfig('liquidtrackerror');clf;
v=initvol:-1:initvol-aspvolume;
htrue=[];hest=[];
for i=1:length(v)
  htrue(i)=vol2height(v(i),mdl(1));
  hest(i)=vol2height(v(i),mdl(2));
end
relht=hest-htrue;
relht=relht-relht(1)-1;
plot(initvol-v,relht,'g');
hold on;
plot([0,aspvolume],[0,0],'r:');
xlabel('Aspirated Volume (ul)');
ylabel('Height of tip above liquid (mm)');
title(sprintf('Removal of %.1f ul from %.1f ul',aspvolume,initvol));

% Compute height of liquid at given volume
% tube has given fixed radius at cylindrical part and then funnels down to flatradius as a cone in bottom mm
function vol=height2vol(h,mdl)
if ~isempty(mdl.vmeasured)
  vol=interp1(mdl.hmeasured,mdl.vmeasured,h,'spline','extrap');
  return;
end
hextend=mdl.bottom/(mdl.radius-mdl.flatradius)*mdl.flatradius;
volextend=1/3*pi*mdl.flatradius^2*hextend;
if h<mdl.bottom
  rsurf=h/mdl.bottom*(mdl.radius-mdl.flatradius)+mdl.flatradius;
  conevol=1/3*pi*rsurf^2*(h+hextend)-volextend;
  vol=conevol;
else
  rsurf=mdl.radius;
  conevol=1/3*pi*rsurf^2*(mdl.bottom+hextend)-volextend;
  vol=conevol+(h-mdl.bottom)*pi*rsurf^2;
end

  
function height=vol2height(v,mdl)
if ~isempty(mdl.vmeasured)
  height=interp1(mdl.vmeasured,mdl.hmeasured,v,'spline','extrap');
  return;
end
h=0:.1:60;
vol=[];
for i=1:length(h)
  vol(i)=height2vol(h(i),mdl);
end
height=interp1(vol,h,v);
  
