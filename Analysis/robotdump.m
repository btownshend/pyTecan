% Analyze a robot  run
% Usage: robotanalyze(data)
%	data.results - Cell array of Ct/Conc data
function robotdump(data,csv)
if nargin<2
  csv=0;
end

fprintf('Note: concentrations are relative to sample tubes, not final concentrations in T7\n');
% Print header lines
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
tbl{1,c}='DilChain'; c=c+1;
colbreak(c-1)=1;
for p=1:length(primers)
  tbl{1,c}=primers{p};
  c=c+1;
end
colbreak(c-1)=1;
for p=1:length(primers)
  tbl{1,c}=sprintf('L(%s)',primers{p});
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
tbl{1,c}='Yield';
tbl{2,c}='nM';
c=c+1;
colbreak(c-1)=1;
tbl{1,c}='RNA';
tbl{2,c}='Gain'; c=c+1;
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
  if strcmp(usamp.type,'tmpl') && isfield(data,'summary')
    % Use summary values of cleavage, yield
    sel=find(strcmp(usamp.tmpl,{data.summary.tmpl}));
    if length(sel)==1
      s=data.summary(sel);
      usamp.yield=s.yield;
      usamp.cleavage=s.cleavage;
      if isfield(usamp,'MX')
        usamp.rnagain=s.yield/usamp.MX.conc;
      end
    else
      fprintf('Unable to find summary data for template %s\n', usamp.tmpl);
    end
  end
  c=1;
  tbl{r,c}=usamp.name;c=c+1;
  tbl{r,c}=sprintf('%s/%.0f',usamp.dilrelative,usamp.dilution);c=c+1;
  tbl{r,c}=sprintf('%.1f/%.1f/%.1f',usamp.dilchain);c=c+1;
  for p=1:length(primers)
    if isfield(usamp,primers{p})
      tbl{r,c}=usamp.(primers{p})(1).samp.well;
      for rep=2:length(usamp.(primers{p}))
        tbl{r,c}=[tbl{r,c},'/',usamp.(primers{p})(rep).samp.well];
      end
    end
    c=c+1;
  end
  for p=1:length(primers)
    if isfield(usamp,primers{p})
      tbl{r,c}=sprintf('%d',usamp.(primers{p})(1).length);
    end
    c=c+1;
  end
  for p=1:length(primers)
    if isfield(usamp,primers{p})
      tbl{r,c}=sprintf('%.2f',usamp.(primers{p})(1).ct);
      for rep=2:length(usamp.(primers{p}))
        tbl{r,c}=[tbl{r,c},'/',sprintf('%.2f',usamp.(primers{p})(rep).ct)];
      end
    end
    c=c+1;
  end
  for p=1:length(primers)
    if isfield(usamp,primers{p})
      tbl{r,c}=sprintf('%.2f',usamp.(primers{p})(1).conc);
    end
    c=c+1;
  end
  % Yield
  if isfield(usamp,'yield')
    tbl{r,c}=sprintf('%.1f',usamp.yield);
  end
  c=c+1;

  % RNAgain
  if isfield(usamp,'rnagain')
    tbl{r,c}=sprintf('%.1f',usamp.rnagain);
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
    if csv
      fprintf(',');
    elseif colbreak(c)
      fprintf('|');
    else
      fprintf(' ');
    end
  end
  fprintf('\n');
  if rowbreak(r) && ~csv
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
