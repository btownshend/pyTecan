logfile='LOG02308.txt';
vol=200:-10:60;
zmax=1032;

cmd=sprintf('grep ''RVZ'' %s | sed -e ''s/.*ecode=0, *//'' -e ''s/p[0-9]=//g'' >/tmp/rvz.csv',logfile);
system(cmd);
x=load('/tmp/rvz.csv');
x=x';
x(x==0)=nan;
x=reshape(x(:),4,2,[]);
heights=-(2100-squeeze(nanmean(x,2))-zmax)/10;
% Force a zero
heights(:,end+1)=0;
vol(end+1)=0;
fit=fitheights(vol,heights,17.5,[5.08/2,9.16,10]);
% See https://www.evernote.com/shard/s43/nl/4571194/eabe3ee0-a8e2-4078-b344-33079564ef19/
% Has full dimensions: 
%  r1=2.59, h0=-6.79, h1=10.05, v0=8, angle=17.5deg
