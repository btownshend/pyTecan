function s=concfmt(c,dpoints)
if nargin<2
  dpoints=1;
end
if c>=1
  units='M';
elseif c>=1e-3
  units='mM'; c=c*1000;
elseif c>=1e-6
  units='uM'; c=c*1e6;
elseif c>=1e-9
  units='nM'; c=c*1e9;
elseif c>=1e-12
  units='pM'; c=c*1e12;
elseif c>=1e-15
  units='fM'; c=c*1e15;
else
  fmt=sprintf('%%%d.%dg M',dpoints+5,dpoints+1);
  s=sprintf(fmt,c);
  return;
end
fmt=sprintf('%%%d.%df %%-2.2s',dpoints+4,dpoints);
s=sprintf(fmt,c,units);

    