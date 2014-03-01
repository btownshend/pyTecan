% Analyze a robot  run
% Usage: robotanalyze(data)
%	data.results - Cell array of Ct/Conc data
function robotdump(data)

% Printer header lines
primers=fieldnames(data.primers);
psel=false(1,length(primers));
for i=1:length(primers)
  psel(i)=any(cellfun(@(z) isfield(z,primers{i}), data.results));
end
primers=primers(psel);

c=1;
colbreak=[];
tbl{1,c}='Name'; c=c+1;
tbl{1,c}='Dilution'; c=c+1;
colbreak(c-1)=1;
for p=1:length(primers)
  tbl{1,c}=primers{p};
  c=c+1;
end
colbreak(c-1)=1;
for p=1:length(primers)
  tbl{1,c}=sprintf('Ct(%s)',primers{p});
  tbl{2,c}=sprintf('%.2f',data.primers.(primers{p}).eff);
  c=c+1;
end
colbreak(c-1)=1;
for p=1:length(primers)
  tbl{1,c}=['[',primers{p},']'];
  tbl{2,c}=sprintf('%.2f',data.primers.(primers{p}).ct0);
  c=c+1;
end
colbreak(c-1)=1;
tbl{1,c}='Yield'; c=c+1;
colbreak(c-1)=1;
tbl{1,c}='Clv%'; c=c+1;
colbreak(c-1)=1;
if ismember('T',primers)
  tbl{1,c}='Theo%'; c=c+1;
  colbreak(c-1)=1;
end


% Data
lasttmpl='?';
rowbreak=[];
for i=1:length(data.results)
  r=i+2;
  usamp=data.results{i};
  dot=strfind([usamp.name,'.'],'.');
  tmpl=usamp.name(1:dot(1)-1);
  if ~strcmp(tmpl,lasttmpl)
    rowbreak(r-1)=1;
    lasttmpl=tmpl;
  else
    rowbreak(r-1)=0;
  end

  c=1;
  tbl{r,c}=usamp.name;c=c+1;
  tbl{r,c}=sprintf('%s/%.0f',usamp.dilrelative,usamp.dilution);c=c+1;
  for p=1:length(primers)
    if isfield(usamp,primers{p})
      tbl{r,c}=usamp.(primers{p}).samp.well;
    end
    c=c+1;
  end
  for p=1:length(primers)
    if isfield(usamp,primers{p})
      tbl{r,c}=sprintf('%.2f',usamp.(primers{p}).ct);
    end
    c=c+1;
  end
  for p=1:length(primers)
    if isfield(usamp,primers{p})
      tbl{r,c}=sprintf('%.2f',usamp.(primers{p}).conc);
    end
    c=c+1;
  end
  % Yield
  if isfield(usamp,'yield')
    tbl{r,c}=sprintf('%.1f',usamp.yield);
  end
  c=c+1;

  % Cleavage
  if isfield(usamp,'cleavage')
    tbl{r,c}=sprintf('%.1f%%',usamp.cleavage*100);
  end
  c=c+1;

  if ismember('T',primers)
    if isfield(usamp,'theofrac')
      tbl{r,c}=sprintf('%.2f%%',usamp.theofrac*100);
    end
    c=c+1;
  end
end
rowbreak(size(tbl,1))=1;

width=[];
for c=1:size(tbl,2)
  width(c)=max(cellfun(@(z) length(z), tbl(:,c)));
end

for r=1:size(tbl,1)
  for c=1:size(tbl,2)
    if c<=2
      fprintf(sprintf('%%-%d.%ds',width(c),width(c)),tbl{r,c});
    else
      fprintf(sprintf('%%%d.%ds',width(c),width(c)),tbl{r,c});
    end
    if colbreak(c)
      fprintf('|');
    else
      fprintf(' ');
    end
  end
  fprintf('\n');
  if rowbreak(r)
    for c=1:size(tbl,2)
      fprintf(sprintf('%%%d.%ds',width(c),width(c)),repmat('-',1,max(width)));
      if colbreak(c)
        fprintf('+');
      else
        fprintf('-');
      end
    end
    fprintf('\n');
  end
end
if isfield(data,'opd')
  fprintf('* OPD=%s\n', data.opd.filename);
end
if data.useminer
  fprintf('* Ct''s from PCR-Miner\n');
else
  fprintf('* Ct''s from internal computation\n');
end
