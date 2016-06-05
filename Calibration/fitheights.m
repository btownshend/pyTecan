% Build model to vol, height data
function [fit,angle]=fitheights(vol,heights,angle,x0)
plot(vol,heights,'o');
xlabel('Volume (ul)');
ylabel('Height above ZMax (mm)');
if nargin<3
  angle=17.5;
end
if nargin<4
  x0=[2.5,10,10];
end

hold on;
hstep=0:max(heights(:));
%plot(calcvol(hstep,angle,x0(1),x0(2),x0(3)),hstep,':r','LineWidth',1);
options=optimset('Display','notify','TolFun',1e-8,'TolX',1e-8);
meanheight=nanmean(heights,1);
sel=isfinite(meanheight);
fit=fminsearch(@(x) sum((calcvol(meanheight(sel),angle,x(1),x(2),x(3))-vol(sel)).^2),x0,options);
expected=interp1(calcvol(hstep,angle,fit(1),fit(2),fit(3)),hstep,vol(sel));
rmse=sqrt(nanmean((meanheight(sel)-expected).^2));
r1=fit(1); h1=fit(2); v0=fit(3);
% h0 is height of bottom of pointy cone
h0=h1-r1/tand(angle/2);
angle=atand(r1/(h1-h0))*2;
% hbottom is height of bottom of infilled cone (assuming that the bottom is flat)
hbottom=(v0/(pi/3)/((r1/(h1-h0))^2))^(1/3)+h0;
fprintf('fit:  angle=%.1f deg, r1=%.2f mm, h1=%.2f mm, v0=%.1f ul\nh0=%.1f mm, hbottom=%.1f\n', angle, fit, h0, hbottom);
fprintf('RMSE = %.2f mm\n', rmse);
plot(calcvol(hstep,angle,fit(1),fit(2),fit(3)),hstep,':k','LineWidth',2);
legend({'Tip 1','Tip 2','Tip 3','Tip 4','Fit'},'Location','NorthWest');


