% Analyze TRP data
function data=robotanalyze(varargin)
defaults=struct('sampfile','','data',[]);
args=processargs(defaults,varargin);

if isempty(args.sampfile)
  if exist('./analyticTRP.m','file')
    args.sampfile='analyticTRP.m'
  elseif exist('./multispike.m','file')
    args.sampfile='multispike.m'
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
      'A',struct('ct0',0.97*ct0M,'eff',1.9),...
      'B',struct('ct0',0.97*ct0M,'eff',1.9),...
      'M',struct('ct0',ct0M,'eff',1.9),...
      'T',struct('ct0',1.996*ct0M,'eff',1.9));

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
tmpls=sort(unique(cellfun(@(z) z.tmpl, data.results,'UniformOutput',false)));
conds=sort(unique(cellfun(@(z) z.cond, data.results,'UniformOutput',false)));
cleavage=nan(length(tmpls),length(conds));
yield=nan(length(tmpls),length(conds));
tconc=nan(length(tmpls),length(conds));
labels={};
for i=1:length(tmpls)
  tmpl=tmpls{i};
  tsel=cellfun(@(z) strcmp(z.tmpl,tmpl),data.results);
  for j=1:length(conds)
    cond=conds{j};
    csel=cellfun(@(z) strcmp(z.tmpl,tmpl)&strcmp(z.cond,cond),data.results);
    r=data.results(csel);
    ligsel=cellfun(@(z) strcmp(z.type,'Lig'), r);
    if sum(ligsel)>1
      fprintf('Found %d entries for %s/%s/Lig, expected only 1\n', sum(ligsel),tmpl,cond);
    end
    if sum(ligsel)==1
      clvd=r{ligsel}.(r{ligsel}.ligsuffix).conc;
      total=r{ligsel}.A.conc+r{ligsel}.B.conc;
      cleavage(i,j)=clvd/total;
      yield(i,j)=total;
    end
    t7sel=cellfun(@(z) strcmp(z.type,'T7'), r);
    if sum(t7sel)==0
      t7sel=cellfun(@(z) strcmp(z.type,'tmpl'), r);
    end
    if sum(t7sel)==1
      if isfield(r{t7sel},'M')
        tconc(i,j)=r{t7sel}.M.conc;
      elseif r{ligsel}.ligsuffix=='A' && isfield(r{t7sel},'B')
        tconc(i,j)=r{t7sel}.B.conc;
      elseif r{ligsel}.ligsuffix=='B' && isfield(r{t7sel},'A')
        tconc(i,j)=r{t7sel}.A.conc;
      end
    end
  end
  labels{i}=tmpl;
end

setfig('analyze'); clf;
nx=1;ny=4;pnum=1;
ny=any(isfinite(cleavage(:)))+any(isfinite(yield(:)))+any(isfinite(tconc(:)))+any(any(isfinite(tconc+yield)));

sel=any(isfinite(cleavage'));
if any(sel)
  subplot(ny,nx,pnum); pnum=pnum+1;
  csel=any(isfinite(cleavage));
  bar(cleavage(sel,csel)*100);
  ylabel('Cleavage (%)');
  xlabel('Sample');
  set(gca,'XTick',1:sum(sel));
  c=axis;c(2)=sum(sel)+1;axis(c);
  set(gca,'XTickLabel',labels(sel));
  legend(conds(csel));
  title('Cleavage');
  xticklabel_rotate;
end

sel=any(isfinite(yield'));
if any(sel)
  subplot(ny,nx,pnum); pnum=pnum+1;
  csel=any(isfinite(yield));
  bar(yield(sel,csel));
  ylabel('RNA Yield (nM)');
  xlabel('Sample');
  set(gca,'XTick',1:sum(sel));
  c=axis;c(2)=sum(sel)+1;axis(c);
  set(gca,'XTickLabel',labels(sel));
  set(gca,'YScale','log');
  legend(conds(csel));
  title('Yield');
  c=axis; c(3)=1; c(4)=max(max(yield(sel,csel)))*1.1; axis(c);
  xticklabel_rotate;
end

sel=any(isfinite(tconc'));
if any(sel)
  subplot(ny,nx,pnum); pnum=pnum+1;
  csel=any(isfinite(tconc));
  bar(tconc(sel,csel));
  ylabel('Template Conc (nM)');
  xlabel('Sample');
  set(gca,'XTick',1:sum(sel));
  c=axis;c(2)=sum(sel)+1;axis(c);
  set(gca,'XTickLabel',labels(sel));
  set(gca,'YScale','log');
  legend(conds(csel));
  title('Template Conc');
  c=axis; c(3)=0.1; axis(c);
  xticklabel_rotate;
end

sel=any(isfinite(tconc')&isfinite(yield'));
if any(sel)
  subplot(ny,nx,pnum); pnum=pnum+1;
  csel=any(isfinite(tconc)&isfinite(yield));
  bar(yield(sel,csel)./tconc(sel,csel));
  ylabel('RNA Gain (x)');
  xlabel('Sample');
  set(gca,'XTick',1:sum(sel));
  c=axis;c(2)=sum(sel)+1;axis(c);
  set(gca,'XTickLabel',labels(sel));
  legend(conds(csel));
  title('RNA Gain');
  xticklabel_rotate;
end
d=pwd;
d=d(max(strfind(d,'/'))+1:end);
if data.useminer
  suptitle(sprintf('Miner results for %s',d));
else
  suptitle(sprintf('Internal results for %s',d));
end
  

% A+B vs B
setfig('MScale');clf;
x=[];y=[];z=[];
for i=1:length(data.results)
  if isfield(data.results{i},'A') & isfield(data.results{i},'B') & isfield(data.results{i},'M')
    x(end+1)=data.results{i}.A.conc;
    y(end+1)=data.results{i}.B.conc;
    z(end+1)=data.results{i}.M.conc;
  end
end
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
