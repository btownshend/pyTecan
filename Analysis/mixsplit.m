% Test splitting of mixdowns

function stages=mixsplit(vols,names,minvol,maxvol,maxmix,nextmixnum,dilute)
if nargin<2
  names=arrayfun(@(z) sprintf('S%d',z),1:length(vols),'UniformOutput',false);
end
if nargin<3
  minvol=4;
end
if nargin<4
  maxvol=20;
end
if nargin<5
  maxmix=100;
end
if nargin<6
  nextmixnum=1;
end
if nextmixnum>40
  error('Too deep');
end
if nargin<7
  dilute=1;
end
[vols,ord]=sort(vols,'ascend');
names=names(ord);
vols=vols*minvol/min(vols);
if dilute>1
  water=min(maxmix-sum(vols),(dilute-1)*sum(vols));
  vols(end+1)=water;
  names{end+1}='Water';
  dilute=sum(vols)/sum(vols(1:end-1));
end
fprintf('Level %d, sum(vol)=%.1f, Dilute=%.2f\n',nextmixnum,sum(.vols),dilute);
for i=1:length(names)
  fprintf('%s%-5.5s %.2f\n',blanks(nextmixnum-1),names{i}, vols(i));
end
if sum(vols)<=maxmix
  stages=struct('prodname',sprintf('Mix%d',nextmixnum),'names',{names},'vols',vols,'dilute',dilute);
  return
end
for i=1:length(vols)
  if sum(vols(1:i))>maxmix || vols(i)>maxvol
    % Split at i-1
    if sum(vols(1:i-1))<vols(i)*minvol/maxvol
      dilute=vols(i)/sum(vols(1:i-1));
    else
      dilute=1;
    end
    stages=mixsplit(vols(1:i-1),names(1:i-1),minvol,maxvol,maxmix,nextmixnum,dilute);
    vv=[vols(i:end),sum(vols(1:i-1))*stages(end).dilute];
    nn={names{i:end},stages(end).prodname};
    stages=[stages,mixsplit(vv,nn,minvol,maxvol,maxmix, nextmixnum+length(stages))];
    pause(1);
    return;
  end
end
  
