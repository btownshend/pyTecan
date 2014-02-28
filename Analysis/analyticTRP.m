% Analyze an robot analyticTRP run
% Usage: analyticTRP(z,samples)
%	z - OPD data from qPCR
%	txtfile - filename for analyticTRP.txt file output by python script
function analyticTRP(z,txtfile)
% Parse robot dump file to figure out labels, wells
cmd=sprintf('grep ''\\.Q'' %s | sed -e ''s/^\\(.*\\)\\.Q\\(.*\\)\\[.*qPCR\\.\\([A-H][0-9]*\\),.*/\\1,\\2,\\3/'' >/tmp/qpcr.txt',txtfile);
[s,r]=system(cmd);
if s~=0
  error('%s: %s',cmd,r);
end
fd=fopen('/tmp/qpcr.txt','r');
layout=textscan(fd,'%[^,],%[^,],%s');
sample=layout{1};
primer=layout{2};
well=layout{3};
usamp=unique(sample);
uprimer=['A','B','M',unique(primer(~ismember(primer,{'A','B','M'})))];

% Get Cts
ct=ctcalc(z);
w=wellnames(z);
fprintf('%-20s\t','Sample');
for p=1:length(uprimer)
  fprintf('W(%s)\tCt(%s)\t',uprimer{p},uprimer{p});
end
for p=1:length(uprimer)
  fprintf('%5s\t',['[',uprimer{p},']']);
end
fprintf('Cleavage\t');
fprintf('\n');
data=nan(length(usamp),length(uprimer));
ct0=30000;   % Concentration of Ct=0 in pM
eff=2.0;  
for i=1:length(usamp)
  fprintf('%-20s\t',usamp{i});
  for p=1:length(uprimer)
    sel=find(strcmp(sample,usamp{i})&strcmp(primer,uprimer{p}));
    fprintf('%2s\t',well{sel});
    if isempty(sel)
      fprintf('NR\t');
    else
      index=find(strcmp(w,well{sel}));
      if isempty(index)
        fprintf('NW\t');
      else
        fprintf('%5.2f\t',ct(index));
        data(i,p)=ct(index);
        conc(i,p)=eff^-ct(index)*ct0;
      end
    end
  end
  for p=1:length(uprimer)
    fprintf('%6.2f\t',conc(i,p));
  end
  if ~isempty(strfind(usamp{i},'.LB.'))
    cleavage(i)=conc(i,2)/sum(conc(i,1:2));
  elseif ~isempty(strfind(usamp{i},'.LA.'))
    cleavage(i)=conc(i,1)/sum(conc(i,1:2));
  else
    cleavage(i)=nan;
  end
  if isnan(cleavage(i))
    fprintf('     \t');
  else
    fprintf('%4.1f%%\t',cleavage(i)*100);
  end
  fprintf('\n');
end
