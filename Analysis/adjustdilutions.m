% Adjust dilution factors based on reference signal
% refconc - reference concentration in nM
function data=adjustdilutions(data,refconc)
fprintf('Adjusting dilutions such that reference is always %.1f nM\n', refconc);
for i=1:length(data.results)
  r=data.results{i};
  if isfield(r,'REF')
    scale=refconc/r.REF.conc;
    if scale<1/1.5 || scale>1.5
      fprintf('Warning: Large scaling factor for reference for %s: %.2f\n', r.name, scale);
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
