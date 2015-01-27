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
  if length(indtmpl)<1
    fprintf('getcleavages: Unable to locate template for %s\n', tmpl);
    continue;
  end
  if length(indtmpl)>1
    fprintf('getcleavages: Multiple possible templates for %s\n', tmpl);
    keyboard
    continue;
  end
  if length(indlig)<1
    fprintf('getcleavages: Unable to locate ligation product for %s\n', tmpl);
    continue;
  end
  
  for ii=1:length(indlig)
    lig=data.results{indlig(ii)};
    t=data.results{indtmpl};
  
    % Figure out prefix of template, ligation product
    % each entry in this table is {template qPCR product, ligation qPCR product, ligation prefix} 
    pairs={{'WX','AX','AT7'},{'WX','BX','BT7W'},{'AS','BS','BN7'},{'BS','AS','AN7'},{'BS','WS','WN7'},{'AX','BX','BN7'},{'BX','AX','AN7'},{'MX','AX','AT7'},{'MX','BX','BT7W'},{'MX','AX','AN7'},{'MX','BX','BN7'},{'WX','AX','AN7'}};
    thepair=[];
    for j=1:length(pairs)
      p=pairs{j};
      if isfield(t,p{1}) && isfield(lig,p{1}) && isfield(lig,p{2}) && strcmp(p{3},lig.ligprefix)
        thepair=p;
        break;
      end
    end
    if isempty(thepair)
      fprintf('Unable to determine template/ligation prefixes for %s\n',lig.name);
      continue;
    end
    lig.ucpair=thepair(1:2);
    
    if strcmp(thepair{1},'MX') && strcmp(thepair{3},'AT7')
      % New method: MX is total including template, AX is uncleaved only
      total=lig.(thepair{1}).conc;
      tmplc=t.(thepair{1}).conc;
      unclvd=lig.(thepair{2}).conc;
      yield=total-tmplc;
      clvd=yield-unclvd;
    elseif strcmp(thepair{1},'MX') && strcmp(thepair{3},'BT7W')
      % New method: MX is total including template, BX is cleaved only
      total=lig.(thepair{1}).conc;
      tmplc=t.(thepair{1}).conc;
      clvd=lig.(thepair{2}).conc;
      yield=total-tmplc;
      unclvd=yield-clvd;
    else
      clvd=lig.(thepair{2}).conc;
      unclvd=lig.(thepair{1}).conc-t.(thepair{1}).conc;
      yield=clvd+unclvd;
    end
    
    if unclvd<0
      fprintf('Warning: %s has inconsistent MX concentration.\n', tmpl);
      continue;
    end
    lig.cleavage=clvd/(clvd+unclvd);
    lig.yield=yield;
    lig.rnagain=yield/t.(thepair{1}).conc;
    
    data.results{indlig(ii)}=lig;
  end
end


