% Entry of data 
% Samples contain cleavage information based on what the cleavage was on the operation that 
% formed them, NOT what will be observed if they are run in a TRP
classdef Sample < handle
  properties
    name;
    prefix;
    rndnum;
    srcEntry;	% Entry whose PRODUCT is this sample
    cleaveratio;
    products;
  end
  
  methods
    function obj=Sample(name,prefix,rndnum)
      obj.name=name;
      obj.prefix=prefix;
      obj.rndnum=rndnum;
      obj.srcEntry=[];
      obj.products=[];
    end
    
    function [c,estimated]=cleaveRatio(obj)
    % Get the cleavage ratio of the sample
    % If no particular data, use estimate based on average of product's and return negative of value
      if isempty(obj.srcEntry) || ~isfinite(obj.srcEntry.cleaveRatio())
        prodRatios=arrayfun(@(z) z.cleaveRatio(), obj.products);
        c=exp(nanmean(log(prodRatios)));
        estimated=true;
      else
        c=obj.srcEntry.cleaveRatio();
        estimated=false;
      end
    end
    
    function g=rnagain(obj)
      if isempty(obj.srcEntry) || ~isfinite(obj.srcEntry.cleaveRatio())
        g=nan;
      else
        g=obj.srcEntry.rnagain();
      end
    end

    function addSrcEntry(obj,e)
      assert(isempty(obj.srcEntry));
      obj.srcEntry=e;
    end
    
    function addProduct(obj,p)
      obj.products=[obj.products,p];
    end

    function print(obj)
      if ~isempty(obj.srcEntry)
        obj.srcEntry.print();
      end
    end
  end
end
