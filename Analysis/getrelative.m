% Get all wells relative to a given component (e.g. MT7)
% Only include ones that have all components in othercomp
function ss=getrelative(samps,comp,othercomp,only)
ss=[];
if nargin<4
  only=false;
end
if nargin>2 && ~iscell(othercomp)
  othercomp={othercomp};
end
for i=1:length(samps)
  s=samps(i);
  if strcmp(s.plate,'qPCR')
    if nargin>2
      if ~all(ismember(othercomp,s.ingredients))
        continue;
      end
      if only && length(s.ingredients)~=length(othercomp)+1
        continue;
      end
    end
    ind=find(strcmp(s.ingredients,comp),1);
    if ~isempty(ind)
      s.dil=sum(s.volumes)/s.volumes(ind);
      ss=[ss,s];
    end
  end
end
