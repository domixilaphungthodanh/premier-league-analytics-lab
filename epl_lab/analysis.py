"""One row per team-match; SQL and independently expanded pandas must agree."""
import calendar
from datetime import date
import pandas as pd
from .db import connect,day
STATS=['shots','target','corners','yellow','red']
def team_cte():
    return """WITH team_matches AS (
    SELECT m.match_id,m.played_on,m.kickoff_time,m.home_team_id team_id,m.away_team_id opponent_id,'home' venue,
      m.home_goals gf,m.away_goals ga,CASE m.result WHEN 'H' THEN 3 WHEN 'D' THEN 1 ELSE 0 END points,
      CASE m.result WHEN 'H' THEN 'W' WHEN 'D' THEN 'D' ELSE 'L' END outcome,"""+','.join('m.home_'+s+' '+s for s in STATS)+"""
    FROM matches m WHERE played_on<=:as_of
    UNION ALL
    SELECT m.match_id,m.played_on,m.kickoff_time,m.away_team_id,m.home_team_id,'away',m.away_goals,m.home_goals,
      CASE m.result WHEN 'A' THEN 3 WHEN 'D' THEN 1 ELSE 0 END,
      CASE m.result WHEN 'A' THEN 'W' WHEN 'D' THEN 'D' ELSE 'L' END,"""+','.join('m.away_'+s for s in STATS)+"""
    FROM matches m WHERE played_on<=:as_of)
    """
def scope(db,as_of=None):
    with connect(db) as c:latest=c.execute('SELECT MAX(played_on) FROM matches').fetchone()[0]
    return day(as_of or latest or date.today().isoformat())
def quality(db):
    with connect(db) as c:
        if c.execute('PRAGMA integrity_check').fetchone()[0]!='ok' or c.execute('PRAGMA foreign_key_check').fetchall():raise ValueError('Database không toàn vẹn')
        rows=pd.read_sql_query('SELECT * FROM matches',c);teams=pd.read_sql_query('SELECT * FROM teams',c)
        if len(rows)!=380 or len(teams)!=20:raise ValueError('Database phải có đủ toàn mùa 380 trận/20 đội')
        if rows.duplicated(['home_team_id','away_team_id']).any() or (rows.home_team_id==rows.away_team_id).any():raise ValueError('Trùng cặp trận/đội tự đấu')
        for key in ['home_team_id','away_team_id']:
            counts=rows.groupby(key).size()
            if len(counts)!=20 or not counts.eq(19).all():raise ValueError('Mỗi đội cần 19 trận mỗi sân')
        for r in rows.itertuples():
            day(r.played_on)
            if not '2025-08-01'<=r.played_on<='2026-05-31':raise ValueError('Ngày ngoài mùa')
            expected='H' if r.home_goals>r.away_goals else 'A' if r.home_goals<r.away_goals else 'D'
            if r.result!=expected:raise ValueError('Tỷ số không khớp kết quả')
        source=c.execute('SELECT * FROM source_files').fetchall()
        from .download import SHA256
        if len(source)!=1 or source[0][2]!=SHA256:raise ValueError('Nguồn không đúng snapshot đã chốt')
    missing=int(rows[['home_'+s for s in STATS]+['away_'+s for s in STATS]].isna().sum().sum())
    checks=[{'check':'matches','value':380},{'check':'teams','value':20},{'check':'duplicate_pair','value':0},{'check':'optional_stat_missing_cells','value':missing},{'check':'foreign_key_errors','value':0}]
    from .possession import available,manifest
    with connect(db) as c:
        if available(c):
            records=c.execute('SELECT status,COUNT(*) FROM match_possession GROUP BY status').fetchall()
            if sum(n for _,n in records)!=380:raise ValueError('Bổ sung kiểm soát bóng phải đối chiếu đủ 380 trận')
            expected={(e['file_name'],e['url'],e['sha256'],manifest()['commit']) for e in manifest()['files']}
            actual=set(c.execute('SELECT file_name,url,sha256,source_commit FROM possession_sources').fetchall())
            if expected!=actual:raise ValueError('Nguồn kiểm soát bóng không khớp snapshot')
            checks.extend({'check':'possession_'+status+'_matches','value':count} for status,count in records)
        else:checks.append({'check':'possession_not_loaded','value':1})
    return pd.DataFrame(checks)
