% Check for replicate differences in Cts
function replicatediff(d)
allnames=cellfun(@(z) z.name, d.results,'UniformOutput',false);
comp={[],[],[]};
fns={'MX','AX','BX'};
foundSome=false;
for i=1:length(d.results)
  r=d.results{i};
  if ~isempty(strfind(r.name,'.2.'))
    n1=strrep(r.name,'.2.','.');
    j=find(strcmp(n1,allnames));
    if length(j)~=1
      fprintf('Unable to find %s to match with %s\n', n1, r.name);
      continue;
    end
    r1=d.results{j};
    for k=1:length(fns)
      if isfield(r1,fns{k}) && isfield(r,fns{k})
        comp{k}(end+1,:)=[r1.(fns{k}).ct,r.(fns{k}).ct];
        foundSome=true;
      end
    end
  end
end
if ~foundSome
  return;
end
setfig('replicate diff'); clf;
cols=hsv(length(fns));
leg={};
for k=1:length(fns)
  if size(comp{k},1)>0
    plot(comp{k}(:,1),comp{k}(:,2),'o','Color',cols(k,:));
    hold on;
    leg{end+1}=sprintf('%s: RMSE=%.2f', fns{k}, sqrt(mean((comp{k}(:,1)-comp{k}(:,2)).^2)));
  end
end
legend(leg);
title('Replicate Ct');
xlabel('Ct (replicate 1)');
ylabel('Ct (replicate 2)');
axis equal
c=axis;
plot(c(1:2),c(1:2),':');

