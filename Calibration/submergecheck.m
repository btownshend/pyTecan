% Run check that tracking during aspirate doesn't cause tip to come out of liquid
%gfit=[5.17,29.25]
for startheight=1:30
  gv1=gemcalcvol(startheight,gmdl);
  v1=calcvol2(startheight,[],[],angle,fit(1),fit(2),fit(3),fit(4),fit(5),fit(6:8));
  for endheight=0:startheight-1
    v2=calcvol2(endheight,[],[],angle,fit(1),fit(2),fit(3),fit(4),fit(5),fit(6:8));
    if v1-v2>200 || v2<15
      continue;   % Can only pipette up to 200, always leave at least 15ul behind
    end
    gh2=gemcalcheight(v2+gv1-v1,gmdl);
    if gh2>endheight+0.5
      fprintf('At end of aspirate of %.1f ul from %.1f ul, gemini will be %.1f mm too high\n', v1-v2, v1, gh2-endheight);
    end
  end
end


