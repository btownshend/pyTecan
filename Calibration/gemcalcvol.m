% Model is
%    depth - depth of conical part (point to cylinder)
%    area = area above ridge
%    hoffset - height offset
function vol=gemcalcvol(h,mdl)
h=h-mdl.hoffset;
if mdl.depth==0
  vol=mdl.area*h;
else
  r1=sqrt(mdl.area/pi);
  vol=1/3*pi * (h).^3 * (r1/mdl.depth)^2;
  v1=1/3*pi * mdl.depth^3 * (r1/mdl.depth)^2;
  volhi=v1+(h-mdl.depth)*mdl.area;
  vol(h>mdl.depth)=volhi(h>mdl.depth);
end
