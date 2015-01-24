% Combine data over multiple results to give single cleavage and gain estimates
% Uses B/(A+B) where B comes from MLigBT7W.QB  and A comes from MLigAT7.QA

function result=combinecleavages(data)
c=containers.Map();
for i=1:length(data.results)
  r=data.results{i};
  if isKey(c,r.tmpl)
    concs=c(r.tmpl);
  else
    concs=nan(1,4); % AX, BX, MX(A), MX(B)
  end
  if strcmp(r.type,'Lig') && isfield(r,'BX')
    concs(2)=r.BX.conc;
  end
  if strcmp(r.type,'Lig') && isfield(r,'AX')
    concs(1)=r.AX.conc;
  end
  if strcmp(r.type,'Lig') && isfield(r,'MX')
    if r.ligprefix(1)=='A'
      concs(3)=r.MX.conc;
    elseif r.ligprefix(1)=='A'
      concs(4)=r.MX.conc;
    end
  end
  if any(isfinite(concs))
    c(r.tmpl)=concs;
  end
end
tmpls=sort(c.keys);
result=[];
for i=1:length(tmpls)
  concs=c(tmpls{i});
  result=[result,struct('tmpl',tmpls{i},'unclvd',concs(1),'clvd',concs(2),'yieldM',nanmean(concs(3:4)))];
end
for i=1:length(result)
  result(i).yield=(result(i).clvd+result(i).unclvd);
  result(i).cleavage=result(i).clvd/result(i).yield;
end
