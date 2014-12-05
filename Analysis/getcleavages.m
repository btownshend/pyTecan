% Compute cleavages, yields etc
% Takes into account:
%  - template carry forward
%  - dilution adjustment using references (not yet)
function data=getcleavages(data)
fprintf('Computing net yields and cleavages\n');
tmpls=cellfun(@(z) z.tmpl, data.results,'UniformOutput',false);
types=cellfun(@(z) z.type, data.results,'UniformOutput',false);
utmpls=unique(tmpls);
for i=1:length(utmpls)
  tmpl=utmpls{i};
  fprintf('Processing %s\n', tmpl);
  % Locate template measurement and ligation measurement
  indtmpl=find(strcmp(tmpls,tmpl)&strcmp(types,'tmpl'));
  indlig=find(strcmp(tmpls,tmpl) &strcmp(types,'Lig'));
  if length(indtmpl)~=1
    fprintf('getcleavages: Unable to locate template for %s\n', tmpl);
    continue;
  end
  if length(indlig)~=1 && length(indlig)~=2
    fprintf('getcleavages: Unable to locate ligation product for %s\n', tmpl);
    continue;
  end
  
  for ii=1:length(indlig)
    lig=data.results{indlig(ii)};
    t=data.results{indtmpl};
  
    % Figure out prefix of template, ligation product
    pairs={{'WX','AX'},{'AS','BS'},{'BS','AS'},{'BS','WS'},{'AX','BX'},{'BX','AX'},{'MX','AX'},{'MX','BX'}};
    thepair=[];
    for j=1:length(pairs)
      p=pairs{j};
      if isfield(t,p{1}) && isfield(lig,p{1}) && isfield(lig,p{2}) && p{2}(1)==lig.ligprefix
        thepair=p;
        break;
      end
    end
    if isempty(thepair)
      fprintf('Unable to determine template/ligation prefixes\n');
      keyboard
      continue;
    end
    lig.ucpair=thepair;
    
    if strcmp(thepair{1},'MX')
      % New method: MX is total including template, AX is uncleaved only, BX is cleaved only
      total=lig.(thepair{1}).conc;
      tmplc=t.(thepair{1}).conc;
      if strcmp(thepair{2},'AX')
        unclvd=lig.(thepair{2}).conc;
        yield=total-tmplc;
        clvd=yield-unclvd;
      else
        clvd=lig.(thepair{2}).conc;
        yield=total-tmplc;
        unclvd=yield-clvd;
      end
    else
      clvd=lig.(thepair{2}).conc;
      unclvd=lig.(thepair{1}).conc-t.(thepair{1}).conc;
      yield=clvd+unclvd;
    end
    
    if unclvd<0
      fprintf('Warning: %s has less template in the ligation product than it started with\n', tmpl);
      continue;
    end
    lig.cleavage=clvd/(clvd+unclvd);
    lig.yield=yield;
    lig.rnagain=yield/t.(thepair{1}).conc;
    
    data.results{indlig(ii)}=lig;
  end
end


