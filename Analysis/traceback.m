% Display chain of operations/dilutions
function traceback(samps,start)
samp=find(strcmp({samps.name},start));
if length(samp)~=1
  error('Unable to find sample %s\n',start);
end
frac=[1];
dest={start};
history={''};
for i=1:length(samps)
  if samp==i
    continue;
  end
  ing=find(strcmp(samps(i).ingredients,start));
  assert(length(ing)<=1);
  if ~isempty(ing) && ~strcmp(samps(i).plate,'qPCR') && ~strcmp(samps(i).plate,'Dilutions')
    fprintf('%30s (%3d) ',samps(i).name,i);
    frac(end+1)=samps(i).volumes(ing)/sum(samps(i).volumes);
    dest{end+1}=samps(i).name;
    history{end+1}=samps(i).history;
    for j=length(frac)-1:-1:1
      if ~isempty(strfind(history{end},[dest{j},'[']))
        fprintf('=%30s/%5.2f ',dest{j},frac(j)/frac(end));
      end
    end
    fprintf('\n');
  end
end

    