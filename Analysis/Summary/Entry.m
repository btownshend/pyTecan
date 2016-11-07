% Entry of data 
classdef Entry < handle
  properties
    run;
    t7;
    ext;
    ind; % index of [m,clvd,unclvd]
    in;	% Source sample
    out;	% Output sample
    tgt;	% Targets present during run (or empty if none)
    stype;	% C or U
  end
  
  methods
    function obj=Entry(run, t7,ext, ind, in, out, tgt, stype)
      obj.run=run;
      obj.t7=t7;
      obj.ext=ext;
      obj.ind=ind;
      obj.in=in;
      obj.out=out;
      obj.tgt=tgt;
      obj.stype=stype;
    end
    
    function s=concstr(obj,v)
      assert(length(v)==length(obj.run.primers));
      s='[';
      for i=1:length(v)
        if isfinite(v(i))
          if length(s)>1
            s=[s,', '];
          end
          if v(i)>10
            fmt='%4.0f';
          elseif v(i)>1
            fmt='%4.1f';
          elseif v(i)>0.1
            fmt='%4.2f';
          else
            fmt='%.2g';
          end
          s=[s,sprintf(['%s=',fmt],obj.run.primers{i},v(i))];
        end
      end
      s=[s,']'];
    end
    
      
    function print(obj)
      fprintf('%s ',obj.run.desc);
      if isempty(obj.tgt)
        fprintf(' %s->%s\n', obj.in.name, obj.out.name);
      else
        fprintf(' %s-%s->%s\n', obj.in.name, obj.tgt, obj.out.name);
      end
      if any(isfinite(obj.t7))
        fprintf('   T7:  %s ', obj.concstr(obj.t7));
        inconc=obj.run.getval(obj.t7,'T7X')/obj.run.getval(obj.t7,'REF')*50;
        if isfinite(inconc)
          fprintf('T7X/REF*50=%.0f nM',inconc);
        end
        fprintf('\n');
      end
      if any(isfinite(obj.ext))
        fprintf('   Ext: %s ', obj.concstr(obj.ext));
        aratio=obj.run.getval(obj.ext,'AX')/obj.run.getval(obj.ext,'MX');
        bratio=obj.run.getval(obj.ext,'BX')/obj.run.getval(obj.ext,'MX');
        wratio=obj.run.getval(obj.ext,'WX')/obj.run.getval(obj.ext,'MX');
        t7ratio=obj.run.getval(obj.ext,'MX')/obj.run.getval(obj.ext,'T7X');
        if isfinite(aratio)
          fprintf('A/M=%.2f ',aratio);
        end
        if isfinite(bratio)
          fprintf('B/M=%.2f ',bratio);
        end
        if isfinite(aratio)
          fprintf('W/M=%.2f ',wratio);
        end
        if isfinite(aratio)
          fprintf('M/T7=%.1f ',t7ratio);
        end
        fprintf('\n');
      end
    end
    
    function r=ratios(obj)
      if length(obj.ind)==3
        r=obj.ext(obj.ind(2:3))/obj.ext(obj.ind(1));
      else
        r=NaN;
      end
    end

    function c=cleaveRatio(obj)
      if length(obj.ind)==3
        c=obj.ext(obj.ind(2))/obj.ext(obj.ind(3));
        if isinf(c) || c>10
          c=10;
        elseif c<0.01
          c=0.01;
        end
      else
        c=NaN;
      end
    end

    function r=rnagain(obj)
      mx=find(strcmp(obj.run.primers,'MX'),1);
      t7x=find(strcmp(obj.run.primers,'T7X'),1);
      if isempty(mx) || isempty(t7x)
        r=nan;
      else
        r=obj.ext(mx)/obj.ext(t7x)-1;
      end
    end
  end
end
