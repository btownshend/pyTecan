% Build model to vol, height data using Gemini built-in structure (simple cone+cylinder)
% Fit parameters are depth of bottom, area
% Use max fit error as criteria
function gmdl=geminifit(vol,heights,x0)
plot(vol,heights,'k');
xlabel('Volume (ul)');
ylabel('Height above ZMax (mm)');
if nargin<3
  x0=[26.35,pi*4.062^2,-8.6];
end
gmdl0=struct('depth',x0(1),'area',x0(2),'hoffset',x0(3));
hold on;
options=optimset('Display','notify','TolFun',1e-8,'TolX',1e-8);
fit=fminsearch(@(x) sum((gemcalcvol(heights,struct('depth',x(1),'area',x(2),'hoffset',x(3)))-vol).^2),x0,options);
gmdl=struct('depth',fit(1),'area',fit(2),'hoffset',fit(3));
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
plot(gemcalcvol(heights,gmdl),heights,'g','LineWidth',2);
plot(vol,gemcalcheight(vol,gmdl),'g','LineWidth',2);
plot(gemcalcvol(heights,gmdl0),heights,'m','LineWidth',2);
legend({'Desired','Fit','Fit','Initial'},'Location','NorthWest');
