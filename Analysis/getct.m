% Collect together the Ct's for each sample 
function result=getct(data,sampname)
if nargin<2
  sampnames={};
  allnames={data.samps(strcmp({data.samps.plate},'qPCR')).name};
  for i=1:length(allnames)
    qpos=strfind(allnames{i},'.Q');
    if length(qpos)~=1
      fprintf('Unable to find ".Q" in %s -- ignoring\n',allnames{i});
    else
      sampnames{end+1}=allnames{i}(1:qpos-1);
    end
  end
  sampnames=unique(sampnames);
  result={};
  for i=1:length(sampnames)
    result{end+1}=getct(data,sampnames{i});
  end
  return;
end

% Locate samples
sel=find(strncmp({data.samps.name},[sampname,'.Q'],length(sampname)+2));
if length(sel)==0
  fprintf('Unable to locate %s.Q*\n', sampname);
  result=struct();
  return;
end
result=struct('name',sampname);
% Split based on dots
dots=find([sampname,'.']=='.');
parts={};
pdot=1;
for i=1:length(dots)
  pt=sampname(pdot:dots(i)-1);
  if pt(1)~='D' && pt(1)~='R' && (pt(1)<'1' || pt(1)>'9')
    parts{end+1}=pt;
  end
  pdot=dots(i)+1;
end
result.tmpl=parts{1};
if length(parts)==1
  result.type='tmpl';
  result.cond='tmpl';
else
  if parts{2}(end)=='-'
    result.cond='-';
  elseif parts{2}(end)=='+'
    result.cond=parts{2};
  else
    result.cond='?';
  end

  if length(parts)==2
    result.type='T7';
  else
    if parts{end}(1)=='L'
      result.type='Lig';
      result.ligprefix=parts{end}(2:end);
    elseif length(parts{end})>=4 && strcmp(parts{end}(1:4),'MLig')
      result.type='Lig';
      result.ligprefix=parts{end}(5);
    else
      result.type=parts{end};
    end
  end
end

if ~data.useminer && isfield(data,'opd')
  if ~isfield(data.opd,'ct')
    data.opd=ctcalc(data.opd);
  end
end
  
for i=1:length(sel)
  samp=data.samps(sel(i));
  v=struct('samp',samp);
  if ~strcmp(v.samp.plate,'qPCR')
    error('%s is on plate %s, not qPCR plate\n', v.name, v.plate);
  end
  if ~strcmp(samp.name(length(sampname)+(1:2)),'.Q')
    error('Expected QPCR sample to start with "%s", but found "%s"\n',[sampname,'.Q'],samp.name);
  end
  v.primer=samp.name(length(sampname)+3:end);
  if length(v.primer)==1
    fprintf('Converting old style primer name "%s" to 2-letter code: ', v.primer);
    if v.primer(1)=='W'
      v.primer='WX';
    else
      v.primer=[v.primer,'S'];
    end
    fprintf('%s\n',v.primer);
  end
  
  if isfield(data,'md')
    well=find(strcmp(data.md.SampleNames,samp.well));
    if isempty(well)
      error('Unable to find well %s in Miner results\n', samp.well);
    end
    v.ctm=data.md.CT(well);
  end
  if isfield(data,'opd')
    v.well=wellnames2pos({samp.well});
    opdindex=find([data.opd.WIRT.platepos]==v.well);
    if isempty(opdindex)
      error('Unable to find platepos %d for well %s in data.opt.WIRT',v.well, samp.well);
    end
    v.cti=data.opd.ct(opdindex);
  end

  if data.useminer
    v.ct=v.ctm;
  elseif isfield(v,'cti')
    v.ct=v.cti;
  else
    fprintf('No data to find Ct\n');
    v.ct=nan;
  end

  if isfield(result,v.primer) && ~isempty(result.(v.primer))
    fprintf('Have multiple samples for primer %s\n', v.primer);
  end
  
  % Calculation dilution based on volumes of ingredients
  [vols,o]=sort(samp.volumes,'descend');
  for k=1:length(o)
    nmk=samp.ingredients{o(k)};
    if ~any(strcmp(nmk,{'Water','SSD','MPosRT'})) && ~strncmp(nmk,'MQ',2)  && ~strncmp(nmk,'MLig',4) && ~strncmp(nmk,'MStp',4)
      if nmk(1)=='M'
        rdilstr=data.samps(find(strcmp({data.samps.name},nmk))).concentration;
        if rdilstr(end)~='x'
          error('Uninterpretable dilution string for %s: %s\n', nmk, rdilstr);
        end
        rdil=str2num(rdilstr(1:end-1));
        nmk=nmk(2:end);
      else
        rdil=1;
      end
      dilution=sum(vols)/vols(k)/rdil;

      if isfield(result,'dilution')
        if result.dilution~=dilution || ~strcmp(result.dilrelative,nmk)
          error('Inconsistent dilution information for %s\n',v.samp.name);
        end
      else
        result.dilution=dilution;
        result.dilrelative=nmk;
      end
      break;
    end
  end
  if ~isfield(result,'dilution')
    result.dilution=1;
    result.dilrelative='None';
  end
  % Calculate concentrations
  p=data.primers.(v.primer);
  if isfinite(v.ct)
    v.conc=p.eff^-v.ct*p.ct0*result.dilution;
  else
    v.conc=nan;
  end

  result.(v.primer)=v;
end

% Calculate cleavage, yield, theofrac
% Cleavage
if strcmp(result.type,'Lig')
  if isfield(result,result.ligprefix)
    clvd=result.(result.ligprefix).conc;
  elseif isfield(result,[result.ligprefix,'S'])
    clvd=result.([result.ligprefix,'S']).conc;
  elseif isfield(result,[result.ligprefix,'X'])
    clvd=result.([result.ligprefix,'X']).conc;
  elseif isfield(result,[result.ligprefix,'W'])
    clvd=result.([result.ligprefix,'W']).conc;
  else
    error('Unable to locate ligation suffix %s or %sW\n', result.ligprefix, result.ligprefix);
  end
    
  fn=fieldnames(result);
  uprimer={};
  for i=1:length(fn)
    if length(fn{i})<=2 && fn{i}(1)~=result.ligprefix(1) && fn{i}(1)~='M'
      uprimer{end+1}=fn{i};
    end
  end
  if length(uprimer)>1
    error('%s: Unable to determine uncleaved prefix out of %d possibilities.\n', result.name, length(uprimer));
  elseif length(uprimer)==0
    error('%s: No potential uncleaved prefix\n', result.name);
  else
    uprimer=uprimer{1};
    unclvd=result.(uprimer).conc;
    result.cleavage=clvd/(clvd+unclvd);
    result.yield=clvd+unclvd;
  end
end

if isfield(result,'T') && isfield(result,'M')
  result.theofrac=result.T.conc/result.M.conc;
end
  
