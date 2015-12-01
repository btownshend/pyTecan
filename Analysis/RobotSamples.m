% Analyze a robot run 
classdef RobotSamples < handle
  properties
    q;		% QPCR data
    samps;
    opd;
    primers;
    sampmap;
    qsamps;
  end
  
  methods
    function obj=RobotSamples(sampfilename,opdfilename,varargin)
      defaults=struct('thresh',[],'doplot',true,'basecycles',2:8);
      args=processargs(defaults,varargin);
      assert(exist(sampfilename,'file')~=0);
      eval(sampfilename);	% This loads all the data into a var called 'samps'
      obj.samps=samps;		% Copy to class
      obj.qsamps=containers.Map;
      obj.buildsampmap();
      if nargin<2 || isempty(opdfilename)
        obj.opd=opdread();
      else
        obj.opd=opdread(opdfilename);
      end
      obj.opd=ctcalc(obj.opd,'thresh',args.thresh,'basecycles',args.basecycles,'doplot',args.doplot);
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
      defaults=struct('refname','QPCRREF','refconc',50,'refstrands',2,'qpcrdil',2.5,'minct',7,'processWells',true);
      args=processargs(defaults,varargin);

      obj.q=QPCR(obj.opd.ctgrid,'minct',args.minct);
      obj.primers={};
      obj.addQPCRRef(args.refname);
      if args.processWells
        obj.processWells;
      end
    end
    
    function addQPCRRef(obj,refname,varargin)
      defaults=struct('refconc',50,'refstrands',2,'qpcrdil',2.5);
      args=processargs(defaults,varargin);

      ss=getrelative(obj.samps,refname);
      for i=1:length(ss)
        s=ss(i);
        for j=1:length(s.ingredients)
          if strncmp(s.ingredients{j},'MQ',2)
            obj.primers{end+1}=s.ingredients{j}(3:end);
          end
        end
      end
      obj.primers=unique(obj.primers);
      for i=1:length(obj.primers)
        p=obj.primers{i};
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
          fprintf(' %s[%s]@%.3fpM ',ss(j).name,wells{j},concs(j));
        end
        fprintf('\n');
        obj.q.addref(p,wells,concs,'units','pM','strands',args.refstrands);
      end
    end

    function processWells(obj)
      % Run through the wells using the 'samps' data figure out their Ct and concentration prior to qPCR dilution
      % Currently only handles single replicates and doesn't track confidence intervals
      for i=1:length(obj.samps)
        s=obj.samps(i);
        if strcmp(s.well,'None')
          continue;
        end
        well=obj.q.parsewells(s.well);
        if strcmp(s.plate,'qPCR') % && isempty(obj.q.primers{well})
          %fprintf('Need to parse %s at well %s (%d)\n', s.name, s.well, well);
          dots=find(s.name=='.');
          primer=s.name(dots(end)+2:end);
          if length(dots)>1
            dilution=str2double(strrep(s.name(dots(end-1)+2:dots(end)-1),'_','.'));
            root=s.name(1:dots(end-1)-1);
          else
            dilution=1;
            root=s.name(1:dots(end)-1);
          end
          obj.setwell(root,s.well,primer,dilution);
        end
      end
    end
  
    function setwell(obj,root,well,primer,dilution)
    % Set a particular well to have the name 'root', primer and dilution as given
    %fprintf(' root=%s, primer=%s, dilution=%f\n', root, primer, dilution);
      if ~isKey(obj.qsamps,root)
        entry=struct('name',root,'dilution',[],'ct',{nan(size(obj.primers))},'conc',{nan(size(obj.primers))},'wells',{cell(size(obj.primers))},'order',[]);
        for j=1:length(obj.primers)
          entry.wells{j}={};
          entry.dilution(j)=nan;
        end
      else
        entry=obj.qsamps(root);
      end
      pindex=find(strcmp(primer,obj.primers));
      if length(pindex)~=1
        fprintf('Unable to find primer %s for assigning sample %s\n', primer, root);
      else
        if ~isnan(entry.ct(pindex)) 
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
      obj.primers{end+1}=new;
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
    
    function printconcs(obj)
      keys=obj.qsamps.keys;
      fprintf('Primers:                                         ');
      for i=1:length(obj.primers)
        fprintf('%4s ', obj.primers{i});
      end
      fprintf('\n');
      for i=1:length(keys)
        ord(i)=obj.qsamps(keys{i}).order;
      end
      [~,sortorder]=sort(ord);
      for i=sortorder
        qs=obj.qsamps(keys{i});
        if nanstd(qs.dilution)==0
          dil=nanmean(qs.dilution);
        else
          dil=nan;
        end
        fprintf('%-30.30s:  Dil=%6.0f, Ct=[%s], Conc=[%s] nM\n', qs.name, dil, sprintf('%4.1f ',qs.ct),sprintf('%7.2f ',qs.conc));
      end

      % Check for any missed ones
      for i=1:prod(size(obj.q.ctgrid))
        if isfinite(obj.q.ctgrid(i)) && isempty(obj.q.primers{i})
          fprintf(' Undetermined primer for well %s with Ct=%.1f\n', obj.q.wellnames{i}, obj.q.ctgrid(i));
        end
      end
    end
  
  end
  
end
