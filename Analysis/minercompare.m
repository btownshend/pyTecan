% Compare Ct's from Miner with internal computation
function minercompare(data)
primers=fieldnames(data.primers);
internal=[];miner=[];
for i=1:length(primers)
  primer=primers{i};
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
    end
  end
  fprintf('Primer %s, %d points\n', primer, length(internal));
end

setfig('minercompare'); clf;
subplot(211);
plot(internal,miner,'.');
subplot(212);
diff=miner-internal;
plot(diff,'.');
fprintf('Miner-Internal=%.1f, MSE=%.1f\n',nanmean(diff), sqrt(nanmean(diff.^2))); 

