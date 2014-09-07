% Take a robotanalyze output from a TRP run and use internal references to compute stats
function x=refanalyze(x)
refconc=10;
primers=fieldnames(x.primers);
for i=1:length(x.results)
  if isfield(x.results{i},'REF')
    r=x.results{i};
    scale=r.REF.conc/refconc;
    fprintf('Sample %s: REF=%.1f, scale=%.2f\n', r.tmpl, r.REF.conc, scale);
    for j=1:length(primers)
      if isfield(r,primers{j})
        r.(primers{j}).conc=r.(primers{j}).conc/scale;
      end
    end
    x.results{i}=r;
    x.results{i}.refscale=scale;
  end
end
