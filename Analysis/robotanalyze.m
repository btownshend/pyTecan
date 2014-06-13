% Analyze TRP data
function data=robotanalyze(varargin)
defaults=struct('sampfile','','data',[]);
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
  opdfile=dir('*.opd');
  if isempty(opdfile)
    fprintf('No OPD file found\n');
  elseif length(opdfile)>1
    fprintf('More than one OPD file found\n');
  else
    fprintf('Loading qPCR data from %s\n', opdfile.name);
    opd=opdread(opdfile.name);
    data.opd=ctcalc(opd);
  end

  % Setup primers, ct0 is concentration of Ct=0 in nM
  ct0M=2;
  data.primers=struct(...
      'AS',struct('ct0',0.97*ct0M,'eff',1.9),...
      'AW',struct('ct0',ct0M,'eff',1.9),...    # Old labelling
      'AX',struct('ct0',0.97*ct0M,'eff',1.9),...
      'BS',struct('ct0',0.97*ct0M,'eff',1.9),...
      'BX',struct('ct0',0.97*ct0M,'eff',1.9),...
      'MS',struct('ct0',ct0M,'eff',1.9),...
      'WX',struct('ct0',ct0M,'eff',1.9),...
      'WS',struct('ct0',ct0M,'eff',1.9),...
      'TS',struct('ct0',1.996*ct0M,'eff',1.9));
  data.primers.WS2=data.primers.WS;
  data.primers.WS3=data.primers.WS;
  data.primers.AS2=data.primers.AS;
  data.primers.AS3=data.primers.AS;
  data.primers.BS2=data.primers.BS;
  data.primers.BS3=data.primers.BS;

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
robotdump(data);

% Make some plots...

% Bar graph of cleavage
tmpls=sort(unique(cellfun(@(z) strrep(z.tmpl,'-spike',''), data.results,'UniformOutput',false)));
conds=cellfun(@(z) z.cond, data.results,'UniformOutput',false);
spike=cellfun(@(z) ~isempty(strfind(z.tmpl,'spike')), data.results);
fspike=find(spike);
for i=1:length(fspike)
  conds{fspike(i)}=[conds{fspike(i)},' (spike)'];
end
conds=sort(unique(conds));
cleavage=nan(length(tmpls),length(conds));
yield=nan(length(tmpls),length(conds));
tconc=nan(length(tmpls),length(conds));
labels={};
for i=1:length(tmpls)
  tmpl=tmpls{i};
  tsel=cellfun(@(z) strcmp(z.tmpl,tmpl),data.results);
  for j=1:length(conds)
    cond=strrep(conds{j},' (spike)','');
    spike=~isempty(strfind(conds{j},'(spike)'));
    if spike
      csel=cellfun(@(z) strcmp(z.tmpl,[tmpl,'-spike'])&strcmp(z.cond,cond),data.results);
    else
      csel=cellfun(@(z) strcmp(z.tmpl,tmpl)&strcmp(z.cond,cond),data.results);
    end
    r=data.results(csel);
    ligsel=cellfun(@(z) strcmp(z.type,'Lig'), r);
    if sum(ligsel)>1
      fprintf('Found %d entries for %s/%s/Lig, expected only 1\n', sum(ligsel),tmpl,cond);
    end
    if sum(ligsel)==1
      cleavage(i,j)=r{ligsel}.cleavage;
      yield(i,j)=r{ligsel}.yield;
    end
    t7sel=cellfun(@(z) strcmp(z.type,'T7'), r);
    if sum(t7sel)==0
      t7sel=cellfun(@(z) strcmp(z.type,'tmpl'), r);
    end
    if sum(t7sel)==1
      % Figure out correct field for template concentration
      if isfield(r{t7sel},'M')
        tconc(i,j)=r{t7sel}.M.conc;
      elseif sum(ligsel)==1
        if r{ligsel}.ligprefix(1)~='B' && isfield(r{t7sel},'BS')
          tconc(i,j)=r{t7sel}.BS.conc;
        elseif r{ligsel}.ligprefix(1)~='B' && isfield(r{t7sel},'BX')
          tconc(i,j)=r{t7sel}.BX.conc;
        elseif r{ligsel}.ligprefix(1)~='A' && isfield(r{t7sel},'AS')
          tconc(i,j)=r{t7sel}.AS.conc;
        elseif r{ligsel}.ligprefix(1)~='A' && isfield(r{t7sel},'AX')
          tconc(i,j)=r{t7sel}.AX.conc;
        elseif r{ligsel}.ligprefix(1)~='W' && isfield(r{t7sel},'WS')
          tconc(i,j)=r{t7sel}.WS.conc;
        elseif r{ligsel}.ligprefix(1)~='W' && isfield(r{t7sel},'WX')
          tconc(i,j)=r{t7sel}.WX.conc;
        else
          fprintf('Unable to identify primers for template %s with ligation %s\n', r{t7sel}.name, r{ligsel}.name);
        end
      end
    end
  end
  labels{i}=tmpl;
end