def queries(db,as_of=None):
    as_of=scope(db,as_of);p={'as_of':as_of};cte=team_cte()
    with connect(db) as c:
        table=pd.read_sql_query(cte+""", totals AS (
        SELECT t.team_id,t.name,COUNT(x.match_id) played,
        COALESCE(SUM(x.outcome='W'),0) won,COALESCE(SUM(x.outcome='D'),0) drawn,COALESCE(SUM(x.outcome='L'),0) lost,
        COALESCE(SUM(x.gf),0) gf,COALESCE(SUM(x.ga),0) ga,COALESCE(SUM(x.gf-x.ga),0) gd,COALESCE(SUM(x.points),0) points
        FROM teams t LEFT JOIN team_matches x USING(team_id) GROUP BY t.team_id,t.name)
        SELECT RANK() OVER(ORDER BY points DESC,gd DESC,gf DESC) rank,* FROM totals ORDER BY rank,name""",c,params=p)
        tm=pd.read_sql_query(cte+"""SELECT x.*,t.name,o.name opponent FROM team_matches x JOIN teams t USING(team_id)
        JOIN teams o ON o.team_id=x.opponent_id ORDER BY team_id,played_on,kickoff_time,match_id""",c,params=p)
        venue=pd.read_sql_query(cte+"""SELECT t.name,x.venue,COUNT(*) played,SUM(points) points,SUM(gf) gf,SUM(ga) ga
        FROM team_matches x JOIN teams t USING(team_id) GROUP BY t.name,x.venue ORDER BY t.name,x.venue""",c,params=p)
        form=pd.read_sql_query(cte+""", numbered AS (SELECT *,ROW_NUMBER() OVER(PARTITION BY team_id ORDER BY played_on DESC,kickoff_time DESC,match_id DESC) rn FROM team_matches)
        SELECT t.name,COUNT(*) recent_played,SUM(points) last5_points,SUM(gf) gf,SUM(ga) ga
        FROM numbered JOIN teams t USING(team_id) WHERE rn<=5 GROUP BY t.name ORDER BY last5_points DESC,t.name""",c,params=p)
        monthly=pd.read_sql_query("""SELECT substr(played_on,1,7) month,COUNT(*) matches,SUM(home_goals+away_goals) goals FROM matches WHERE played_on<=:as_of GROUP BY month ORDER BY month""",c,params=p)
    months=pd.DataFrame({'month':pd.period_range('2025-08','2026-05',freq='M').astype(str)})
    monthly=months.merge(monthly,on='month',how='left')
    for col in ['matches','goals']:
        monthly[col]=monthly[col].astype('Int64')
        monthly.loc[monthly.month<=as_of[:7],col]=monthly.loc[monthly.month<=as_of[:7],col].fillna(0)
    from .possession import enrich_sql
    return enrich_sql(db,{'standings':table,'team_matches':tm,'home_away':venue,'last5_form':form,'monthly':monthly},as_of)
