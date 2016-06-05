function h=gemcalcheight(v,mdl)
r1=sqrt(mdl.area/pi);
h=(v./(r1/mdl.depth)^2*3/pi).^(1/3);
v1=1/3*pi * mdl.depth^3 * (r1/mdl.depth)^2;
hhi=(v-v1)/mdl.area+mdl.depth;
h(v>v1)=hhi(v>v1);
h=h+mdl.hoffset;


