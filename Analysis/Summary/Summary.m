% Summary of data 
classdef Summary < handle
  properties
    runs;
    runprimers;   % Primers (in order) used for this run
    runcolor;	  % Color to use to display
    samps;
    data;
    anonID;	   % ID for anonymous samples
  end
  
  methods
    function obj=Summary()
      obj.samps=containers.Map();
      obj.runs={};
      obj.runprimers={};
      obj.data={[]};
      obj.anonID=1;
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
      
    function add(obj,run,in,out,t7,ext,ind,rndnum)
      if nargin<8
        rndnum=[];
      end
      in=obj.getsamp(in); 
      if isempty(out)
        out=obj.addsamp(sprintf('z%d',obj.anonID),'?',in.rndnum+1);
        obj.anonID=obj.anonID+1;
      else
        out=obj.getsamp(out);
      end
      e=Entry(run,t7,ext,ind,rndnum,out);
      in.addEntry(e);
    end
    
    function h=plotcleavage(obj,samp,track,prior)
    % Plot cleavage starting with 'samp'
      if nargin<3
        track=1;
      end
      if nargin<4
        prior=[];
      end
      if isempty(prior)
        fprintf('plotcleavage(%s@%.2f,%d)\n', samp.name, samp.cleaveratio,track);
      else
        fprintf('plotcleavage(%s@%.2f,%d,%s@%.2f)\n', samp.name, samp.cleaveratio, track, prior.name,prior.cleaveratio);
      end
      colors='rgbmcyk';
      for j=1:size(samp.data,2)
        d=samp.data(j);  % An Entry
        cOVERu=d.cleavage();
        if ~isempty(d.out)
          fprintf('%s%s: %s -> %s  %.2f\n',blanks(samp.rndnum*2),obj.runs{d(1).run},samp.name,d.out.name,cOVERu);
        else
          fprintf('%s%s: %s -> %.2f\n',blanks(samp.rndnum*2),obj.runs{d(1).run},samp.name,cOVERu);
        end
        h=semilogy(samp.rndnum+1,cOVERu,['o',colors(mod(track-1,length(colors))+1)]);
        hold on;
        color=obj.runcolor{d.run};
        if isempty(color)
          color=colors(mod(track-1,length(colors))+1);
        end
        if isempty(prior)
          plot([samp.rndnum+0.6,samp.rndnum+1],[cOVERu,cOVERu],[':',color]);
          text(samp.rndnum+0.2,cOVERu,samp.name);
        else
          plot([prior.rndnum,samp.rndnum]+1,[prior.cleaveratio,cOVERu],['-',color]);
        end
        rps=obj.runprimers{d.run};
        if ~isempty(d.out) && d.out.name(1)~='z'
          text(samp.rndnum+1.05,cOVERu,[d.out.name,'-',d.out.prefix]);
        end
        rtext=obj.runs{d.run};
        if length(rtext)>=8 && strcmp(rtext(1:2),'20')
          rtext=rtext(5:8);
        end
        if ~isempty(prior) && isfinite(prior.cleaveratio)
          text((prior.rndnum+samp.rndnum)/2+1,sqrt(prior.cleaveratio*cOVERu),rtext);
        else
          text(samp.rndnum+0.5,cOVERu,rtext);
        end
      end
      for j=1:size(samp.data,2)
        d=samp.data(j);  % An Entry
        if ~isempty(d.out)
          obj.plotcleavage(d.out,track,samp);
        end
      end
      %track=track+1;

      if nargin<4
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