setfig('analyze'); clf;
nx=1;pnum=1;
ny=any(isfinite(cleavage(:)))+any(isfinite(yield(:)))+any(isfinite(tconc(:)))+any(any(isfinite(tconc+yield)))+1;

sel=any(isfinite(cleavage),2);
if any(sel)
  if pnum==ny-1
    subplot(ny,nx,pnum:pnum+1);
  else
    subplot(ny,nx,pnum); 
  end
  pnum=pnum+1;
  csel=any(isfinite(cleavage));
  bar(cleavage(sel,csel)*100);
  ylabel('Cleavage (%)');
  c=axis;c(2)=sum(sel)+1;axis(c);
  if pnum==2
    legend(conds(csel));
  end
  title('Cleavage');
  if ny==pnum
    xlabel('Sample');
    set(gca,'XTick',1:sum(sel));
    set(gca,'XTickLabel',labels(sel));
    xticklabel_rotate;
  end
end

sel=any(isfinite(yield),2);
if any(sel)
  if pnum==ny-1
    subplot(ny,nx,pnum:pnum+1);
  else
    subplot(ny,nx,pnum); 
  end
  pnum=pnum+1;
  csel=any(isfinite(yield));
  bar(yield(sel,csel));
  ylabel('RNA Yield (nM)');
  c=axis;
  c(2)=sum(sel)+1;
  c(3)=0; c(4)=max(max(yield(sel,csel)))*1.1; 
  axis(c);
  if pnum==2
    legend(conds(csel));
  end
  title('Yield');
  if ny==pnum
    xlabel('Sample');
    set(gca,'XTick',1:sum(sel));
    set(gca,'XTickLabel',labels(sel));
    xticklabel_rotate;
  end
end

sel=any(isfinite(tconc),2);
if any(sel)
  if pnum==ny-1
    subplot(ny,nx,pnum:pnum+1);
  else
    subplot(ny,nx,pnum); 
  end
  pnum=pnum+1;
  csel=any(isfinite(tconc));
  bar(tconc(sel,csel));
  ylabel('Template Conc (nM)');
  c=axis;c(2)=sum(sel)+1;c(3)=0;axis(c);
  if pnum==2
    legend(conds(csel));
  end
  title('Template Conc');
  if ny==pnum
    xlabel('Sample');
    set(gca,'XTick',1:sum(sel));
    set(gca,'XTickLabel',labels(sel));
    xticklabel_rotate;
  end
end

sel=any(isfinite(tconc)&isfinite(yield),2);
if any(sel)
  if pnum==ny-1
    subplot(ny,nx,pnum:pnum+1);
  else
    subplot(ny,nx,pnum); 
  end
  pnum=pnum+1;
  csel=any(isfinite(tconc)&isfinite(yield));
  bar(yield(sel,csel)./tconc(sel,csel));
  ylabel('RNA Gain (x)');
  c=axis;c(2)=sum(sel)+1;axis(c);
  if pnum==2
    legend(conds(csel));
  end
  title('RNA Gain');
  if ny==pnum
    xlabel('Sample');
    set(gca,'XTick',1:sum(sel));
    set(gca,'XTickLabel',labels(sel));
    xticklabel_rotate;
  end
end
d=pwd;
d=d(max(strfind(d,'/'))+1:end);
if data.useminer
  suptitle(sprintf('Miner results for %s',d));
else
  suptitle(sprintf('Internal results for %s',d));
end
  

% A+B vs B
x=[];y=[];z=[];
for i=1:length(data.results)
  if isfield(data.results{i},'A') & isfield(data.results{i},'B') & isfield(data.results{i},'M')
    x(end+1)=data.results{i}.A.conc;
    y(end+1)=data.results{i}.B.conc;
    z(end+1)=data.results{i}.M.conc;
  end
end
if length(x)>1
  setfig('MScale');clf;
  loglog(x,y,'o');
  hold on
  for i=1:length(x)
    sc=z(i)/(x(i)+y(i));
    plot(x(i)*sc,y(i)*sc,'x');
    if sc>1
      col='g';
    else
      col='r';
    end
    plot(x(i)*[1,sc],y(i)*[1,sc],col);
  end
  c=axis;
  legend('(A,B)','(MA/(A+B),MB/(A+B))');
  xlabel('[A] (nM)');
  ylabel('[B] (nM)');
  title('M vs A+B');
  axis equal
  axis([0,max([x,y])*1.1,0,max([x,y])*1.1]);
end

r=data.results;
theosel=cellfun(@(z) isfield(z,'theofrac') && ~isempty(strfind(z.tmpl,'spike')), r);
if sum(theosel)>0
  setfig('Theofrac');clf;
  theofrac=cellfun(@(z) z.theofrac, r(theosel));
  bar(theofrac*100);
  set(gca,'XTick',1:sum(theosel));
  c=axis;c(2)=sum(theosel)+1;axis(c);
  labels=cellfun(@(z) z.tmpl, r(theosel),'UniformOutput',false);
  set(gca,'XTickLabel',labels);
  ylabel('Fraction with Theo Aptamer (%)');
  xticklabel_rotate;
  title('Frac(theo) in spike-in');
end

