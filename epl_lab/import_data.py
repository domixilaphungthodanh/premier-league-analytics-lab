import argparse,csv,io,os,tempfile,json
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path
from .db import ROOT,DEFAULT_DB,connect
from .download import CSV,URL,SHA256,verify
STAT_MAP={'HS':'home_shots','AS':'away_shots','HST':'home_target','AST':'away_target','HC':'home_corners','AC':'away_corners','HY':'home_yellow','AY':'away_yellow','HR':'home_red','AR':'away_red'}
REQUIRED=['Div','Date','Time','HomeTeam','AwayTeam','FTHG','FTAG','FTR',*STAT_MAP]
def integer(value,field,line,optional=False):
    if optional and value=='':return None
    if not value.isascii() or not value.isdigit():raise ValueError(f'Dòng {line}: {field} phải là số nguyên không âm')
    return int(value)
def parse(data,complete=True):
    reader=csv.DictReader(io.StringIO(data.decode('utf-8-sig'),newline=''),strict=True)
    if not reader.fieldnames or len(set(reader.fieldnames))!=len(reader.fieldnames) or not set(REQUIRED)<=set(reader.fieldnames):raise ValueError('Thiếu cột hoặc tên cột trùng')
    rows=[];seen=set();home=Counter();away=Counter()
    for line,row in enumerate(reader,2):
        if None in row or any(v is None for v in row.values()):raise ValueError(f'Dòng {line}: CSV sai số cột')
        h,a=row['HomeTeam'].strip(),row['AwayTeam'].strip()
        if not h or not a or h==a:raise ValueError(f'Dòng {line}: đội không hợp lệ')
        if (h,a) in seen:raise ValueError(f'Dòng {line}: trùng cặp sân nhà–sân khách')
        seen.add((h,a));home[h]+=1;away[a]+=1
        dt=datetime.strptime(row['Date'],'%d/%m/%Y').date()
        if row['Div']!='E0' or not '2025-08-01'<=dt.isoformat()<='2026-05-31':raise ValueError(f'Dòng {line}: ngoài giải/mùa đã chọn')
        tm=datetime.strptime(row['Time'],'%H:%M').strftime('%H:%M')
        hg=integer(row['FTHG'],'FTHG',line);ag=integer(row['FTAG'],'FTAG',line)
        result='H' if hg>ag else 'A' if hg<ag else 'D'
        if row['FTR']!=result:raise ValueError(f'Dòng {line}: FTR khác tỷ số')
        item={'source_row':line,'played_on':dt.isoformat(),'kickoff_time':tm,'home':h,'away':a,'home_goals':hg,'away_goals':ag,'result':result}
        for source,dest in STAT_MAP.items():item[dest]=integer(row[source],source,line,True)
        for side in ['home','away']:
            if item[side+'_target'] is not None and item[side+'_shots'] is not None and item[side+'_target']>item[side+'_shots']:raise ValueError(f'Dòng {line}: sút trúng đích lớn hơn tổng sút')
        rows.append(item)
    names=sorted(set(home)|set(away))
    if complete and (len(rows)!=380 or len(names)!=20 or any(home[n]!=19 or away[n]!=19 for n in names)):raise ValueError('Chưa đủ toàn mùa: cần 380 trận, 20 đội, mỗi đội 19 sân nhà + 19 sân khách')
    return rows,names
def import_data(source=CSV,db=DEFAULT_DB):
    db=Path(db)
    if db.exists():raise FileExistsError('Database đã tồn tại; dùng --db khác, không ghi đè.')
    data=verify(source);rows,names=parse(data)
    db.parent.mkdir(parents=True,exist_ok=True);fd,tmp=tempfile.mkstemp(dir=db.parent,suffix='.sqlite.tmp');os.close(fd)
    try:
        with connect(tmp,False) as c:
            c.executescript((ROOT/'sql/schema.sql').read_text(encoding='utf-8'))
            c.execute('INSERT INTO source_files VALUES(1,?,?,?,?)',(URL,SHA256,datetime.now(timezone.utc).isoformat(),len(data)))
            ids={name:i for i,name in enumerate(names,1)}
            c.executemany('INSERT INTO teams VALUES(?,?)',[(i,n) for n,i in ids.items()])
            cols=['source_row','played_on','kickoff_time','home_team_id','away_team_id','home_goals','away_goals','result',*STAT_MAP.values()]
            for row in rows:
                row['home_team_id']=ids[row.pop('home')];row['away_team_id']=ids[row.pop('away')]
                c.execute('INSERT INTO matches(source_id,'+','.join(cols)+') VALUES(1,'+','.join('?' for _ in cols)+')',[row[x] for x in cols])
            c.executemany('INSERT INTO metadata VALUES(?,?)',[('season','2025-2026'),('data_kind','real'),('source_sha256',SHA256),('date_semantics','Source local match date; as-of is inclusive end of date, not intraday live state')])
        c.close()
        from .analysis import quality
        quality(tmp)
        os.link(tmp,db)
    finally:Path(tmp).unlink(missing_ok=True)
    return db
def main():
    p=argparse.ArgumentParser();p.add_argument('--input',default=str(CSV));p.add_argument('--db',default=str(DEFAULT_DB));a=p.parse_args()
    try:print(import_data(a.input,a.db))
    except (ValueError,OSError,csv.Error) as e:p.exit(1,str(e)+'\n')
if __name__=='__main__':main()
