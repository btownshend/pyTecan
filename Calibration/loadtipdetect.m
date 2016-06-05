% Load tip detect data from a Gemini log file
% Returns a matrix of heights from the deck in mm organized as (4,N) tip x measurement
function heights=loadtipdetect(logfile)
cmd=sprintf('grep ''RVZ.*selector=0'' %s | sed -e ''s/.*ecode=0, *//'' -e ''s/p[0-9]=//g'' >/tmp/rvz.csv',logfile);
system(cmd);
x=load('/tmp/rvz.csv');
x=x';
x(x==0)=nan;
x=reshape(x(:),4,[]);
heights=(2100-x)/10;
