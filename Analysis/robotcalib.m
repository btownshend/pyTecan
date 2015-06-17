% Create a calibrated qPCR object from a robot analysis
function r=robotcalib(r,varargin)
defaults=struct('refconc',50,'units','pM');
args=processargs(defaults,varargin);
q=QPCR(r.opd.ctgrid);
q.lengrid(:)=nan;
primers={};
for i=1:length(r.results)
  fn=fieldnames(r.results{i});
  for j=1:length(fn)
    if isstruct(r.results{i}.(fn{j})) && isfield(r.results{i}.(fn{j}),'length')
      rr=r.results{i}.(fn{j});
      q.lengrid(q.parsewells(rr.samp.well))=rr.length;
      fprintf('i=%d,%s  well %d = %d\n', i, fn{j}, rr.well+1, rr.length);
      primers=union(primers,{fn{j}});
    end
  end
end
refs=find(strcmp(cellfun(@(z) z.tmpl, r.results,'UniformOutput',false),'QPCRREF'));
refs=[refs,find(strcmp(cellfun(@(z) z.tmpl, r.results,'UniformOutput',false),'Water'))];
if isempty(refs)
  fprintf('No QPCR references found');
  return;
end
for ip=1:length(primers)
  primer=primers{ip};
  concs=[];
  wells={};
  for i=1:length(refs)
    rr=r.results{refs(i)};
    if isfield(rr,primer)
      if strcmp(rr.name,'Water')
        concs=[concs,0];
      else
        concs=[concs,args.refconc/rr.dilution];
      end
      wells{end+1}=rr.(primer).samp.well;
    end
  end
  q.addref(primer,wells,concs,'units',args.units);
end
for ip=1:length(primers)
  primer=primers{ip};
  for i=1:length(r.results)
    if isfield(r.results{i},primer)
      [r.results{i}.(primer).conc,r.results{i}.(primer).conclow,r.results{i}.(primer).conchigh]=q.getconc(primer,r.results{i}.(primer).samp.well);
    end
  end
end
r.qpcr=q;

