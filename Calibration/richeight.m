logfile='LOG02314.txt';
vol=25:25:(5*7*25);
zmax=563;

cmd=sprintf('grep ''RVZ'' %s | sed -e ''s/.*ecode=0, *//'' -e ''s/p[0-9]=//g'' >/tmp/rvz.csv',logfile);
system(cmd);
x=load('/tmp/rvz.csv');
x=x';
x(x==0)=nan;
x=reshape(x(:),4,2,[]);
heights=-(2100-squeeze(nanmean(x,2))-zmax)/10;
fit=fitheights(vol,heights);
