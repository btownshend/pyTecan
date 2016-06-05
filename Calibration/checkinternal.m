% Check internal mapping of heights to volume
% Use HSP96xx - use data from a log file where we have both heights (from RPZ commands) and Gemini detected liquid notes

data=[134,1155+35-1072
      129,1180+10-1072
      48,1144+10-1072
      129,1155+35-1072
      112,1173+10-1072
      100,1168+10-1072
      76,1158+10-1072
      34,1135+10-1072
      30,1132+10-1072
      6,1103+10-1072
      ];

setfig('gemcheck');clf;
vol=data(:,1)';
h=repmat(data(:,2),1,4)';
geminifit(vol, h/10,[9.56,24.10]);
