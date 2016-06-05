logfile='LOG02320.txt';
vol=10:10:200;
zmax=994;

cmd=sprintf('grep ''RVZ'' %s | sed -e ''s/.*ecode=0, *//'' -e ''s/p[0-9]=//g'' >/tmp/rvz.csv',logfile);
system(cmd);
x=load('/tmp/rvz.csv');
x=x';
x(x==0)=nan;
x=reshape(x(:),4,2,[]);
heights=-(2100-squeeze(x(:,2,:))-zmax)/10;
heights(:,end+1)=0;
vol(end+1)=0;
fit=fitheights(vol,heights);
