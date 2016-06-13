% Run check that tracking during aspirate doesn't cause tip to come out of liquid
%gfit=[5.17,29.25]
for startheight=[1:30]
  gv1=gemcalcvol(startheight,gmdl);
  v1=calcvol2(startheight,[],[],angle,fit(1),fit(2),fit(3),fit(4),fit(5),fit(6:8));
  maxerr=0;maxendheight=0;maxv2=0;
  minerr=1000;minendheight=0;minv2=0;
  for endheight=(0:0.01:1)*startheight
    v2=calcvol2(endheight,[],[],angle,fit(1),fit(2),fit(3),fit(4),fit(5),fit(6:8));
    if v1-v2>200 || v2<15
      continue;   % Can only pipette up to 200, always leave at least 15ul behind
    end
    gh2=gemcalcheight(gv1-(v1-v2),gmdl);
    if gh2-endheight>maxerr
      maxerr=gh2-endheight;
      maxendheight=endheight;
      maxv2=v2;
    end
    if gh2<minerr
      minerr=gh2-endheight;
      minendheight=endheight;
      minv2=v2;
    end
  end
  if maxerr>1.0
    fprintf('At end of aspirate of %5.1f ul from %5.1f ul, gemini will be %3.1f mm higher than it starts at\n', v1-maxv2, v1, maxerr);
  end
  if minerr<1
    fprintf('At end of aspirate of %5.1f ul from %5.1f ul, gemini will think is %3.1f mm below bottom\n', v1-minv2, v1, -minerr);
  end
end


