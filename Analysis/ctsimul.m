% Simulate expected ranges of Ct's
function ctsimul
ctsigma=0.5;
dilSigma=0.1;    % Dilutions can vary by this fraction
rnagain=3;
trueeff=1.95;
mdleff=1.95;
clv=0.50;
n=500;   % Number of trials
normalize=false;

t7=ones(1,n);
t7=dilute(t7,5/3,dilSigma);
t7=dilute(t7,2,dilSigma);	
t7=dilute(t7,5,dilSigma);	
t7dil=dilute(t7,30,dilSigma);
rt=dilute(t7,2,dilSigma);
rt=dilute(rt,5,dilSigma);
rtsave=dilute(rt,3,dilSigma);
lig=[];
for i=1:3
  lig(i,:)=dilute(rt,3,dilSigma);
  lig(i,:)=dilute(lig(i,:),3, dilSigma);
end
rtsave=dilute(rtsave,3,dilSigma);
qpcr=[];
for i=1:5
  qpcr(i,1,:)=dilute(t7dil,2.5,dilSigma);
  qpcr(i,2,:)=dilute(rtsave,2.5,dilSigma);
  for j=1:3
    qpcr(i,j+2,:)=dilute(lig(j,:),2.5,dilSigma);
  end
end
qpcr(1,[1,2,4],:)=0;
qpcr(1,[3,5],:)=qpcr(1,[3,5],:)*(1-clv);
qpcr(2,[1,2,3],:)=0;
qpcr(2,[4,5],:)=qpcr(2,[4,5],:)*clv;
qpcr(3,2:end,:)=qpcr(3,2:end,:)*(1+rnagain/2);
qpcr(4,2:3,:)=qpcr(4,2:3,:)*(1+rnagain/2*(1-clv));
qpcr(4,4:5,:)=qpcr(4,4:5,:)*(1+rnagain/2);
for i=1:5
  for j=1:5
    ct(i,j,:)=-log(qpcr(i,j,:))/log(trueeff)+randn(size(qpcr(i,j,:)))*ctsigma;
  end
end
% ct(i,j,k): i: 1=AX, 2=BX, 3=MX, 4=WX, 5=REF; j: 1=templ, 2=RT, 3=LigA, 4=LigB, 5=LigBoth;  k=iteration
conc=3750*mdleff.^-ct;
conc(:,1,:)=conc(:,1,:)/3;

% Normalize using REF
if normalize
  for i=1:size(conc,1)
    for j=1:size(conc,2)
      for k=1:size(conc,3)
        conc(i,j,k)=conc(i,j,k)/conc(5,j,k);
      end
    end
  end
end

primers={'AX','BX','MX','WX','RF'};
conds={'Templ','RT','LigA','LigB','LigBoth'};
for k=1:size(conc,3)
  fprintf('Sample %d:\n',k);
  for j=1:size(conc,2)
    fprintf('%7.7s ',conds{j});
    for i=1:size(conc,1)
      fprintf('[%s]=%5.2f ', primers{i}, conc(i,j,k));
    end
    if j>=2
      fprintf('MGain=%5.2f ',(conc(3,j,k)-conc(3,1,k))*2/conc(3,1,k));
      fprintf('WGain=%5.2f ',(conc(4,j,k)-conc(4,1,k))*2/conc(4,1,k));
    end
    if j==4
      sepclv(k)=conc(2,4,k)/(conc(2,4,k)+conc(1,3,k));
      fprintf('Clv=%5.2f ',sepclv(k));
    elseif j==5
      jntclv(k)=conc(2,5,k)/(conc(2,5,k)+conc(1,5,k));
      fprintf('Clv=%5.2f ',jntclv(k));
    end
    fprintf('\n');
  end
end
fprintf('Mean separate cleavage computation = %.2f std=%.2f\n', mean(sepclv), std(sepclv));
fprintf('Mean joint    cleavage computation = %.2f std=%.2f\n', mean(jntclv), std(jntclv));


function y=dilute(x,factor,sigma)
s=exp(randn(size(x))*log(1+sigma));
y=x/factor.*s;


