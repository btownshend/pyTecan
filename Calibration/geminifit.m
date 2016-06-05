% Build model to vol, height data using Gemini built-in structure (simple cone+cylinder)
% Fit parameters are depth of bottom, area
% Use max fit error as criteria
function fit=geminifit(vol,heights,x0)
plot(vol,heights,'k');
xlabel('Volume (ul)');
ylabel('Height above ZMax (mm)');
if nargin<3
  x0=[2,16];
end

hold on;
options=optimset('Display','notify','TolFun',1e-8,'TolX',1e-8);
fit=fminsearch(@(x) max(abs(gemcalcheight(vol,x(1),x(2))-heights)),x0,options);
hest=gemcalcheight(vol,fit(1),fit(2));
rmse=sqrt(nanmean((heights-hest).^2));
maxerr=[min(heights-hest),max(heights-hest)];
vest=gemcalcvol(heights,fit(1),fit(2));
vrmse=sqrt(nanmean((vol-vest).^2));
vmaxerr=[min(vol-vest),max(vol-vest)];
vmaxfrac=max(abs((vol-vest)./vol));
fprintf('Gemini fit:  depth=%.2f mm, area=%.2f mm^2, r=%.2fmm\n', fit,sqrt(fit(2)/pi));
fprintf('Height RMSE = %.2f mm, max = %.2f:%.2f mm\n', rmse,maxerr);
fprintf('Volume RMSE = %.2f ul, max = %.2f:%.2f ul (%.0f%%)\n', vrmse,vmaxerr,vmaxfrac*100);
plot(gemcalcvol(heights,fit(1),fit(2)),heights,'g','LineWidth',2);
plot(vol,gemcalcheight(vol,fit(1),fit(2)),'g','LineWidth',2);
if nargin>=3
  plot(gemcalcvol(heights,x0(1),x0(2)),heights,'m','LineWidth',2);
  legend({'Desired','Fit','Fit','Initial'},'Location','NorthWest');
else
  legend({'Desired','Fit','Fit'},'Location','NorthWest');
end
