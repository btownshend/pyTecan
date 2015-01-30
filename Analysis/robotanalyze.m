% Analyze TRP data
function data=robotanalyze(varargin)
defaults=struct('sampfile','','opdfile','','data',[],'refadj',false,'refconc',[],'useinternal',false,'minerfile',[]);
args=processargs(defaults,varargin);

if isempty(args.sampfile)
  flist=dir('*.gem');
  for i=1:length(flist)
    mfilename=strrep(flist(i).name,'.gem','.m');
    if exist(mfilename,'file')
      args.sampfile=mfilename;
      break;
    end
  end
  if isempty(args.sampfile)
    error('No sample file (use ''sampfile'' optional arg to specify)\n');
  else
    fprintf('Loading robot setup from %s\n', args.sampfile);
  end
end

if ~isempty(args.refconc)
  args.refadj=true;
end

if ~isempty(args.data)
  data=args.data;
else
  % Load sample layout
  eval(strrep(args.sampfile,'.m',''));
  data=struct('samps',samps,'changed',true,'sampfile',args.sampfile);
  
  % Load qPCR data
  if isempty(args.opdfile)
    opdfile=dir('*.opd');
    if isempty(opdfile)
      fprintf('No local OPD file found, checking in Smolke server\n');
      opdfile=opdlocate();
    elseif length(opdfile)>1
      error('More than one OPD file found (use ''opdfile'' optional arg to specify)\n');
    else
      opdfile=opdfile.name;
    end
  else
    opdfile=args.opdfile;
  end
  fprintf('Loading qPCR data from %s\n', opdfile);
  opd=opdread(opdfile);
  data.opd=ctcalc(opd);

  if args.useinternal
    data.useminer=false;
  else
    if isempty(args.minerfile)
      minerfile=dir('./Miner_*_Analyzed_Data.txt');
    else
      minerfile=dir(args.minerfile);
    end
    if isempty(minerfile)
      fprintf('No Miner analysis file found\n');
      data.useminer=false;
    elseif length(minerfile)>1
      fprintf('More than one miner file found - ignoring\n');
      data.useminer=false;
    else
      fprintf('Loading PCR-Miner data from %s\n', minerfile.name);
      data.md=minerload(minerfile.name);
      data.useminer=true;
    end
  end
  
  % Setup primers, ct0 is concentration of nucleotides at Ct=0 in uM
  if data.useminer
    ct0M=2.35*10/350;
  else
    ct0M=2.35;
  end
  eff=1.92;
  data.primers=struct(...
      'AS',struct('ct0',ct0M,'eff',eff),...
      'AW',struct('ct0',ct0M,'eff',eff),...    # Old labelling
      'AX',struct('ct0',ct0M,'eff',eff),...
      'BS',struct('ct0',ct0M,'eff',eff),...
      'BX',struct('ct0',ct0M,'eff',eff),...
      'MS',struct('ct0',ct0M,'eff',eff),...
      'MX',struct('ct0',ct0M,'eff',eff),...
      'WX',struct('ct0',ct0M,'eff',eff),...
      'WS',struct('ct0',ct0M,'eff',eff),...
      'REF',struct('ct0',ct0M,'eff',eff),...
      'TS',struct('ct0',ct0M,'eff',eff));
  data.primers.WS2=data.primers.WS;
  data.primers.WS3=data.primers.WS;
  data.primers.AS2=data.primers.AS;
  data.primers.AS3=data.primers.AS;
  data.primers.AX2=data.primers.AX;
  data.primers.AX3=data.primers.AX;
  data.primers.BS2=data.primers.BS;
  data.primers.BS3=data.primers.BS;
  data.primers.BX2=data.primers.BX;
  data.primers.BX3=data.primers.BX;
end

if data.useminer && ~isfield(data,'md')
  sel=find(strcmp({data.samps.plate},'qPCR'));
  samps=wellnames2pos({data.samps(sel).well});
  minerdump(data.opd,samps);
  fprintf('Submit above data to miner\n');
  while true
    jobid=input('Enter Miner job id: ','s');
    if isempty(jobid)
      continue;
    end
    % Load Miner data
    try
      data.md=minerload(jobid);
      data.jobid=jobid;
      data.changed=true;
      break;
    catch me
      fprintf('Error loading data: %s\n',me.message);
    end
  end
end
  
% if data.changed
%   % Save data
%   fprintf('Saving data in %s\n',savefile);
%   save(savefile,'-struct','data');
%   data.changed=false;
% end

% Load length information
fd=fopen('seqs.csv','r');
lnum=1;
data.lengths=[];
if fd>0
  while true
    % Read name, sequence
    line=fgetl(fd);
    if line==-1
      break;
    end
    commas=strfind(line,',');
    if length(commas)<1
      fprintf('Syntax error at line %d of seqs.csv:  expected at least 1 comma\n');
      continue;
    end
    name=line(1:commas(1)-1);
    lens=struct('MX',[],'WX',[],'AX',[],'BX',[]);
    commas(end+1)=length(line)+1;
    for k=2:length(commas)
      seq=line(commas(k-1)+1:commas(k)-1);
      seq=upper(strrep(seq,' ',''));
      if ~strncmp(seq,'GCTGTC',6)
        fprintf('Bad seq "%s"\n  Expected GCTGTC*GACAGC\n',seq);
        continue;
      end
      lens.WX(end+1)=35+length(seq)+17;
      lens.AX(end+1)=56+length(seq)+17;
      lens.BX(end+1)=56+length(seq)+17;
      mstart=strfind(seq,'TCCGGTCTGATGAGTCC');
      if isempty(mstart)
        fprintf('Unable to locate MidPrimer in %s: %s\n', name,seq);
      else
        lens.MX(end+1)=length(seq)+1-mstart(1)+17;
      end
    end
    fns=fieldnames(lens);
    for i=1:length(fns)
      fn=fns{i};
      if length(lens.(fn))>0
        data.lengths=[data.lengths,struct('samp',name,'seq',seq,'ligation','*','primers',fn,'length',round(mean(lens.(fn))))];
        fprintf('%s: %s=%d\n', data.lengths(end).samp,data.lengths(end).primers,data.lengths(end).length);
      end
    end
  end
  fclose(fd);
else
  % Try lengths.csv instead
  fd=fopen('lengths.csv','r');
  if fd<0
    error('Unable to open seqs.csv or lengths.csv');
  end
  ts=textscan(fd,'%[^,],%[^,],%[^,],%d');
  fclose(fd);
  data.lengths=struct('samp',ts{1},'ligation',ts{2},'primers',ts{3},'length',num2cell(ts{4}));
end

% Run analysis
data.results=getct(data);
if args.refadj
  d2=adjustdilutions(data,args.refconc);
else
  d2=data;
end
d3=getcleavages(d2);
d3.summary=combinecleavages(d3);
robotdump(d3);

% Make some plots...
robotplot(d3);
replicatediff(d3);
data=d3;
