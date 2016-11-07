% Entry of data 
classdef Run < handle
  properties
    desc;
    primers;
    color;
  end
  
  methods
    function obj=Run(desc,primers,color)
      obj.desc=desc;
      obj.primers=primers;
      obj.color=color;
    end

    function print(obj)
      fprintf('Run: %s, %s, %s\n', obj.desc, obj.primers, obj.color);
    end

    function ind=getind(obj,s)
      ind=find(strcmp(s,obj.primers),1);
    end

    function v=getval(obj,vals,s)
      ind=obj.getind(s);
      if isempty(ind)
        v=nan;
      else
        v=vals(ind);
      end
    end
  end
end
