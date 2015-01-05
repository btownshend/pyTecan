% Compare Ct's from Miner with internal computation
function results=minercompare(data)
primers=fieldnames(data.primers);
internal=[];miner=[];plist={};sampnum=[];
for i=1:length(primers)
  primer=primers{i};
  prevlength=length(internal);
  for j=1:length(data.results)
    r=data.results{j};
    if isfield(r,primer)
      if isfield(r.(primer),'cti') 
        internal(end+1)=r.(primer).cti;
      else
        internal(end+1)=nan;
      end
      if isfield(r.(primer),'ctm')
        miner(end+1)=r.(primer).ctm;
      else
        miner(end+1)=nan;
      end
      plist{end+1}=primer;
      sampnum(end+1)=j;
    end
  end
  if length(internal)>prevlength
    fprintf('Primer %s, %d points\n', primer, length(internal)-prevlength);
  end
end

diff=miner-internal;
checkrange=[6,20];
fprintf('Fitting over miner range of Ct of [%f, %f]\n', checkrange);
checksel=miner>=checkrange(1) & miner<=checkrange(2);

uprimers=unique(plist);
cmap=hsv(max(4,length(uprimers)));
ctrange=[min(internal),max(internal)];

setfig('minercompare'); clf;
subplot(3,1,[1,2]);
h=[];
for i=1:length(uprimers)
  sel=strcmp(plist,uprimers{i});
  h(i)=plot(internal(sel),miner(sel),'o','Color',cmap(i,:));
  hold on;
  plot(ctrange,ctrange+nanmean(diff(sel&checksel)),'-','Color',cmap(i,:));
end
legend(h,uprimers);
xlabel('Internal');
ylabel('Miner');
axis equal
subplot(313);
for i=1:length(uprimers)
  sel=strcmp(plist,uprimers{i});
  plot(sampnum(sel),diff(sel),'o','Color',cmap(i,:));
  hold on;
  fprintf('%s: Miner-Internal=%.1f, Std=%.1f (N=%d)\n',uprimers{i},nanmean(diff(sel&checksel)), nanstd(diff(sel&checksel)),sum(sel&checksel)); 
end
xlabel('Sample number');
ylabel('Miner-Internal');
fprintf('Miner-Internal=%.1f, Std=%.1f (N=%d) \n',nanmean(diff(checksel)), nanstd(diff(checksel)),sum(checksel)); 

results=struct('miner',num2cell(miner),'internal',num2cell(internal),'primer',plist,'sampnum',num2cell(sampnum));
