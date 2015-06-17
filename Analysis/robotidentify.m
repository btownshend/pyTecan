% Identify a qPCR sample by looking at its ingredients
% Return a structure containing field:
%  name: name of sample
%  tmpl: name of template
%  type: one of 'rt','tmpl','Lig','T7','PCR'
%  ligprefix: if type is lig, suffix of MLig*** used
%  primer: qPCR primer set used
%  pcrprimer: PCR primer set used
%  cond: target condition during transcription ('-','+', or '?')
% Returns [] if sample is not a qPCR product
function r=robotidentify(samp)

ignores={'Water','SSD','Dynabeads','MStpBeads','MStpX','MStopXBio','MLigase','BeadBuffer'};
targets={'Theo'};
hasT7=false;
hasRT=false;
hasPCR=false;
lig=[];
primer=[];
tmpl=[];
cond='';
for i=1:length(samp.ingredients)
  ingred=samp.ingredients{i};
  if strcmp(ingred,'MT7')
    hasT7=true;
  elseif strcmp(ingred,'MPosRT')
    hasRT=true;
  elseif strncmp(ingred,'MLig',4) && ~strcmp(ingred,'MLigase')
    lig=ingred(5:end);
  elseif strncmp(ingred,'MQ',2)
    primer=ingred(3:end);
  elseif strncmp(ingred,'MPCR',4)
    hasPCR=true;
    pcrprimer=ingred(5:end);
  elseif strncmp(ingred,samp.name,length(ingred))
    tmpl=ingred;
  elseif any(strcmp(targets,ingred))
    cond=[cond,'+',ingred];
  elseif any(strcmp(ignores,ingred))
    % Ignore this ingredient
    ;
  else
    cond='?';
    fprintf('Unrecognized ingredient: %s\n', ingred);
  end
end
r=struct('name',samp.name,'samp',samp);
if isempty(tmpl)
  fprintf('Unable to find template for %s\n',samp.name);
  return;
end
r.tmpl=tmpl;
if isempty(primer)
  fprintf('No qPCR primer for %s\n',samp.name);
  return;
end
r.primer=primer;

if ~isempty(lig)
  r.type='Lig';
  r.ligprefix=lig;
elseif hasRT
  r.type='rt';
elseif hasT7
  %  r.type='T7';
  r.type='tmpl';	% We treat this as a template measurement since the RNA is not amplifiable
else
  r.type='tmpl';
end
if hasPCR
  r.pcrprimer=pcrprimer;
end
if hasT7 && isempty(cond)
  r.cond='-';
else
  r.cond=cond;
end


