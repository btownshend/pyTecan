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
    stages;
    stagedilution;
    wellsProcessed;
  end
  
  methods
    function obj=RobotSamples(sampfilename,opdfilename,varargin)
      defaults=struct('thresh',[],'doplot',true,'basecycles',2:8,'fulow',[],'fuhigh',[]);
      args=processargs(defaults,varargin);
      if ~iscell(sampfilename)
        sampfilename={sampfilename};
      end
      obj.options=args;
      for i=1:length(sampfilename)
        assert(exist(sampfilename{i},'file')~=0);
        eval(sampfilename{i});	% This loads all the data into a var called 'samps'
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
      obj.stagedilution=containers.Map;
      obj.buildsampmap();
      if nargin<2 || isempty(opdfilename)
        obj.opd={opdread()};
      elseif iscell(opdfilename)
        obj.opd={};
        for i=1:length(opdfilename)
          obj.opd{i}=opdread(opdfilename{i});
        end
      else
        obj.opd={opdread(opdfilename)};
      end
      for i=1:length(obj.opd)
        obj.opd{i}=ctcalc(obj.opd{i},'thresh',args.thresh,'basecycles',args.basecycles,'doplot',args.doplot,'fulow',args.fulow,'fuhigh',args.fuhigh);
      end
      obj.templates={};
      obj.stages={};
      obj.wellsProcessed=false;
    end

    function buildsampmap(obj)
    % Build a map from sample name to samp entry
      obj.sampmap=containers.Map();
      for i=1:length(obj.samps)
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
      fprintf('%s%8.0f %s\n',blanks(level*2),1/frac,name);
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
      defaults=struct('refname','QPCRREF','refconc',50,'refstrands',2,'qpcrdil',2.5,'minct',7,'processWells',false);
      args=processargs(defaults,varargin);

      ctgrid=obj.opd{1}.ctgrid;
      for i=2:length(obj.opd)
        ctgrid=[ctgrid,obj.opd{i}.ctgrid];
      end
      obj.q=QPCR(ctgrid,'minct',args.minct);
      obj.addQPCRRef(args.refname);
      if args.processWells
        obj.processWells;
      end
    end
    
    function addQPCRRef(obj,refname,varargin)
      defaults=struct('refconc',50,'refstrands',2,'qpcrdil',2.5);
      args=processargs(defaults,varargin);

      ss=getrelative(obj.samps,refname);
      primers={};
      for i=1:length(ss)
        s=ss(i);
        for j=1:length(s.ingredients)
          if strncmp(s.ingredients{j},'MQ',2)
            primers{end+1}=s.ingredients{j}(3:end);
          end
        end
      end
      primers=unique(primers);
      for i=1:length(primers)
        p=primers{i};
        ss=getrelative(obj.samps,refname,{['MQ',p],'Water'},true);
        water=getrelative(obj.samps,['MQ',p],{'Water'},true);
        if isempty(ss)
          ss=getrelative(obj.samps,refname,{['MQ',p],'SSDDil'},true);
          water=getrelative(obj.samps,['MQ',p],{'SSDDil'},true);
        end
        % Also include undiluted one if present
        ss=[ss,getrelative(obj.samps,refname,{['MQ',p]},true)];
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
            fprintf(' %s[%s]@%.3fpM ',ss(j).name,wells{j},concs(j));
          else
            fprintf(' [%s]@%.3fpM ',wells{j},concs(j));
          end
        end
        fprintf('\n');
        obj.q.addref(p,wells,concs,'units','pM','strands',args.refstrands);
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
          primer=s.name(dots(end)+2:end);
          if length(dots)>1 && s.name(dots(end-1)+1)=='D'
            dilution=str2double(strrep(s.name(dots(end-1)+2:dots(end)-1),'_','.'));
            root=s.name(1:dots(end-1)-1);
          else
            dilution=1;
            root=s.name(1:dots(end)-1);
          end
          obj.setwell(root,s.well,primer,dilution);

          % Determine templates and stages
          % Templates are all the unique names up to the first dot
          % Stages are all the unique suffixes after templates not including any dilution or QPCR suffixes
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
          obj.stages=union(obj.stages,stage,'stable');
        end        
      end
      obj.wellsProcessed=true;
    end
  
    function setstagedilution(obj,stage,dilution)
    % Set dilution from reference stage (e.g. T7 reaction) to 'stage'
    % e.g. setstagedilution('.T-.RT',1.1*2);
      obj.stagedilution(stage)=dilution;
    end
    
    function setwell(obj,root,well,primer,dilution)
    % Set a particular well to have the name 'root', primer and dilution as given
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
        entry.conc(pindex)=obj.q.getconc(primer,well,{},{},{},'dilution',dilution)/1000;
        wellindex=obj.q.parsewells(well);
        entry.order=min([entry.order,wellindex]);
      end
      obj.qsamps(root)=entry;
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
      
      obj.processWells;	% Re-process the wells
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
              close;
              return;
            end
            title([obj.templates{j},' - ',obj.primers(i)]);
          end
        end
        return;
      end

      [w,i]=obj.wellfind('qPCR',regex);
      if isempty(w)
        fprintf('plotmelt: No samples match "%s"\n', regex);
        return;
      end
      havedata=false;
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
    
    function printconcs(obj)
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
        fprintf('%-30.30s:  Dil=%s, Ct=[%s], Conc=[%s] nM\n', qs.name, dil, sprintf('%4.1f ',qs.ct),sprintf('%7.2f ',qs.conc));
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

      % Now summarize by template, stage taking into account stage dilutions
      fprintf('Scaled back to reference reaction:\n');
      for j=1:length(obj.stages)
        note='';
        if ~isKey(obj.stagedilution,obj.stages{j})
          note='Not specified, assuming 1.0';
          obj.stagedilution(obj.stages{j})=1.0;
        end
        fprintf(' %20.20s: %5.2f %s\n', obj.stages{j}, obj.stagedilution(obj.stages{j}),note);
      end

      fprintf('%-40.40s ','');
      for i=1:length(obj.primers())
        fprintf('%8s ',obj.primers(i));
      end
      fprintf('\n');

      sv=[];
      for i=1:length(obj.templates)
        for j=1:length(obj.stages)
          nm=[obj.templates{i},obj.stages{j}];
          if isKey(obj.qsamps,nm)
            scale=obj.stagedilution(obj.stages{j});
            concs=obj.qsamps(nm).conc*scale;
            fprintf('%-40.40s %s\n',nm,sprintf('%8.3f ',concs));
            sv(i,j,:)=concs;
          end
        end
        fprintf('\n');
      end

    end

    function analyze(obj)
      if ~obj.wellsProcessed
        obj.processWells();
      end
      obj.printconcs();
      setfig('qpcr');clf;
      obj.q.plot();
      obj.plotmelt('all');
      pdfsavefig('all');
    end
  end
  
end
