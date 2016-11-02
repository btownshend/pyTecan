% Summary of data 
classdef Summary < handle
  properties
    runs;
    runprimers;   % Primers (in order) used for this run
    runcolor;	  % Color to use to display
    samps;
    data;
  end
  
  methods
    function obj=Summary()
      obj.samps={};
      obj.runs={};
      obj.runprimers={};
      obj.data={[]};
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
    
    function n=getsamp(obj,name)
      sel=strcmp(obj.samps,name);
      if sum(sel)==1
        n=find(sel);
      else
        obj.samps{end+1}=name;
        n=length(obj.samps);
      end
    end
        
      
    function add(obj,run,in,out,t7,ext,ind,rndnum)
      if nargin<8
        rndnum=[];
      end
      in=obj.getsamp(in); 
      if size(obj.data,1)>=in && size(obj.data,2)>=out
        obj.data{in,out}=[obj.data{in,out},e];
      else
        obj.data{in,out}=e;
      if ~isempty(out)
        out=obj.getsamp(out);
      end
      e=Entry(run,t7,ext,ind,rndnum,out);
    end
    
    function h=plotcleavage(obj,name,depth,track,prior,priorrnd)
    % Plot cleavage starting with 'name'
      if nargin<3
        depth=1;
      end
      if nargin<4
        track=1;
      end
      if nargin<5
        prior=nan;
        priorrnd=nan;
      end
      fprintf('plotcleavage(%s,%d,%d,%.2f,%d)\n', name, depth,track,prior,priorrnd);
      is=find(strcmp(obj.samps,name));
      if is>size(obj.data,1)
        return;
      end
      colors='rgbmcyk';
      for j=1:size(obj.data,2)
        d=obj.data{is,j};
        if ~isempty(d)
          cOVERu=arrayfun(@(z) z.cleavage(),d);
          fprintf('%s%s: %s -> %s  [ %s ]\n',blanks(depth*2),obj.runs{d(1).run},obj.samps{is},obj.samps{j},sprintf('%.2f ',cOVERu));
          for k=1:length(cOVERu)
            if isempty(d(k).rndnum)
              rndnum=depth;
            else
              rndnum=d(k).rndnum;
            end
            h=semilogy(rndnum,cOVERu(k),['o',colors(mod(track-1,length(colors))+1)]);
            hold on;
            color=obj.runcolor{d(k).run};
            if isempty(color)
              color=colors(mod(track-1,length(colors))+1);
            end
            if rndnum==1
              prior=cOVERu(k);
              plot([rndnum-0.6,rndnum],[cOVERu(k),cOVERu(k)],[':',color]);
              text(rndnum-0.6,cOVERu(k),name);
            else
              plot([priorrnd,rndnum],[prior,cOVERu(k)],['-',color]);
            end
            rps=obj.runprimers{d(k).run};
            prefix=rps{d(k).ind(2)};
            %prefix=strrep(prefix,'T7','');
            if prefix(end)=='X'
              prefix=prefix(1:end-1);
            end
            text(rndnum+0.05,cOVERu(k),[obj.samps{j},'-',prefix]);
            if isfinite(prior)
              text((priorrnd+rndnum)/2,sqrt(prior*cOVERu(k)),obj.runs{d(k).run}(5:8));
            else
              text(rndnum-0.5,cOVERu(k),obj.runs{d(k).run}(5:8));
            end
          end
          obj.plotcleavage(obj.samps{j},depth+1,track,mean(cOVERu),rndnum);
          %track=track+1;
        end
      end
      if depth==1
        cleaveticks(0,1,0.01,0.9,true);
        ylabel('clvd/(clvd+unclvd)');
        xlabel('Round');
        axis auto;
        c=axis;
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
