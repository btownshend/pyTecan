% Build model to vol, height data using Gemini built-in structure (simple cone+cylinder)
% Fit parameters are depth of bottom, area
% Use max fit error as criteria
function gmdl=geminifit(vol,heights,x0,gmdl)
useoffset=false;
fitradius=true;
plot(vol,heights,'g','LineWidth',2);
leg={'Desired'};
hold on;
xlabel('Volume (ul)');
ylabel('Height above ZMax (mm)');
if nargin<4
  if nargin<3
    x0=[4,16.4,0];
  end
  gmdl0=struct('depth',x0(1),'area',x0(2),'hoffset',x0(3));
  %plot(gemcalcvol(heights,gmdl0),heights,'m','LineWidth',2);
  %leg{end+1}='IC';
  options=optimset('Display','notify','TolFun',1e-8,'TolX',1e-8);
  fprintf('Matching Gemini model over range of %.1f-%.1f ul using %d points\n', min(vol), max(vol), length(vol));
  if useoffset
    fit=fminsearch(@(x) sum((gemcalcheight(vol,struct('depth',x(1),'area',x(2),'hoffset',x(3)))-heights).^2),x0,options);
    gmdl=struct('depth',fit(1),'area',fit(2),'hoffset',fit(3));
  elseif fitradius
    % Seems that fitting for minimizing height error gives poor fit (stuck in local minima)
    %fit=fminsearch(@(x) sum((gemcalcheight(vol,struct('depth',x(1),'area',x(2),'hoffset',0))-heights).^2),x0(1:2),options);
    fit=fminsearch(@(x) sum((gemcalcvol(heights,struct('depth',x(1),'area',x(2),'hoffset',0))-vol).^2),x0(1:2),options);
    % Refitting using above fit does work though, gives similar solution
    %fit=fminsearch(@(x) sum((gemcalcheight(vol,struct('depth',x(1),'area',x(2),'hoffset',0))-heights).^2),fit(1:2),options);
    gmdl=struct('depth',fit(1),'area',fit(2),'hoffset',0);
    if gmdl.depth<0
      fprintf('Best fit has negative depth (%f), which is illegal; refitting with depth=0\n',gmdl.depth);
      fit=fminsearch(@(x) sum((gemcalcvol(heights,struct('depth',0,'area',x(1),'hoffset',0))-vol).^2),gmdl.area,options);
      gmdl=struct('depth',0,'area',fit(1),'hoffset',0);
    end
  else
    area=51.84;
    fit=fminsearch(@(x) max(abs(gemcalcheight(vol,struct('depth',x(1),'area',area,'hoffset',0))-heights)),x0(1),options);
    gmdl=struct('depth',fit(1),'area',area,'hoffset',0);
  end
else
  fprintf('Using fixed Gemini model\n');
end
hest=gemcalcheight(vol,gmdl);
rmse=sqrt(nanmean((heights-hest).^2));
maxerr=[min(heights-hest),max(heights-hest)];
vest=gemcalcvol(heights,gmdl);
vrmse=sqrt(nanmean((vol-vest).^2));
vmaxerr=[min(vol-vest),max(vol-vest)];
vmaxfrac=max(abs((vol-vest)./vol));
fprintf('Gemini fit:  depth=%.2f mm, area=%.2f mm^2, r=%.2fmm, offset=%.2fmm\n', gmdl.depth, gmdl.area,sqrt(gmdl.area/pi),gmdl.hoffset);
fprintf('Height RMSE = %.2f mm, max = %.2f:%.2f mm\n', rmse,maxerr);
fprintf('Volume RMSE = %.2f ul, max = %.2f:%.2f ul (%.0f%%)\n', vrmse,vmaxerr,vmaxfrac*100);
plot(gemcalcvol([0,heights],gmdl),[0,heights],'k','LineWidth',2);
leg{end+1}='Fit';
plot(vol,gemcalcheight(vol,gmdl),'k','LineWidth',2);
legend(leg,'Location','NorthWest');
