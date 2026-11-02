"""Optional, versioned match possession. Never infer missing values or repair scores."""
import argparse
import csv
import hashlib
import io
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import pandas as pd
import requests

from .db import ROOT, DEFAULT_DB, connect

MANIFEST=ROOT/'docs/possession_source.json'
ALIASES={'Man Utd':'Man United','Spurs':'Tottenham'}
DDL="""
CREATE TABLE IF NOT EXISTS possession_sources(
 file_name TEXT PRIMARY KEY,url TEXT NOT NULL,sha256 TEXT NOT NULL,
 source_commit TEXT NOT NULL,imported_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS match_possession(
 match_id INTEGER PRIMARY KEY REFERENCES matches,
 source_file TEXT NOT NULL REFERENCES possession_sources(file_name),
 source_row INTEGER NOT NULL,source_match_id TEXT NOT NULL UNIQUE,
 home_bp INTEGER CHECK(home_bp BETWEEN 0 AND 10000),
 away_bp INTEGER CHECK(away_bp BETWEEN 0 AND 10000),
 status TEXT NOT NULL CHECK(status IN ('valid','score_conflict','missing')),
 reason TEXT NOT NULL,
 CHECK((status='valid' AND home_bp IS NOT NULL AND away_bp IS NOT NULL AND home_bp+away_bp=10000)
 OR (status<>'valid' AND home_bp IS NULL AND away_bp IS NULL)));
"""

def manifest():return json.loads(MANIFEST.read_text(encoding='utf-8'))

def fetch_sources(cache=None):
    spec=manifest();cache=Path(cache or ROOT/'data/raw/possession');cache.mkdir(parents=True,exist_ok=True)
    def fetch(entry):
        p=cache/entry['file_name']
        if p.exists():data=p.read_bytes()
        else:
            response=requests.get(entry['url'],timeout=(15,60));response.raise_for_status();data=response.content
        if hashlib.sha256(data).hexdigest()!=entry['sha256']:raise ValueError('Nguồn kiểm soát bóng khác SHA256: '+entry['file_name'])
        if not p.exists():p.write_bytes(data)
        return entry['file_name'],data
    with ThreadPoolExecutor(max_workers=6) as pool:return dict(pool.map(fetch,spec['files']))

def whole(value):
    d=Decimal(value)
    if not d.is_finite() or d!=d.to_integral_value():raise ValueError('Mã đội/tỷ số phải nguyên')
    return int(d)

def basis_points(value):
    d=Decimal(value)
    if not d.is_finite() or not Decimal(0)<=d<=Decimal(100) or d*100!=(d*100).to_integral_value():raise ValueError('Kiểm soát bóng phải nằm 0–100%, tối đa hai số lẻ')
    return int(d*100)

def parse_sources(files,matches):
    teams={whole(r['code']):ALIASES.get(r['name'],r['name']) for r in csv.DictReader(io.StringIO(files['teams.csv'].decode('utf-8-sig')))}
    rows=[];seen=set()
    for name,data in sorted(files.items()):
        if name=='teams.csv':continue
        reader=csv.DictReader(io.StringIO(data.decode('utf-8-sig')),strict=True)
        required={'home_team','away_team','kickoff_time','home_score','away_score','finished','home_possession','away_possession','match_id'}
        if not required<=set(reader.fieldnames or []):raise ValueError('Thiếu cột: '+name)
        for line,r in enumerate(reader,2):
            if None in r or any(v is None for v in r.values()):raise ValueError(f'{name}:{line}: CSV sai cấu trúc')
            key=(teams[whole(r['home_team'])],teams[whole(r['away_team'])])
            if key in seen or key not in matches:raise ValueError(f'{name}:{line}: trùng hoặc không ghép được trận {key}')
            seen.add(key);m=matches[key]
            kick=datetime.fromisoformat(r['kickoff_time'])
            if kick.tzinfo is None or kick.date().isoformat()!=m['played_on']:raise ValueError(f'{name}:{line}: khác ngày trận')
            status='valid';reason='';hp=ap=None
            if r['finished'].casefold()!='true' or whole(r['home_score'])!=m['home_goals'] or whole(r['away_score'])!=m['away_goals']:
                status='score_conflict';reason=f"Nguồn phụ {r['home_score']}–{r['away_score']}; nguồn chính {m['home_goals']}–{m['away_goals']}. Không dùng vào trung bình."
            elif not r['home_possession'] or not r['away_possession']:
                status='missing';reason='Thiếu kiểm soát bóng; không thay bằng 0.'
            else:
                hp=basis_points(r['home_possession']);ap=basis_points(r['away_possession'])
                if hp+ap!=10000:raise ValueError(f'{name}:{line}: hai phía không cộng thành 100%')
            rows.append((m['match_id'],name,line,r['match_id'],hp,ap,status,reason))
    if seen!=set(matches):raise ValueError('Nguồn phụ chưa phủ đủ các trận của nguồn chính')
    return rows

