% Build model to vol, height data
% wells(:,2)  - position of well A1=(1,1), H12=(12,8)
% tips(:)     - tip number (1-4)
% slopemodel  - 1 to model slope of plate
% flatbottom  - true to assume flat-bottom wells
function [fit,angle,expected]=fitheights2(vol,heights,wells,tips,angle,x0,slopemodel,flatbottom)
sel=isfinite(vol)&isfinite(heights);
vol=vol(sel);
heights=heights(sel);
wells=wells(sel,:);
tips=tips(sel);

if nargin<5
  angle=17.5;
end
if nargin<6 || isempty(x0)
  x0=[2.5,10,10,0,0,0,0,0];
end
if nargin<8
  flatbottom=false;
end

hold on;
hstep=0:max(heights(:));

if flatbottom
  % Can just do a linear fit from height to vol
  b = robustfit(vol,heights);
  fprintf('Flat bottom fit: %.2f %.2f\n', b);
  h1 = b(1);
  r1 = sqrt((1/b(2))/pi);
  v0 = 0;
  angle = 180;
  h0 = h1;
  hbottom = h1;
  fit=[r1,h1,v0,0,0,0,0,0];
else
  %plot(calcvol2(hstep,angle,x0(1),x0(2),x0(3)),hstep,':r','LineWidth',1);
  options=optimset('Display','notify','TolFun',1e-10,'TolX',1e-10,'MaxFunEvals',20000,'MaxIter',20000);
  % Fit with model x=[r1,h1,v0,slopex,slopey,tip2-tip1,tip3-tip1,tip4-tip1]
  if slopemodel
    fit=fminsearch(@(x) sum((calcvol2(heights,wells,tips,angle,x(1),x(2),x(3),x(4),x(5),[0,x(6:8)])-vol).^2),x0,options);
  else
    x0=x0([1:3,6:8]);
    fit=fminsearch(@(x) sum((calcvol2(heights,wells,tips,angle,x(1),x(2),x(3),0,0,[0,x(4:6)])-vol).^2),x0,options);
    fit=[fit(1:3),0,0,fit(4:6)];
  end
  r1=fit(1); h1=fit(2); v0=fit(3);
  % h0 is height of bottom of pointy cone
  h0=h1-r1/tand(angle/2);
  angle=atand(r1/(h1-h0))*2;
  % hbottom is height of bottom of infilled cone (assuming that the bottom is flat)
  hbottom=(v0/(pi/3)/((r1/(h1-h0))^2))^(1/3)+h0;
end
volestimate=calcvol2(heights,wells,tips,angle,fit(1),fit(2),fit(3),fit(4),fit(5),[0,fit(6:8)]);
rmse=sqrt(nanmean((vol-volestimate).^2));

fprintf('fit:  angle=%.1f deg, r1=%.3f mm, h1=%.2f mm, v0=%.1f ul, sx=%.3f mm/well, sy=%.3f mm/well, offsets=[0,%.2f,%.2f,%.2f]\nh0=%.2f mm, hbottom=%.2f\n', angle, fit, h0, hbottom);
fprintf('RMSE = %.2f ul\n', rmse);
fprintf('Volume at zmax-1.0mm = %.1f ul, zmax-1.5m = %.1f ul\n',calcvol2([1.0,1.5],[],[],angle,fit(1),fit(2),fit(3),fit(4),fit(5),[0,fit(6:8)]));
%plot(volestimate,hstep,':k','LineWidth',2);
%legend({'Tip 1','Tip 2','Tip 3','Tip 4','Fit'},'Location','NorthWest');


expected=nan(size(sel));
expected(sel)=volestimate;