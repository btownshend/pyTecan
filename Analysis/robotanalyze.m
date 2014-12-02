% Analyze TRP data
function data=robotanalyze(varargin)
defaults=struct('sampfile','','opdfile','','data',[],'refadj',true);
args=processargs(defaults,varargin);

if isempty(args.sampfile)
  if exist('./analyticTRP.m','file')
    args.sampfile='analyticTRP.m';
  elseif exist('./multispike.m','file')
    args.sampfile='multispike.m';
  elseif exist('./NGSTRP.m','file')
    args.sampfile='NGSTRP.m';
  else
    error('No sample file\n');
  end
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
      error('No OPD file found\n');
    elseif length(opdfile)>1
      error('More than one OPD file found\n');
    end
    opdfile=opdfile.name;
  else
    opdfile=args.opdfile;
  end
  fprintf('Loading qPCR data from %s\n', opdfile);
  opd=opdread(opdfile);
  data.opd=ctcalc(opd);

  % Setup primers, ct0 is concentration of Ct=0 in nM
  ct0M=2;
  data.primers=struct(...
      'AS',struct('ct0',0.97*ct0M,'eff',1.9),...
      'AW',struct('ct0',ct0M,'eff',1.9),...    # Old labelling
      'AX',struct('ct0',0.97*ct0M,'eff',1.7246),...
      'BS',struct('ct0',0.97*ct0M,'eff',1.9),...
      'BX',struct('ct0',0.97*ct0M,'eff',1.8744),...
      'MS',struct('ct0',ct0M,'eff',1.9),...
      'MX',struct('ct0',ct0M,'eff',1.9),...
      'WX',struct('ct0',ct0M,'eff',1.9),...
      'WS',struct('ct0',ct0M,'eff',1.9),...
      'REF',struct('ct0',ct0M,'eff',1.9235),...
      'TS',struct('ct0',1.996*ct0M,'eff',1.9));
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

  minerfile=dir('./Miner_*_Analyzed_Data.txt');
  if isempty(minerfile)
    fprintf('No Miner analysis file found\n');
    data.useminer=false;
  elseif length(minerfile)>1
    fprintf('More than one miner file found - ignoring\n');
    data.useminer=false;
  else
    data.md=minerload(minerfile.name);
    data.useminer=true;
  end
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

% Run analysis
data.results=getct(data);
if args.refadj
  d2=adjustdilutions(data);
else
  d2=data;
end
d3=getcleavages(d2);
robotdump(d3);

% Make some plots...
robotplot(d3);
data=d3;