def install(db=DEFAULT_DB,cache=None):
    spec=manifest();files=fetch_sources(cache)
    with connect(db) as c:
        original=pd.read_sql_query('SELECT m.*,h.name home,a.name away FROM matches m JOIN teams h ON h.team_id=m.home_team_id JOIN teams a ON a.team_id=m.away_team_id',c)
    rows=parse_sources(files,{(r['home'],r['away']):r for r in original.to_dict('records')})
    if len(rows)!=380:raise ValueError('Cần đối chiếu đủ 380 trận')
    with connect(db,False) as c:
        # BEGIN inside executescript: schema and all rows share a single transaction.
        c.executescript('BEGIN IMMEDIATE;'+DDL)
        existing=c.execute('SELECT DISTINCT source_commit FROM possession_sources').fetchall()
        if existing and existing!=[(spec['commit'],)]:raise ValueError('Đã có snapshot khác; không tự thay dữ liệu')
        for e in spec['files']:
            c.execute('INSERT OR IGNORE INTO possession_sources VALUES(?,?,?,?,?)',(e['file_name'],e['url'],e['sha256'],spec['commit'],datetime.now(timezone.utc).isoformat()))
        for row in rows:
            old=c.execute('SELECT * FROM match_possession WHERE match_id=?',(row[0],)).fetchone()
            if old is not None and tuple(old)!=row:raise ValueError('Dữ liệu đã nhập khác snapshot; không ghi đè')
            if old is None:c.execute('INSERT INTO match_possession VALUES(?,?,?,?,?,?,?,?)',row)
    return {'matched':len(rows),'valid':sum(r[6]=='valid' for r in rows),'excluded':sum(r[6]!='valid' for r in rows)}

def available(c):return c.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='match_possession'").fetchone() is not None

def enrich_sql(db,tables,as_of):
    with connect(db) as c:
        if available(c):
            sides=pd.read_sql_query("""SELECT m.match_id,'home' venue,p.home_bp/100.0 possession_pct FROM matches m LEFT JOIN match_possession p ON p.match_id=m.match_id
            UNION ALL SELECT m.match_id,'away',p.away_bp/100.0 FROM matches m LEFT JOIN match_possession p ON p.match_id=m.match_id""",c)
            aggregate=pd.read_sql_query("""WITH sides AS (
             SELECT m.home_team_id team_id,'home' venue,m.played_on,p.home_bp bp FROM matches m LEFT JOIN match_possession p USING(match_id)
             UNION ALL SELECT m.away_team_id,'away',m.played_on,p.away_bp FROM matches m LEFT JOIN match_possession p USING(match_id))
             SELECT t.name,COUNT(s.bp) possession_matches,AVG(s.bp)/100.0 avg_possession_pct
             FROM teams t LEFT JOIN sides s ON t.team_id=s.team_id AND s.played_on<=? GROUP BY t.team_id,t.name ORDER BY t.name""",c,params=(as_of,))
            venue=pd.read_sql_query("""WITH sides AS (
             SELECT m.home_team_id team_id,'home' venue,m.played_on,p.home_bp bp FROM matches m LEFT JOIN match_possession p USING(match_id)
             UNION ALL SELECT m.away_team_id,'away',m.played_on,p.away_bp FROM matches m LEFT JOIN match_possession p USING(match_id))
             SELECT t.name,s.venue,COUNT(s.bp) possession_matches,AVG(s.bp)/100.0 avg_possession_pct
             FROM sides s JOIN teams t USING(team_id) WHERE s.played_on<=? GROUP BY t.name,s.venue""",c,params=(as_of,))
        else:sides=aggregate=venue=None
    return merge_tables(tables,sides,aggregate,venue)

def enrich_pandas(db,tables,as_of):
    with connect(db) as c:
        p=pd.read_sql_query('SELECT match_id,home_bp,away_bp FROM match_possession',c) if available(c) else None
    if p is None:return merge_tables(tables,None,None,None)
    tm=tables['team_matches'];parts=[]
    for v in ['home','away']:
        parts.append(p[['match_id',v+'_bp']].rename(columns={v+'_bp':'bp'}).assign(venue=v))
    side=pd.concat(parts,ignore_index=True);side['possession_pct']=side.bp/100.0
    joined=tm.merge(side[['match_id','venue','possession_pct']],on=['match_id','venue'],how='left')
    aggregate=joined.groupby('name').agg(possession_matches=('possession_pct','count'),avg_possession_pct=('possession_pct','mean')).reset_index()
    # Keep teams without matches in the selected historical period.
    aggregate=tables['standings'][['name']].merge(aggregate,on='name',how='left');aggregate['possession_matches']=aggregate.possession_matches.fillna(0).astype(int)
    venue=joined.groupby(['name','venue']).agg(possession_matches=('possession_pct','count'),avg_possession_pct=('possession_pct','mean')).reset_index()
    return merge_tables(tables,side[['match_id','venue','possession_pct']],aggregate,venue)

def merge_tables(tables,sides,aggregate,venue):
    if sides is None:
        tables['team_matches']['possession_pct']=float('nan')
        for key in ['standings','home_away']:
            tables[key]['possession_matches']=0;tables[key]['avg_possession_pct']=float('nan');tables[key]['possession_missing']=tables[key]['played']
    else:
        tables['team_matches']=tables['team_matches'].merge(sides,on=['match_id','venue'],how='left',validate='one_to_one')
        for key,agg,keys in [('standings',aggregate,['name']),('home_away',venue,['name','venue'])]:
            tables[key]=tables[key].merge(agg,on=keys,how='left',validate='one_to_one')
            tables[key]['possession_missing']=tables[key]['played']-tables[key]['possession_matches']
    return tables

def main():
    p=argparse.ArgumentParser();p.add_argument('--db',default=str(DEFAULT_DB));p.add_argument('--cache');a=p.parse_args()
    try:print(install(a.db,a.cache))
    except (ValueError,OSError,requests.RequestException,KeyError) as e:p.exit(1,str(e)+'\nKhông thay hoặc suy đoán dữ liệu còn thiếu.\n')
if __name__=='__main__':main()