def pandas_tables(db,as_of):
    # Reads only original source tables, not SQL aggregates or team-match view.
    with connect(db) as c:
        m=pd.read_sql_query('SELECT * FROM matches',c);t=pd.read_sql_query('SELECT * FROM teams',c)
    m=m[m.played_on<=as_of];expanded=[]
    for r in m.to_dict('records'):
        for side,other,venue in [('home','away','home'),('away','home','away')]:
            gf,ga=r[side+'_goals'],r[other+'_goals'];pts=3 if gf>ga else 1 if gf==ga else 0
            expanded.append(dict(match_id=r['match_id'],played_on=r['played_on'],kickoff_time=r['kickoff_time'],team_id=r[side+'_team_id'],opponent_id=r[other+'_team_id'],venue=venue,gf=gf,ga=ga,points=pts,outcome='W' if pts==3 else 'D' if pts==1 else 'L',**{s:r[side+'_'+s] for s in STATS}))
    cols=['match_id','played_on','kickoff_time','team_id','opponent_id','venue','gf','ga','points','outcome',*STATS]
    x=pd.DataFrame(expanded,columns=cols)
    x=x.merge(t,on='team_id').merge(t.rename(columns={'team_id':'opponent_id','name':'opponent'}),on='opponent_id').sort_values(['team_id','played_on','kickoff_time','match_id'])
    standings=[]
    for team in t.itertuples():
        z=x[x.team_id==team.team_id];gf=int(z.gf.sum());ga=int(z.ga.sum())
        standings.append(dict(team_id=team.team_id,name=team.name,played=len(z),won=int(z.outcome.eq('W').sum()),drawn=int(z.outcome.eq('D').sum()),lost=int(z.outcome.eq('L').sum()),gf=gf,ga=ga,gd=gf-ga,points=int(z.points.sum())))
    table=pd.DataFrame(standings).sort_values(['points','gd','gf','name'],ascending=[False,False,False,True])
    keys=[tuple(r) for r in table[['points','gd','gf']].to_numpy()];ranks=[keys.index(k)+1 for k in keys];table.insert(0,'rank',ranks)
    venue=x.groupby(['name','venue']).agg(played=('match_id','size'),points=('points','sum'),gf=('gf','sum'),ga=('ga','sum')).reset_index()
    recent=x.sort_values(['played_on','kickoff_time','match_id']).groupby('team_id').tail(5)
    form=recent.groupby('name').agg(recent_played=('match_id','size'),last5_points=('points','sum'),gf=('gf','sum'),ga=('ga','sum')).reset_index().sort_values(['last5_points','name'],ascending=[False,True])
    monthly=pd.DataFrame({'month':pd.period_range('2025-08','2026-05',freq='M').astype(str)})
    agg=m.assign(month=m.played_on.str[:7],goals=m.home_goals+m.away_goals).groupby('month').agg(matches=('match_id','size'),goals=('goals','sum')).reset_index()
    monthly=monthly.merge(agg,on='month',how='left')
    for col in ['matches','goals']:
        monthly[col]=monthly[col].astype('Int64');monthly.loc[monthly.month<=as_of[:7],col]=monthly.loc[monthly.month<=as_of[:7],col].fillna(0)
    from .possession import enrich_pandas
    return enrich_pandas(db,{'standings':table,'team_matches':x[cols+['name','opponent']],'home_away':venue,'last5_form':form,'monthly':monthly},as_of)
def reconcile(db,as_of=None):
    quality(db);as_of=scope(db,as_of);sql=queries(db,as_of);other=pandas_tables(db,as_of)
    for name in sql:
        a=sql[name].reset_index(drop=True);b=other[name][a.columns].reset_index(drop=True)
        # Integer counts remain exact; percentages allow floating arithmetic noise only.
        numeric_ratios=[col for col in a if col in ('avg_possession_pct','possession_pct')]
        pd.testing.assert_frame_equal(a.drop(columns=numeric_ratios),b.drop(columns=numeric_ratios),check_dtype=False,check_exact=True)
        if numeric_ratios:pd.testing.assert_frame_equal(a[numeric_ratios].astype('float64'),b[numeric_ratios].astype('float64'),check_dtype=False,check_exact=False,rtol=0,atol=1e-10)
    if int(sql['standings'].gf.sum())!=int(sql['standings'].ga.sum()):raise ValueError('Tổng bàn thắng/thua lệch')
    return sql
