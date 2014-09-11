% Adjust dilution factors based on reference signal
% refconc - reference concentration in nM
function data=adjustdilutions(data,refconc)
rtotal=0;rcnt=0;
for i=1:length(data.results)
  r=data.results{i};
  if isfield(r,'REF')
    rtotal=rtotal+r.REF.conc;
    rcnt=rcnt+1;
  end
end
if rcnt==0
  fprintf('No dilution references - using nominal dilutions\n');
  return;
end
meanref=rtotal/rcnt;
fprintf('Mean reference before adjusting dilutions is %.1f nM\n', meanref);
if nargin<2
  refconc=meanref;
end
fprintf('Adjusting dilutions such that reference is always %.1f nM\n', refconc);
for i=1:length(data.results)
  r=data.results{i};
  if isfield(r,'REF')
    scale=refconc/r.REF.conc;
    if scale<1/1.5 || scale>1.5
      fprintf('Warning: For %s the reference-based dilution is %.2f times that expected.\n', r.name, 1.0/scale);
    end
    r.dilution=r.dilution/scale;
    primers=fieldnames(data.primers);
    for p=1:length(primers)
      if isfield(r,primers{p})
        r.(primers{p}).conc=r.(primers{p}).conc*scale;
      end
    end
    data.results{i}=r;
  end
end
