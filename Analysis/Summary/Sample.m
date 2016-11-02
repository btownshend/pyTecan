% Entry of data 
classdef Sample < handle
  properties
    name;
    prefix;
    rndnum;
    data;	% struct array of entries
    cleaveratio;
  end
  
  methods
    function obj=Sample(name,prefix,rndnum)
      obj.name=name;
      obj.prefix=prefix;
      obj.rndnum=rndnum;
      obj.data=[];
      obj.cleaveratio=nan;
    end
    
    function computeCleavage(obj)
      obj.cleaveratio=nanmean(arrayfun(@(z) z.cleavage(), obj.data));
    end

    function addEntry(obj,e)
      obj.data=[obj.data,e];
      obj.computeCleavage();
    end
  end
end
