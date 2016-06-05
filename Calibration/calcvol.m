% Model is:
%    angle = conical part angle (in degrees)
%    r1 = radius above ridge
%    h0 = height of cone bottom (=h1-r1/tand(angle/2))  (relative to ZMax)
%    h1 = height of cone top
%    v0 = volume infilled in cone
% h<=h1:   v=1/3*pi * (h-h0)^3 * (r1/(h1-h0))^2-v0
% h>h1:    v=v(h1)+(h-h1)*pi*r1^2

function vol=calcvol(h,angle,r1,h1,v0)
h0=h1-r1/tand(angle/2);
vol=1/3*pi * (h-h0).^3 * (r1/(h1-h0))^2-v0;
v1=1/3*pi * (h1-h0)^3 * (r1/(h1-h0))^2-v0;
volhi=v1+(h-h1)*pi*r1^2;
vol(h>h1)=volhi(h>h1);
