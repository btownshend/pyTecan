% Model is
%    depth - depth of conical part (point to cylinder)
%    area = area above ridge
function vol=gemcalcvol(h,depth,area)
r1=sqrt(area/pi);
vol=1/3*pi * (h).^3 * (r1/depth)^2;
v1=1/3*pi * depth^3 * (r1/depth)^2;
volhi=v1+(h-depth)*area;
vol(h>depth)=volhi(h>depth);
