function samps=wellnames2pos(wells)
  samps=[];
  for i=1:length(wells)
    w=wells{i};
    col=str2num(w(2:end));
    row=w(1)-'A'+1;
    samps=[samps,(col-1)+(row-1)*12];
    %    fprintf('%s: %d,%d = %d\n', w, col, row, samps(end));
  end
end
