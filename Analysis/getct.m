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

if ~data.useminer && isfield(data,'opd')
  if ~isfield(data.opd,'ct')
    data.opd=ctcalc(data.opd);
  end
end
  
for i=1:length(sel)
  samp=data.samps(sel(i));
  v=robotidentify(samp);

  % At this point, all fields should be identical for all with sel (except primer)
  if i==1
    result=rmfield(v,'primer');
    result.name=sampname;
  else
    if ~strcmp(result.tmpl,v.tmpl)
      error('Different templates for same sample: %s vs. %s\n', result.tmpl, v.tmpl);
    end
    if ~strcmp(result.type,v.type)
      error('Different types for same sample: %s vs. %s\n', result.type, v.type);
    end
  end

  if ~strcmp(v.samp.plate,'qPCR')
    error('%s is on plate %s, not qPCR plate\n', v.name, v.plate);
  end
  if length(v.primer)==1
    fprintf('In %s, converting old style primer name "%s" to 2-letter code: ', samp.name, v.primer);
    if ~isempty(strfind(samp.name,'_X'))
      v.primer=[v.primer,'X'];
    elseif ~isempty(strfind(samp.name,'_S'))
      v.primer=[v.primer,'S'];
    else
      fprintf('Unable to determine whether this sample should have an X or an S suffix\n');
      keyboard;
    end
    fprintf('%s\n',v.primer);
  end
  
  % Lookup length of qPCR product
  v.length=nan;
  if isfield(data,'lengths')
    nsel=false(1,length(data.lengths));
    for k=1:length(data.lengths)
      if strncmp(data.lengths(k).samp,v.tmpl,length(data.lengths(k).samp))
        nsel(k)=true;
      end
    end
    psel=strcmp({data.lengths.primers},v.primer) ;
    lsel=nsel&psel;
    if sum(lsel)==0
      fprintf('%s/%s not found in data.lengths\n',v.tmpl, v.primer);
    elseif sum(lsel)>1
      fsel=find(lsel);
      lsel2=[];
      for i=1:length(fsel)
        if data.lengths(fsel(i)).ligation~='*'
          ss=strfind(v.samp.name,data.lengths(fsel(i)).ligation);
          if isempty(ss)
            continue;
          end
        end
        lsel2=[lsel2,fsel(i)];
      end
      if length(lsel2)>1
        fprintf('%s/%s has duplicates in data.lengths\n',v.tmpl, v.primer);
        keyboard
      elseif length(lsel2)<1
        fprintf('%s/%s not found in data.lengths that match ligation\n',v.tmpl, v.primer);
      else
        v.length=data.lengths(lsel2).length;
      end
    else
      v.length=data.lengths(lsel).length;
      %      fprintf('%s/%s has length=%d\n',v.tmpl, v.primer,v.length);
    end
  else
    fprintf('Data is missing primer lengths field\n');
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

  % Calculation dilution based on volumes of ingredients
  [vols,o]=sort(samp.volumes,'descend');
  map=containers.Map();
  for k=1:length(o)
    nmk=samp.ingredients{o(k)};
    map(nmk)=vols(k);
    if ~any(strcmp(nmk,{'SSD','MPosRT','MNegRT'})) && ~strncmp(upper(nmk),'WATER',5) && ~strncmp(nmk,'MQ',2)  && ~strncmp(nmk,'MLig',4) && ~strncmp(nmk,'MStp',4)
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
  dilchain=nan(1,3);   % Chain is Stop->RT, RT->Lig, Lig->QPCR
  if isKey(map,'MStpX') && isKey(map,'MPosRT')
    dilchain(1)=(map('MPosRT')*2)/(map('MStpX')*2);
  elseif isKey(map,'MStpX') && isKey(map,'MNegRT')
    dilchain(1)=(map('MNegRT')*2)/(map('MStpX')*2);
  end
  if isKey(map,'MLigase') && isKey(map,'MPosRT')
    dilchain(2)=(map('MLigase')*3)/(map('MPosRT')*2);
  elseif isKey(map,'MLigase') && isKey(map,'MNegRT')
    dilchain(2)=(map('MLigase')*3)/(map('MNegRT')*2);
  end
  if isKey(map,'MQAX') && isKey(map,'MLigase')
    dilchain(3)=(map('MQAX')*6/9)/(map('MLigase')*3);
  elseif isKey(map,'MQBX') && isKey(map,'MLigase')
    dilchain(3)=(map('MQBX')*6/9)/(map('MLigase')*3);
  elseif isKey(map,'MQMX') && isKey(map,'MLigase')
    dilchain(3)=(map('MQMX')*6/9)/(map('MLigase')*3);
  end
  if ~isfield(result,'dilchain')
    result.dilchain=dilchain;
  elseif any(result.dilchain ~= dilchain & isfinite(dilchain) & isfinite(result.dilchain))
    error('Inconsistent dilution chain: %s vs. %s\n', sprintf('%f/',result.dilchain),sprintf('%f/',dilchain));
  else
    result.dilchain(isfinite(dilchain))=dilchain(isfinite(dilchain));
  end
  if ~isfield(result,'dilution')
    result.dilution=1;
    result.dilrelative='None';
  end
  % Calculate concentrations
  p=data.primers.(v.primer);
  if isfinite(v.ct)
    v.conc=(p.eff^-v.ct*p.ct0*result.dilution)/(double(v.length))*1000;
  else
    v.conc=nan;
  end

  if isfield(result,v.primer)
    % Append replicates
    fprintf('Have multiple samples for primer %s\n', v.primer);
    result.(v.primer)(end+1)=v;
  else
    result.(v.primer)=v;
  end
end

if isfield(result,'T') && isfield(result,'M')
  result.theofrac=result.T.conc/result.M.conc;
end
  
