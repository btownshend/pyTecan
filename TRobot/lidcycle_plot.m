% Plot lid cycle data
file='lidcycle.log';
fd=fopen(file,'r');
data=[];
while true
  line=fgetl(fd);
  if line==-1
    break;
  end
  sp=parseline(line);
  if length(sp)==5 
    d=struct('t1',str2num(sp{1}),'stat',sp(2),'op',strtrim(sp(3)),'ok',0,'retries',nan,'emsg',sp(end-1),'t2',str2num(sp{end}));
    data=[data,d];
  elseif length(sp)==6 && strcmp(sp(4),'ok')
    d=struct('t1',str2num(sp{1}),'stat',sp(2),'op',strtrim(sp(3)),'ok',1,'retries',sp(4),'emsg','','t2',str2num(sp{end}));
    data=[data,d];
  else
    fprintf('Bad line with %d fields: "%s"\n',length(sp),line);
  end
end
keep=arrayfun(@(z) ~isempty(z.t1) & ~isempty(z.t2),data);
data=data(keep);
t1=data(1).t1;
for i=1:length(data)
  data(i).t1=(data(i).t1-t1)/60;
  data(i).t2=(data(i).t2-t1)/60;
end
fprintf('%d good lines\n',length(data));
setfig('status');clf;
t1=[data.t1];
ok=[data.ok];
i=1;
while i<length(t1)
  if t1(i+1)-t1(i)>2
    % Gap 
    t1=[t1(1:i),t1(i:end)];
    ok=[ok(1:i),nan,ok(i+1:end)];
    i=i+2;
  else
    i=i+1;
  end
end
stairs(t1,ok*0.95+0.025);
hold on;
isopen=strcmp({data.op},'open');
h1=plot([data(~isopen).t1],[data(~isopen).ok]*0.95+0.025,'.r');
h2=plot([data(isopen).t1],[data(isopen).ok]*0.95+0.025,'.b');
xlabel('Time (min)');
ylabel('OK?');
legend([h1,h2],{'Close','Open'},'location','east');

% Split at , except inside quotes
function sp=parseline(line)
sp={''};
inquote=false;
for i=1:length(line)
  if line(i)==''''
    inquote=~inquote;
    continue;
  end
  if ~inquote && line(i)==','
    sp{end+1}='';
  else
    sp{end}(end+1)=line(i);
  end
end
end

    