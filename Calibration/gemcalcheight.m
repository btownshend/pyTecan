function h=gemcalcheight(v,depth,area)
r1=sqrt(area/pi);
h=(v./(r1/depth)^2*3/pi).^(1/3);
v1=1/3*pi * depth^3 * (r1/depth)^2;
hhi=(v-v1)/area+depth;
h(v>v1)=hhi(v>v1);


