% Analyze an robot  run
% Usage: robotanalyze(z,samples)
%	z - OPD data from qPCR or miner data from minerread
%	samples - struct containing sample information -- formed by loading .m file outputf from python script for Robot
function robotanalyze(z,samples)
% Setup primers, ct0 is concentration of Ct=0 in nM
ct0M=5;
primers=struct('name','A','ct0',0.97*ct0M,'eff',1.9);
primers(end+1)=struct('name','B','ct0',0.97*ct0M,'eff',1.9);
primers(end+1)=struct('name','M','ct0',ct0M,'eff',1.9);
primers(end+1)=struct('name','T','ct0',1.996*ct0M,'eff',1.9);

qsel=strcmp({samples.plate},'qPCR');
if sum(qsel)<1
  error('Unable to find qPCR plate in samples');
end
name={samples(qsel).name};
namedil=[];
dilution=[]; dilrelative={};
primer={};
for i=1:length(name)
  str=name{i};
  dil=1;
  nm='';
  p='';
  while ~isempty(str)
    [token,str]=strtok(str,'.');
    %    if token(1)=='D' && all(isstrprop(token(2:end),'digit'))
    %      dil=dil*str2num(token(2:end));
    if isempty(str) && token(1)=='Q'
      p=token(2:end);
    elseif isempty(nm)
      nm=token;
    else
      nm=[nm,'.',token];
    end
  end
  name{i}=nm;
      
  if isempty(p)
    error('Unable to locate primer in sample "%s"',name{i});
  end
  % Calculation dilution based on volumes of ingredients
  snum=find(strcmp(name(i),{samples.name}));
  assert(~isempty(snum));
  [v,o]=sort(samples(snum).volumes,'descend');
  for k=1:length(o)
    nmk=samples(snum).ingredients{o(k)};
    if ~any(strcmp(nmk,{'Water','SSD','MPosRT'})) && ~strncmp(nmk,'MQ',2)  && ~strncmp(nmk,'MLig',4) && ~strncmp(nmk,'MStp',4)
      if nmk(1)=='M'
        rdilstr=samples(find(strcmp({samples.name},nmk))).concentration;
        if rdilstr(end)~='x'
          error('Uninterpretable dilution string for %s: %s\n', nmk, rdilstr);
        end
        rdil=str2num(rdilstr(1:end-1));
        nmk=nmk(2:end);
      else
        rdil=1;
      end
      dilution(i)=sum(v)/v(k)/rdil;
      dilrelative{i}=nmk;
      break;
    end
  end

  primer{i}=p;
  namedil(i)=dil;
end
well={samples(qsel).well};
usamp=unique(name);
sel1=cellfun(@(z) ~isempty(strfind(z,'spike')), usamp);
sel2=cellfun(@(z) ~isempty(strfind(z,'.L')), usamp);
usamp={usamp{sel1&~sel2},usamp{sel1&sel2},usamp{~sel1&~sel2},usamp{~sel1&sel2}};
sel3=cellfun(@(z) ~isempty(strfind(z,'Water')), usamp);
usamp={usamp{~sel3},usamp{sel3}};
unknownprimers=unique(primer(~ismember(primer,{primers.name})));
if ~isempty(unknownprimers)
  error('Includes unknown primers: %s\n',sprintf('%s ',unique(unknownprimers)));
end

% Get Cts
if isfield(z,'CT')
  ct=z.CT;
  ctwells=z.SampleNames;
else
  ct=ctcalc(z);
  ctwells=wellnames(z);
end

% Printer header lines
fprintf('%-35s\t%15s\t','Name','Dilution');
for p=1:length(primers)
  fprintf('%3s\t',primers(p).name);
end
for p=1:length(primers)
  fprintf('Ct(%1s)\t',primers(p).name);
end
for p=1:length(primers)
  fprintf('%7s\t',['[',primers(p).name,']']);
end
fprintf('Yield\tCleav%%\tTheo%%\n');

fprintf('%-35s\t%15s\t','Primer Settings:','');
for p=1:length(primers)
  fprintf('%3s\t%5.2f\t','',primers(p).eff);
end
for p=1:length(primers)
  fprintf('%7.2f\t',primers(p).ct0);
end
fprintf('\t\n');

% Data
data=nan(length(usamp),length(primers));
conc=nan(length(usamp),length(primers));
lastletter='?';
for i=1:length(usamp)
  dilsel=find(strcmp(name,usamp{i}),1);
  if usamp{i}(1)~=lastletter
    fprintf('\n');
    lastletter=usamp{i}(1);
  end
  fprintf('%-35s\t%-15s\t',usamp{i},sprintf('%s/%.0f',dilrelative{dilsel},dilution(dilsel)));
  for p=1:length(primers)
    sel=find(strcmp(name,usamp{i})&strcmp(primer,primers(p).name));
    if isempty(sel)
      fprintf('%3s\t','');
    else
      fprintf('%3s\t',well{sel});
    end
  end
  for p=1:length(primers)
    sel=find(strcmp(name,usamp{i})&strcmp(primer,primers(p).name));
    if isempty(sel)
      fprintf('%5s\t','');
    else
      index=find(strcmp(ctwells,well{sel}));
      if isempty(index)
        fprintf('%5s\t','Missing');
      else
        fprintf('%5.2f\t',ct(index));
        data(i,p)=ct(index);
        conc(i,p)=primers(p).eff^-ct(index)*primers(p).ct0*dilution(sel);
      end
    end
  end
  for p=1:length(primers)
    if isnan(conc(i,p))
      fprintf('%7s\t','');
    else
      fprintf('%7.2f\t',conc(i,p));
    end
  end
  % Yield
  if isnan(sum(conc(i,1:2)))
    fprintf('%6s\t','');
  else
    fprintf('%6.1f\t',sum(conc(i,1:2)));
  end
  % Cleavage
  if ~isempty(strfind(usamp{i},'.LB'))
    cleavage(i)=conc(i,2)/sum(conc(i,1:2));
  elseif ~isempty(strfind(usamp{i},'.LA'))
    cleavage(i)=conc(i,1)/sum(conc(i,1:2));
  else
    cleavage(i)=-min(conc(i,1:2))/sum(conc(i,1:2));
  end
  if isnan(cleavage(i))
    fprintf('     \t');
  else
    fprintf('%4.1f%%\t',cleavage(i)*100);
  end
  theofrac(i)=conc(i,4)/conc(i,3);
  if isnan(theofrac(i))
    fprintf('     \t');
  else
    fprintf('%5.2f%%\t',theofrac(i)*100);
  end
  fprintf('\n');
end
