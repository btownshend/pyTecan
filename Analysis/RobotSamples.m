% Analyze a robot run 
classdef RobotSamples < handle
  properties
    options;
    q;		% QPCR data
    samps;
    opd;
    sampmap;
    qsamps;
    templates;
    suffixes;
    wellsProcessed;
    loop1len;	% Dict that maps templates names to the length of loop1
    loop2len;
    rsv; % Saved data 
    sv;	% Saved data (scaled by ref)
  end
  
  methods
    function obj=RobotSamples(sampfilename,opdfilename,varargin)
      defaults=struct('thresh',[],'doplot',true,'basecycles',2:8,'fulow',[],'fuhigh',[],'refconc',10,'remotedir',[],'showall',false,'badcycles',[],'longm',true);
      args=processargs(defaults,varargin);
      if ~iscell(sampfilename)
        sampfilename={sampfilename};
      end
      obj.options=args;
      obj.loop1len=containers.Map;
      obj.loop2len=containers.Map;
      for i=1:length(sampfilename)
        if exist(sampfilename{i},'file')==0
          error('File not found: %s',sampfilename{i});
        end
        eval(sampfilename{i});	% This loads all the data into a var called 'samps'
        for j=1:length(samps)
          if isfield(samps(j),'extrainfo') && ~isempty(samps(j).extrainfo) 
            assert(length(samps(j).extrainfo)==2);
            fprintf('setlooplengths(%s,%d,%d)\n',samps(j).name,samps(j).extrainfo);
            obj.setlooplengths(samps(j).name,samps(j).extrainfo(1),samps(j).extrainfo(2));
          end
        end
        if i==1
          obj.samps=samps;		% Copy to class
        else
          % Update well ID to point to concatenated well
          for j=1:length(samps)
            if ~isempty(samps(j).well)
              samps(j).well=sprintf('%c%d',samps(j).well(1),str2double(samps(j).well(2:end))+12*(i-1));
            end
          end
          obj.samps=[obj.samps,samps];
        end
      end

      obj.qsamps=containers.Map;
      obj.buildsampmap();
      if nargin<2 || isempty(opdfilename)
        obj.opd={opdread('remotedir',args.remotedir)};
      elseif iscell(opdfilename)
        obj.opd={};
        for i=1:length(opdfilename)
          obj.opd{i}=opdread(opdfilename{i},'remotedir',args.remotedir);
        end
      else
        obj.opd={opdread(opdfilename,'remotedir',args.remotedir)};
      end
      if ~isempty(args.badcycles)
        for bc=args.badcycles
          obj.opd{1}.avg.scaled(bc,:,:)=(obj.opd{1}.avg.scaled(bc-1,:,:)+obj.opd{1}.avg.scaled(bc+1,:,:))/2;
        end
      end
      for i=1:length(obj.opd)
        obj.opd{i}=ctcalc(obj.opd{i},'thresh',args.thresh,'basecycles',args.basecycles,'doplot',args.doplot,'fulow',args.fulow,'fuhigh',args.fuhigh,'showall',args.showall);
      end
      obj.templates={};
      obj.suffixes={};
      obj.wellsProcessed=false;
    end

    function buildsampmap(obj)
    % Build a map from sample name to samp entry
      obj.sampmap=containers.Map();
      for i=1:length(obj.samps)
        if isKey(obj.sampmap,obj.samps(i).name)
          error('Duplicate sample name: %s', obj.samps(i).name);
        end
        obj.sampmap(obj.samps(i).name)=obj.samps(i);
      end
    end
    
    function printsamphistory(obj,name,level,frac)
    % Print a hierarchy of sample
      if nargin<3
        level=0;
      end
      if nargin<4
        frac=1;
      end
      fprintf('%s%-10.2f %s\n',blanks(level*2),1/frac,name);
      if isKey(obj.sampmap,name)
        s=obj.sampmap(name);
        for i=1:length(s.ingredients)
          if ~strcmp(s.ingredients{i},name) && ~strcmp(s.ingredients{i},'BIND')
            obj.printsamphistory(s.ingredients{i},level+1,frac*s.volumes(i)/sum(s.volumes));
          end
        end
      end
    end
    
    function setupQPCR(obj,varargin)
    % Scan sample data to setup qPCR 
      defaults=struct('refname','QPCRREF','refconc',50,'refstrands',2,'qpcrdil',4,'minct',7,'processWells',false,'units','pM','cal',[],'primers',{{}});
      args=processargs(defaults,varargin);

      ctgrid=obj.opd{1}.ctgrid;
      for i=2:length(obj.opd)
        ctgrid=[ctgrid,obj.opd{i}.ctgrid];
      end
      obj.q=QPCR(ctgrid,'minct',args.minct);
      if isempty(args.cal)
        obj.addQPCRRef(args.refname,'units',args.units,'refconc',args.refconc,'refstrands',args.refstrands,'qpcrdil',args.qpcrdil);
        haveRefs=obj.q.refs.keys;
        if isempty(haveRefs)
          error('No %s refs for any primer\n', args.refname);
        end
        for p=1:length(args.primers)
          if ~obj.q.refs.isKey(args.primers{p})
            fprintf('No reference for %s -- duplicating %s\n',args.primers{p},haveRefs{1});
            obj.q.dupref(haveRefs{1},args.primers{p});
          end
        end
      elseif ~isempty(args.primers)
        for i=1:length(args.primers)
          obj.q.addmanualref(args.primers{i},2.0,args.cal,'units','ng/ul','ctlod',obj.getWaterCt(args.primers{i}));
        end
      else
        error('setupQCPR: Must specify both cal and primers to use manual calibration\n');
      end

      if args.processWells
        obj.processWells;
      end
    end
    
    function ct=getWaterCt(obj,primer)
      water=getrelative(obj.samps,['P-',primer],{'EvaUSER','Water'},true);
      if isempty(water)
        water=getrelative(obj.samps,['P-',primer],{'EvaUSER','SSDDil'},true);
      end
      if isempty(water)
        ct=nan;
      else
        ct=obj.q.getct(water.well);
      end
      if isnan(ct)
        ct=22;
        fprintf('Missing water control for %s -- assuming %.1f\n', primer,ct);
      end
    end
    
    function addQPCRRef(obj,refname,varargin)
      fprintf('addQPCRRef(%s,...)',refname);
      defaults=struct('refconc',50,'refstrands',2,'qpcrdil',4,'units','pM');
      args=processargs(defaults,varargin);

      ss=getrelative(obj.samps,refname);
      primers={};
      for i=1:length(ss)
        s=ss(i);
        for j=1:length(s.ingredients)
          if strncmp(s.ingredients{j},'MQ',2) || strncmp(s.ingredients{j},'P-',2)
            primers{end+1}=s.ingredients{j}(3:end);
          end
        end
      end
      primers=unique(primers);
      for i=1:length(primers)
        p=primers{i};
        ss=getrelative(obj.samps,refname,{['P-',p]},false);
        water=getrelative(obj.samps,['P-',p],{'EvaGreen','Water'},true);
        if isempty(water)
          water=getrelative(obj.samps,['P-',p],{'EvaGreen','SSDDil'},true);
        end
        % Also include undiluted one if present
        ss=[ss,getrelative(obj.samps,refname,{['P-',p]},true)];
        if isempty(ss)
          fprintf('No wells found for reference %s with primer %s\n', refname, p);
          continue;
        end

        wells={ss.well};
        concs=args.refconc*args.qpcrdil./[ss.dil];
        if isempty(water)
          fprintf('Missing water control for %s\n', p);
        else
          wells{end+1}=water.well;
          concs(end+1)=0;
        end
        fprintf('Added reference %s: ',p);
        for j=1:length(wells)
          if j<=length(ss)
            fprintf(' %s[%s]@%.3f %s ',ss(j).name,wells{j},concs(j),args.units);
          else
            fprintf(' [%s]@%.3f %s ',wells{j},concs(j),args.units);
          end
        end
        fprintf('\n');
        obj.q.addref(p,wells,concs,'units',args.units,'strands',args.refstrands,'ctlod',24);
      end
    end

    function processWells(obj)
      % Run through the wells using the 'samps' data figure out their Ct and concentration prior to qPCR dilution
      % Currently only handles single replicates and doesn't track confidence intervals
      if obj.wellsProcessed
        error('Wells already processed and processWells() called again');
      end
      for i=1:length(obj.samps)
        s=obj.samps(i);
        if ~strcmp(s.plate,'qPCR')
          continue;
        end
        if strcmp(s.well,'None')
          continue;
        end
        well=obj.q.parsewells(s.well);
        if isempty(obj.q.primers{well})
          %fprintf('Need to parse %s at well %s (%d)\n', s.name, s.well, well);
          dots=find(s.name=='.');
          if s.name(dots(end)+1)~='Q'
            % Replicate (i.e. ".2" suffix after what we're looking for
            primers=s.name(dots(end-1)+2:dots(end)-1);
            replicate=str2double(s.name(dots(end)+1:end));
            assert(isfinite(replicate));
            dots=dots(1:end-1);
          else
            primer=s.name(dots(end)+2:end);
            replicate=1;
          end
          if length(dots)>1 && s.name(dots(end-1)+1)=='D'
            dilution=str2double(strrep(strrep(s.name(dots(end-1)+2:dots(end)-1),'_','.'),'#',''));
            root=s.name(1:dots(end-1)-1);
          else
            dilution=1;
            root=s.name(1:dots(end)-1);
          end
          npound=sum(s.name=='#');
          if npound>0
            replicate=replicate+npound;
          end
          if replicate~=1
            root=sprintf('%s.R%d',root,replicate);
          end
          obj.setwell(root,s.well,primer,dilution,s);

          % Determine templates and suffixes
          % Templates are all the unique names up to the first dot
          % Suffixes are all the unique suffixes after templates not including any dilution or QPCR suffixes
          dots=find(root=='.');
          if length(dots)>=1
            template=root(1:dots(1)-1);
            stage=root(dots(1):end);
          else
            template=root;
            stage='';
          end
          %fprintf('%s -> %s & %s\n', root, template, stage);
          obj.templates=union(obj.templates,template,'stable');
          obj.suffixes=union(obj.suffixes,stage,'stable');
        end        
      end
      obj.wellsProcessed=true;
    end
  
    function setstagedilution(obj,stage,dilution)
    % Set dilution from reference stage (e.g. T7 reaction) to 'stage'
    % e.g. setstagedilution('.T-.RT',1.1*2);
      fprintf('setstagedilution() is not longer needed\n');
    end
    
    function setlooplengths(obj,template,loop1,loop2)
    % Set loop sizes for use in computing length of qPCR products
      dot=find(template=='.',1);
      if ~isempty(dot)
        template=template(1:dot-1);
      end
      obj.loop1len(template)=loop1;
      obj.loop2len(template)=loop2;
    end
    
    function setwell(obj,root,well,primer,dilution,samp)
    % Set a particular qPCR well to have the name 'root', primer and dilution as given
    % Samp is entry for the sample (used to calculate dilution from T7 reaction)
    %fprintf(' root=%s, primer=%s, dilution=%f\n', root, primer, dilution);
      if ~isKey(obj.qsamps,root)
        entry=struct('name',root,'dilution',[],'ct',{-1*ones(size(obj.q.refs.keys))},'conc',{nan(size(obj.q.refs.keys))},'wells',{cell(size(obj.q.refs.keys))},'order',[]);
        for j=1:length(obj.q.refs.keys)
          entry.wells{j}={};
          entry.dilution(j)=nan;
        end
      else
        entry=obj.qsamps(root);
      end
      pindex=find(strcmp(primer,obj.q.refs.keys));
      if length(pindex)~=1
        fprintf('Unable to find primer %s for assigning sample %s\n', primer, root);
      else
        if ~isnan(entry.ct(pindex))  && entry.ct(pindex)>0
          fprintf('Duplicate well for %s with primer %s (%s) with dilution %.1f ignored\n', root, primer, well, dilution);
          return;
        end
        entry.wells{pindex}=well;
        entry.ct(pindex)=obj.q.getct(well);
        entry.dilution(pindex)=dilution;
        entry.conc(pindex)=obj.q.getconc(primer,well,{},{},{},'dilution',dilution,'strands',2);
        wellindex=obj.q.parsewells(well);
        entry.order=min([entry.order,wellindex]);
      end
      pTaq=find(strcmp(samp.ingredients,'Taq'));
      pMT7=find(strcmp(samp.ingredients,'MT7'));
      pT7=find(strcmp(samp.ingredients,'T7'));
      if ~isempty(pTaq)  && sum(samp.volumes(pTaq))>sum(samp.volumes(pT7))
        entry.dispDil=1;   % No dilution back-out for PCR products
      else
        % Use base sample to calculate dilution from T7 step
        pMT7=find(strcmp(samp.ingredients,'MT7'));
        if length(pMT7)~=1 && length(pT7)~=1
          if length(samp.ingredients)>3   % Water controls have just EvaUSER, P-*, SSDDil
            fprintf('Unable to locate MT7 or T7 ingredient in %s -- assuming 1x dilution\n', samp.name);
          end
          entry.dispDil=1;
        else 
          if length(pMT7)==1
            dispDil=sum(samp.volumes)/samp.volumes(pMT7);
            dispDil=dispDil/dilution/2.5/4;	% Back out dilution of MT7(2.5), qPCR dilution(dilution), qPCR final dil (4)
          else
            dispDil=sum(samp.volumes)/samp.volumes(pT7);
            dispDil=dispDil/dilution/20/4;	% Back out dilution of T7(20) (note: 10x of actual T7, but half is marked as glycerol), qPCR dilution(dilution), qPCR final dil (4)
          end
          if dispDil>10000
            fprintf('Bad display dilution computation for %s: %.0f\n', root, dispDil);
            dispDil=1;
          end
          entry.dispDil=dispDil;
        end
      end
      obj.qsamps(root)=entry;
    end      

    function len=getlength(obj,template,primer)
    % See if we have the length
      len=nan;
      if obj.loop1len.isKey(template) && obj.loop2len.isKey(template)
        loop1len=obj.loop1len(template);
        loop2len=obj.loop2len(template);
        if strncmp(primer,'MX',2)
          len=17+loop2len+29;
          if obj.options.longm
            len=len+73;
          end
        elseif strncmp(primer,'WX',2)
          len=11+6+loop1len+6+17+loop2len+29;
        elseif strncmp(primer,'AX',2)
          len=21+6+loop1len+6+17+loop2len+29;
        elseif strncmp(primer,'BX',2)
          len=21+6+loop1len+6+17+loop2len+29;
        elseif strncmp(primer,'T7X',3)
          %          len=24+mean([11,21])+6+loop1len+6+17+loop2len+29;  % Could be W,B, or A
          len=24+11+6+loop1len+6+17+loop2len+29;  % Set it to be W
        elseif strncmp(primer,'T7WX',4)
          len=24+11+6+loop1len+6+17+loop2len+29;
        elseif strncmp(primer,'T7AX',4)
          len=24+21+6+loop1len+6+17+loop2len+29;
        elseif strncmp(primer,'T7BX',4)
          len=24+21+6+loop1len+6+17+loop2len+29;
        elseif strcmp(primer,'REF')
          len=90;
        elseif strcmp(primer,'TBR')
          len=74;  
        elseif strcmp(primer,'TWR')
          len=64;            
        elseif strcmp(primer,'TR')
          len=mean([64,74]);   % Could be W or B
        elseif strcmp(primer,'TheoX')
          len=71;
        else
          fprintf('Not implemented: length of sequence with %s primers\n', primer);
        end
      end
    end
    
    function copyprimer(obj,existing,new)
    % Copy data for existing primer 'existing' to 'new'
      fprintf('Using reference for primer %s as a surrogate for %s\n', existing, new);
      tmp=obj.q.refs(existing);
      tmp.samples=containers.Map;
      obj.q.refs(new)=tmp;
      % Expand any existing entries
      keys=obj.qsamps.keys;
      for i=1:length(keys)
        qs=obj.qsamps(keys{i});
        qs.ct(end+1)=nan;
        qs.conc(end+1)=nan;
        qs.wells{end+1}='';
        obj.qsamps(keys{i})=qs;
      end
    end
    
    function [w,indices]=wellfind(obj,plate,regex)
    % Return a cell array of well names for samples matching the regex
      w={};
      indices=[];
      for i=1:length(obj.samps)
        if ~strcmp(obj.samps(i).plate,plate)
          continue;
        end
        m=regexp(obj.samps(i).name,regex);
        if ~isempty(m)
          w{end+1}=obj.samps(i).well;
          indices(end+1)=i;
        end
      end
    end
    
    function havedata=plotmelt(obj, regex)
    % Plot melt curve on the current figure for samples matching regex
    % Plot all curves if regex == 'all'
      if strcmp(regex,'all')
        % Melt plots
        for i=1:length(obj.primers())
          setfig(['melt-',obj.primers(i)]);clf;
          for j=1:length(obj.templates)
            subplot(ceil(length(obj.templates)/2),2,j);
            havedata=obj.plotmelt([regexptranslate('escape',obj.templates{j}),'\..*Q',obj.primers(i)]);
            if ~havedata
              continue;
            end
            title([obj.templates{j},' - ',obj.primers(i)],'Interpreter','None');
          end
        end
        return;
      end

      [w,i]=obj.wellfind('qPCR',regex);
      havedata=false;
      if isempty(w)
        fprintf('plotmelt: No samples match "%s"\n', regex);
        return;
      end
      for j=1:length(obj.opd)
        ut=opdmelt(obj.opd{j},w);
        if length(ut)>1
          havedata=true;
        end
      end
      if havedata
        h=legend({obj.samps(i).name},'Interpreter','None','Location','SouthWest');
        set(h,'FontSize',5);
      end
    end
    
    function plotopd(obj, regex)
    % Plot opd curve on the current figure for samples matching regex
      [w,i]=obj.wellfind('qPCR',regex);
      if isempty(w)
        fprintf('plotopd: No samples match "%s"\n', regex);
        return;
      end
      for i=1:length(obj.opd)
        opdcheck(obj.opd{i},w,'firststage',true,'basecycles',obj.options.basecycles,'thresh',obj.options.thresh);
      end
      legend({obj.samps(i).name},'Interpreter','None','Location','NorthWest');
    end
    
    function p=primers(obj, index)
      p=obj.q.refs.keys;
      if nargin>=2
        p=p{index};
      end
    end
    
    function printconcs(obj,varargin)
      defaults=struct('refprimer','REF','normalize',false);
      args=processargs(defaults,varargin);

      pT7WX=find(strcmp(obj.primers,'T7WX'));
      pWX=find(strcmp(obj.primers,'WX'));
      pAX=find(strcmp(obj.primers,'T7AX'));
      if isempty(pAX)
        pAX=find(strcmp(obj.primers,'AX'));
      end
      pBX=find(strcmp(obj.primers,'T7BX'));
      if isempty(pBX)
        pBX=find(strcmp(obj.primers,'BX'));
      end
      pMX=find(strcmp(obj.primers,'MX'));
      pT7X=find(strcmp(obj.primers,'T7X'));
      pREF=find(strcmp(obj.primers,'REF'));

      keys=obj.qsamps.keys;
      fprintf('Primers:                                         ');
      qkeys=obj.q.refs.keys;
      for i=1:length(qkeys)
        fprintf('%4s ', qkeys{i});
      end
      fprintf('\n');
      for i=1:length(keys)
        ord(i)=obj.qsamps(keys{i}).order;
      end
      [~,sortorder]=sort(ord);
      for i=sortorder
        qs=obj.qsamps(keys{i});
        if nanstd(qs.dilution)<1e-8
          dil=sprintf('%6.0f',nanmean(qs.dilution));
        else
          dil=sprintf('[%s]',sprintf('%.0f ',qs.dilution));
        end
        fprintf('%-30.30s:  Dil=%s, Ct=[%s], Conc=[%s] %s\n', qs.name, dil, sprintf('%4.1f ',qs.ct),sprintf('%7.2f ',qs.conc),obj.q.refs(qkeys{1}).units);
        fprintf('%-30.30s:                 [',' ');
        for i=1:length(qs.wells)
          if isempty(qs.wells{i})
            fprintf('%4s ','');
          else
            fprintf('%4s ',qs.wells{i});
          end
        end
        fprintf(']\n');
      end

      % Check for any missed ones
      for i=1:prod(size(obj.q.ctgrid))
        if isfinite(obj.q.ctgrid(i)) && isempty(obj.q.primers{i})
          fprintf(' Undetermined primer for well %s with Ct=%.1f\n', obj.q.wellnames{i}, obj.q.ctgrid(i));
        end
      end

      obj.sv=[];
      obj.rsv=[];
      printRefScale=false;   % True to add columns scaling by ref
      nrowsprinted=99;   % Default so we print headers first time
      prevlenlist=[];
      for i=1:length(obj.templates)
        lenlist=[];
        for j=1:length(obj.primers())
          lenlist(j)=obj.getlength(obj.templates{i},obj.primers(j));
        end
        if isempty(prevlenlist) || any(prevlenlist~=lenlist)
          fprintf('\n%-40.40s ','');
          fprintf('  Dil ');
          ref=[];
          for j=1:length(obj.primers())
            fprintf('%8s ',obj.primers(j));
            if strcmp(obj.primers(j),args.refprimer)
              ref=j;
            end
          end
          if ~isempty(ref) && printRefScale
            fprintf('%s',blanks(7));
            for j=1:length(obj.primers())
              if j~=ref
                fprintf('%6s ',obj.primers(j));
              end
            end
          end
          fprintf('\n');
          fprintf('%-46.46s ','');
          fprintf('%8d ',lenlist);
        end
        prevlenlist=lenlist;
        
        if ~isempty(ref) && nrowsprinted>=2 && printRefScale
          fprintf('%s',blanks(7));
          for j=1:length(obj.primers())
            if j~=ref
              fprintf('%6s ',['/',obj.primers(ref)]);
            end
          end
          fprintf('* %.1f nM',obj.options.refconc);
        end
        fprintf('\n');

        nrowsprinted=0;
        for j=1:length(obj.suffixes)
          nm=[obj.templates{i},obj.suffixes{j}];
          if isKey(obj.qsamps,nm)
            scale=obj.qsamps(nm).dispDil;
            concs=obj.qsamps(nm).conc*scale;
            concsnm=nan*concs;	% Conc in nM
            for k=1:length(obj.primers())
              mw=607.4*obj.getlength(obj.templates{i},obj.primers{k})+157.9;
              concsnm(k)=concs(k)/1000/mw*1e9;
            end
            if all(isfinite(concsnm)==isfinite(concs))
              if args.normalize && isfinite(concsnm(pREF))
                concsnm=concsnm/concsnm(pREF)*obj.options.refconc;
              end
              fprintf('%-40.40s %6.2f %s nM    ',nm,scale,sprintf('%8.3f ',concsnm));
              obj.rsv(i,j,:)=concsnm;
            else
              fprintf('%-40.40s %6.2f %s ng/ul ',nm,scale,sprintf('%8.3f ',concs));
              obj.rsv(i,j,:)=concs;
            end
            if ~isempty(ref) && printRefScale
              obj.sv(i,j,:)=obj.rsv(i,j,:)/obj.rsv(i,j,ref)*obj.options.refconc;
              fprintf('%6.1f ',obj.sv(i,j,[1:ref-1,ref+1:end]));
            end
            if (length(nm)>4 && strcmp(nm(end-3:end),'.ext')) || (length(nm)>3 && strcmp(nm(end-2:end),'.rt'))
              if nm(1)=='A'
                pCLV=pBX; pUNCLV=pAX;
              elseif nm(1)=='B'
                pCLV=pT7WX; pUNCLV=pBX;
              elseif nm(1)=='W'
                pCLV=pAX; pUNCLV=pT7WX;
              elseif isempty(pBX) && ~isempty(pAX)
                pCLV=pAX; pUNCLV=pT7WX;
              end
              cleavage=100*concsnm(pCLV)/sum(concsnm([pCLV,pUNCLV]));
              if isfinite(cleavage)
                fprintf('T=%4.2f Clv=%4.1f%% ABW/M=%.2f',concsnm(pT7X)/concsnm(pREF)*obj.options.refconc, cleavage,nansum(concsnm([pAX,pBX,pT7WX]))/concsnm(pMX));
              else
                fprintf('T=%4.2f',concsnm(pT7X)/concsnm(pREF)*obj.options.refconc);
              end
            end
            fprintf('\n');
            nrowsprinted=nrowsprinted+1;
          end
        end
        if nrowsprinted>=2
          fprintf('\n');
        end
      end

    end

    function analyze(obj,domelt,doqpcr)
      if nargin<2
        domelt=false;
      end
      if nargin<3
        doqpcr=false;
      end
      if ~obj.wellsProcessed
        obj.processWells();
      end
      obj.printconcs();
      if doqpcr
        setfig('qpcr');clf;
        obj.q.plot();
      end
      if domelt
        obj.plotmelt('all');
      end
    end

    function trpstats(obj,nT7,nEXT)
    % Display stats relevant to a typical TRP run
      if nargin<3 || isempty(nEXT)
        nEXT='.ext';
      end
      if nargin<2 || isempty(nT7)
        nT7='T-';
      end
      sv=obj.rsv;      %obj.rsv is indexed by (template,stage*replicate,primer)
      pT7WX=find(strcmp(obj.primers,'T7WX'));
      pWX=find(strcmp(obj.primers,'WX'));
      pAX=find(strcmp(obj.primers,'T7AX'));
      if isempty(pAX)
        pAX=find(strcmp(obj.primers,'AX'));
      end
      pBX=find(strcmp(obj.primers,'T7BX'));
      if isempty(pBX)
        pBX=find(strcmp(obj.primers,'BX'));
      end
      pMX=find(strcmp(obj.primers,'MX'));
      pT7X=find(strcmp(obj.primers,'T7X'));
      pREF=find(strcmp(obj.primers,'REF'));
      ref=sv(:,:,pREF);ref=ref(isfinite(ref));ref=ref(ref>0);
      fprintf('Mean REF = [%s] = %.0f\n', sprintf('%.0f ',ref),mean(ref));
      for i=1:length(obj.templates)
        s=strrep(obj.suffixes,'#','');   % Remove replicate marker
        sT7=false(size(s));
        sEXT=false(size(s));
        for j=1:length(s)
          if length(s{j})>=length(nT7)
            sT7(j)=strcmp(s{j}(end-length(nT7)+1:end),nT7);
          end
          if length(s{j})>=length(nEXT)
            sEXT(j)=strcmp(s{j}(end-length(nEXT)+1:end),nEXT);
          end
        end
        sT7=find(sT7,1);
        sEXT=find(sEXT,1);
        if true % any(sv(i,sT7,pT7X)>0)
          svi=squeeze(sv(i,:,:));
          valid=false(size(svi,2),1);
          if ~isempty(sT7)
            valid=valid|(svi(sT7,:)'>0);
          end
          if ~isempty(sEXT)
            valid=valid|(svi(sEXT,:)'>0);
          end
          %sT7=sT7(valid); sEXT=sEXT(valid);
          fprintf('\n%s (%d replicates)\n', obj.templates{i},sum(valid));
          if any(svi(sT7,:)'>0)
            fprintf('[Template] = [%s]./[%s] * %.0f = [%s] = %6.1f nM\n', sprintf('%6.1f ',svi(sT7,pT7X)),sprintf('%6.1f ',svi(sT7,pREF)),obj.options.refconc,sprintf('%6.1f ',svi(sT7,pT7X)./svi(sT7,pREF)*obj.options.refconc),nanmean(svi(sT7,pT7X)./svi(sT7,pREF)*obj.options.refconc));
          end
          tW=svi(sT7,[pWX,pT7WX]); tA=svi(sT7,pAX); tB=svi(sT7,pBX);
          mtW=nanmean(tW); mtA=nanmean(tA); mtB=nanmean(tB);
          if mtW>mtA && mtW>mtB;
            desired=tW; undesired=nansum([tA,tB],2);
          elseif mtA>mtW && mtA>mtB
            desired=tA; undesired=nansum([tW,tB],2);
          else
            desired=tB; undesired=nansum([tW,tA],2);
          end
          if any(svi(sT7,:)'>0)
            fprintf('Tmp contam = [%s]./[%s]      = [%s] = %6.1f%%\n', sprintf('%6.1f ',undesired),sprintf('%6.1f ',desired),sprintf('%6.1f ',undesired./desired*100),nanmean(undesired./desired)*100);
          end
          if any(any(svi(sEXT,:)>0))
            fprintf('[MX]       = [%s]./[%s] * %.0f = [%s] = %6.1f nM\n',sprintf('%6.1f ',svi(sEXT,pMX)),sprintf('%6.1f ',svi(sEXT,pREF)),obj.options.refconc,sprintf('%6.1f ',svi(sEXT,pMX)./svi(sEXT,pREF)*obj.options.refconc),nanmean(svi(sEXT,pMX)./svi(sEXT,pREF)*obj.options.refconc));
            fprintf('M/T7       = [%s]./[%s]      = [%s] = %6.1f x\n',sprintf('%6.1f ',svi(sEXT,pMX)),sprintf('%6.1f ',svi(sEXT,pT7X)),sprintf('%6.1f ',svi(sEXT,pMX)./svi(sEXT,pT7X)),nanmean(svi(sEXT,pMX)./svi(sEXT,pT7X)));
            if ~isempty(pT7WX)
              fprintf('T7W/T7     = [%s]./[%s]      = [%s] = %6.1f x\n',sprintf('%6.1f ',svi(sEXT,pT7WX)),sprintf('%6.1f ',svi(sEXT,pT7X)),sprintf('%6.1f ',svi(sEXT,pT7WX)./svi(sEXT,pT7X)),nanmean(svi(sEXT,pT7WX)./svi(sEXT,pT7X)));
              fprintf('T7W/M      = [%s]./[%s]      = [%s] = %6.1f%%\n',sprintf('%6.1f ',svi(sEXT,pT7WX)),sprintf('%6.1f ',svi(sEXT,pMX)),sprintf('%6.1f ',100*svi(sEXT,pT7WX)./svi(sEXT,pMX)),nanmean(100*svi(sEXT,pT7WX)./svi(sEXT,pMX)));
            end
            if ~isempty(pWX)
              fprintf('W/T7       = [%s]./[%s]      = [%s] = %6.1f x\n',sprintf('%6.1f ',svi(sEXT,pWX)),sprintf('%6.1f ',svi(sEXT,pT7X)),sprintf('%6.1f ',svi(sEXT,pWX)./svi(sEXT,pT7X)),nanmean(svi(sEXT,pWX)./svi(sEXT,pT7X)));
              fprintf('W/M        = [%s]./[%s]      = [%s] = %6.1f%%\n',sprintf('%6.1f ',svi(sEXT,pWX)),sprintf('%6.1f ',svi(sEXT,pMX)),sprintf('%6.1f ',100*svi(sEXT,pWX)./svi(sEXT,pMX)),nanmean(100*svi(sEXT,pWX)./svi(sEXT,pMX)));
            end
            if ~isempty(pT7WX) && ~isempty(pWX)
              fprintf('T7W/W      = [%s]./[%s]      = [%s] = %6.1f x\n',sprintf('%6.1f ',svi(sEXT,pT7WX)),sprintf('%6.1f ',svi(sEXT,pWX)),sprintf('%6.1f ',svi(sEXT,pT7WX)./svi(sEXT,pWX)),nanmean(svi(sEXT,pT7WX)./svi(sEXT,pWX)));
            end
            if ~isempty(pAX)
              fprintf('A/T7       = [%s]./[%s]      = [%s] = %6.1f x\n',sprintf('%6.1f ',svi(sEXT,pAX)),sprintf('%6.1f ',svi(sEXT,pT7X)),sprintf('%6.1f ',svi(sEXT,pAX)./svi(sEXT,pT7X)),nanmean(svi(sEXT,pAX)./svi(sEXT,pT7X)));
              fprintf('A/M        = [%s]./[%s]      = [%s] = %6.1f%%\n',sprintf('%6.1f ',svi(sEXT,pAX)),sprintf('%6.1f ',svi(sEXT,pMX)),sprintf('%6.1f ',100*svi(sEXT,pAX)./svi(sEXT,pMX)),nanmean(100*svi(sEXT,pAX)./svi(sEXT,pMX)));
            end
            if ~isempty(pBX)
              fprintf('B/T7       = [%s]./[%s]      = [%s] = %6.1f x\n',sprintf('%6.1f ',svi(sEXT,pBX)),sprintf('%6.1f ',svi(sEXT,pT7X)),sprintf('%6.1f ',svi(sEXT,pBX)./svi(sEXT,pT7X)),nanmean(svi(sEXT,pBX)./svi(sEXT,pT7X)));
              fprintf('B/M        = [%s]./[%s]      = [%s] = %6.1f%%\n',sprintf('%6.1f ',svi(sEXT,pBX)),sprintf('%6.1f ',svi(sEXT,pMX)),sprintf('%6.1f ',100*svi(sEXT,pBX)./svi(sEXT,pMX)),nanmean(100*svi(sEXT,pBX)./svi(sEXT,pMX)));
            end

            add=sum(svi(sEXT,[pAX,pWX,pT7WX,pBX]),2);
            fprintf('(total)/M  = [%s]./[%s]      = [%s] = %6.1f%%\n',sprintf('%6.1f ',add),sprintf('%6.1f ',svi(sEXT,pMX)),sprintf('%6.1f ',100*add./svi(sEXT,pMX)),nanmean(100*add./svi(sEXT,pMX)));
          end
        end
      end
    end

  end
end
