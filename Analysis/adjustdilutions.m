% Adjust dilution factors based on reference signal
% refconc - reference concentration in nM
function data=adjustdilutions(data,refconc,refid)
if nargin<3
  refid='REF';
end
rtotal=0;rcnt=0;
for i=1:length(data.results)
  r=data.results{i};
  if isfield(r,refid)
    rtotal=rtotal+r.(refid).conc;
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
  if isfield(r,refid)
    scale=refconc/r.(refid).conc;
    if scale<1/1.5 || scale>1.5
      fprintf('Warning: For %s the reference-based dilution is %.2f times that expected.\n', r.name, 1.0/scale);
    end
    fprintf('Adjusting %s by %.2fx; dilution went from %.0f to %.0f\n', r.name, scale, r.dilution, r.dilution*scale);
    r.dilution=r.dilution*scale;
    primers=fieldnames(data.primers);
    for p=1:length(primers)
      if isfield(r,primers{p})
        rnew=r.(primers{p}).conc*scale;
        fprintf(' Adjusting %s from %.2f to %.2f\n', primers{p}, r.(primers{p}).conc, rnew);
        r.(primers{p}).conc=rnew;
      end
    end
    data.results{i}=r;
  end
end
