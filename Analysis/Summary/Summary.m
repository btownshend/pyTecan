% Summary of data 
classdef Summary < handle
  properties
    runs;
    runprimers;   % Primers (in order) used for this run
    runcolor;	  % Color to use to display
    samps;
    data;
    anonID;	   % ID for anonymous samples
    showruns;	   % True to show run IDs on plots
  end
  
  methods
    function obj=Summary()
      obj.samps=containers.Map();
      obj.runs={};
      obj.runprimers={};
      obj.data={[]};
      obj.anonID=1;
      obj.showruns=false;
    end

    function r=addrun(obj,desc,lbls,color)
      obj.runs{end+1}=desc;
      obj.runprimers{end+1}=lbls;
      if nargin>=4
        obj.runcolor{end+1}=color;
      else
        obj.runcolor{end+1}=[];
      end
      r=length(obj.runs);
    end
    
    function s=addsamp(obj,name,prefix,rndnum)
      if obj.samps.isKey(name)
        error('Sample %s already exists.',name);
      end
      s=Sample(name,prefix,rndnum);
      obj.samps(name)=s;
    end
    
    function n=getsamp(obj,name)
      if ~obj.samps.isKey(name)
        error('Sample %s does not exist.',name);
      end
      n=obj.samps(name);
    end
    
    function n=anonsamp(obj,rndnum)
        n=obj.addsamp(sprintf('z%d',obj.anonID),'?',rndnum);
        obj.anonID=obj.anonID+1;
    end
    
    function add(obj,run,stype,in,out,t7,ext,ind,tgt)
      if nargin<9
        tgt=[];
      end
      in=obj.getsamp(in); 
      if isempty(out)
        out=obj.anonsamp(in.rndnum+1);
      else
        out=obj.getsamp(out);
      end
      if strcmp(stype,'UC')
        % Break into 2 runs
        assert(out.rndnum==in.rndnum+2);
        tmp=obj.anonsamp(in.rndnum+1);
        tmp.prefix=in.prefix;
        obj.add(run,'U',in.name,tmp.name,t7,nan*ext,ind,tgt);
        obj.add(run,'C',tmp.name,out.name,nan*t7,ext,ind,[]);
        return;
      end
      if out.prefix(1)=='?'
        if strcmp(stype,'U')
          out.prefix=in.prefix;
        else
          if strcmp(in.prefix,'W')
            out.prefix='A';
          elseif strcmp(in.prefix,'A')
            out.prefix='B';
          else
            out.prefix='W';
          end
        end
      end
      
      assert(out.rndnum==in.rndnum+1 || out.rndnum==in.rndnum);
      if length(ind)==3 && isfinite(ind(3))
        assert(strcmp(obj.runprimers{run}{ind(1)},'MX'));
        assert(strcmp(obj.runprimers{run}{ind(3)},[in.prefix,'X']));
        if stype=='C'
          assert(strcmp(obj.runprimers{run}{ind(2)},[out.prefix,'X']));
        else
          assert(strcmp(in.prefix,out.prefix));
        end
      end
      e=Entry(run,t7,ext,ind,in,out,tgt,stype);
      out.addSrcEntry(e);
      in.addProduct(out);
    end
    
    function plotall(obj)
      setfig('plotall');clf;
      k=obj.samps.keys();
      for i=1:length(k)
        s=obj.samps(k{i});
        for j=1:length(s.data)
          semilogy(s.rndnum,s.data(j).cleavage(),'o');
          hold on;
          text(s.rndnum+0.2,s.data(j).cleavage(),s.name);
        end
      end
      cleaveticks(0,1,0.01,0.9,true);
      ylabel('clvd/(clvd+unclvd)');
      xlabel('Round');
      axis auto;
      c=axis;
      c(1)=0;
      axis(c);
      set(gca,'XTick',1:c(2));
      lbls={};
      for i=1:c(2)
        lbls{i}=sprintf('%d',i);
      end
      set(gca,'XTickLabel',lbls);
    end
    
    function h=plotcleavage(obj,samp,track)
    % Plot cleavage starting with 'samp'
      if nargin<3
        track=1;
      end
      colors='rgbmcyk';
      [cr,estimated]=samp.cleaveRatio();
      if estimated
        sym='x';
      else
        sym='o';
      end
      fprintf('plotcleavage(%s@%.2f(%s),%d)\n', samp.name, cr, sym,track);
      h=semilogy(samp.rndnum,cr,[sym,colors(mod(track-1,length(colors))+1)]);
      hold on;
      if samp.name(1)~='z'
        text(samp.rndnum+0.05,cr/1.1,[samp.name,'-',samp.prefix]);
      end
      
      d=samp.srcEntry;  % An Entry
      if isempty(d)
        fprintf('No source for %s\n', samp.name);
      else
        color=obj.runcolor{d.run};
        if isempty(color)
          color=colors(mod(track-1,length(colors))+1);
        end
        [inRatio,inEst]=d.in.cleaveRatio();
        if inEst || estimated
          sym=':';
        else
          sym='-';
        end
        plot([d.in.rndnum,samp.rndnum],[inRatio,cr],[sym,color]);

        if obj.showruns
          rtext=obj.runs{d.run};
          if length(rtext)>=8 && strcmp(rtext(1:2),'20')
            rtext=rtext(5:8);
          end
        else
          rtext='';
        end
        if ~isempty(d.tgt)
          rtext=[rtext,'+',d.tgt];
        end
        text((d.in.rndnum+samp.rndnum)/2,sqrt(inRatio*cr)*1.1,rtext,'Color','g');
      end
      
      for j=1:length(samp.products)
        obj.plotcleavage(samp.products(j),track);
      end

      if nargin<3
        cleaveticks(0,1,0.01,0.9,true);
        ylabel('clvd/(clvd+unclvd)');
        xlabel('Round');
        axis auto;
        c=axis;
        c(1)=0;
        c(3)=min([c(3),.01/.99]);
        c(4)=max([c(4),.9/.1]);
        axis(c);
        set(gca,'XTick',1:c(2));
        lbls={};
        for i=1:c(2)
          lbls{i}=sprintf('%d',i);
        end
        set(gca,'XTickLabel',lbls);
      end
    end
      
    function h=plotgain(obj,name,depth,track,prior)
    % Plot gain starting with 'name'
      if nargin<3
        depth=1;
      end
      if nargin<4
        track=1;
      end
      if nargin<5
        prior=1;
      end
      fprintf('plotgain(%s,%d,%d,%.2f)\n', name, depth,track,prior);
      is=find(strcmp(obj.samps,name));
      if is>size(obj.data,1)
        return;
      end
      colors='rgbmcyk';
      for j=1:size(obj.data,2)
        d=obj.data{is,j};
        if ~isempty(d)
          gain=arrayfun(@(z) z.ext(2)/z.ext(4),d);
          fprintf('%s%s: %s -> %s  [ %s ]\n',blanks(depth*2),obj.runs{d(1).run},obj.samps{is},obj.samps{j},sprintf('%.2f ',gain));
          for k=1:length(gain)
            h=plot(depth,gain(k),['o',colors(mod(track-1,length(colors))+1)]);
            hold on;
            if depth==1
              prior=gain(k);
              plot([depth-0.6,depth],[gain(k),gain(k)],[':',colors(mod(track-1,length(colors))+1)]);
            else
              plot([depth-1,depth],[prior,gain(k)],['-',colors(mod(track-1,length(colors))+1)]);
            end
            text(depth,gain(k),obj.samps{j});
            text(depth-0.53,mean([prior,gain(k)]),obj.runs{d(k).run}(end-1:end));
          end
          obj.plotgain(obj.samps{j},depth+1,track,mean(gain));
          %track=track+1;
        end
      end
      if depth==1
        ylabel('RNA Gain (M/T7)');
        xlabel('Round (with prefix of input)');
        axis auto;
        c=axis;
        set(gca,'XTick',1:c(2));
        lbls={};
        for i=1:c(2)
          lbls{i}=sprintf('%d%s',obj.runlabels{obj.data{is,i}.ind(3)});
        end
        set(gca,'XTickLabel',lbls);
      end
    end
      
    function print(obj)
      for i=1:size(obj.data,1)
        for j=1:size(obj.data,2)
          d=obj.data{i,j};
          if ~isempty(d)
            fprintf('%s -> %s\n',obj.samps{i},obj.samps{j});
            for k=1:length(d)
              fprintf(' %s\n', obj.runs{d(k).run});
              d(k).print();
            end
          end
        end
      end
    end
  end
end
