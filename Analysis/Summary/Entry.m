% Entry of data 
classdef Entry < handle
  properties
    run;
    t7;
    ext;
    ind; % index of [m,clvd,unclvd]
    rndnum;
  end
  
  methods
    function obj=Entry(run, t7,ext, ind, rndnum)
      obj.run=run;
      obj.t7=t7;
      obj.ext=ext;
      obj.ind=ind;
      if nargin>=5
        obj.rndnum=rndnum;
      else
        obj.rndnum=[];
      end
    end
    
    function print(obj)
      fprintf('   T7:  [%s]\n', sprintf('%.1f ',obj.t7));
      fprintf('   Ext: [%s]\n', sprintf('%.1f ',obj.ext));
      fprintf('   x/M: %.1f%% %.1f%%\n', obj.ratios()*100);
    end
    
    function r=ratios(obj)
      r=obj.ext(obj.ind(2:3))/obj.ext(obj.ind(1));
    end
  end
end
