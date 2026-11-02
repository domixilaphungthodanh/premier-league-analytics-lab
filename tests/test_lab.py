"""Small SYNTHETIC fixtures only. These are never substituted for real season data."""
import csv,io,sqlite3,tempfile,unittest,hashlib
from pathlib import Path
from unittest.mock import patch
import pandas as pd
from epl_lab.db import ROOT,connect,day
from epl_lab.import_data import parse,REQUIRED,STAT_MAP
from epl_lab.analysis import queries,pandas_tables,reconcile,quality
from epl_lab.download import verify,SHA256
def csv_bytes(changes=None):
    d=dict.fromkeys(REQUIRED,'0');d.update(Div='E0',Date='15/08/2025',Time='20:00',HomeTeam='Alpha',AwayTeam='Beta',FTHG='2',FTAG='1',FTR='H',HS='10',AS='8',HST='4',AST='2')
    d.update(changes or {});s=io.StringIO(newline='');w=csv.DictWriter(s,fieldnames=REQUIRED);w.writeheader();w.writerow(d);return s.getvalue().encode()
class ParserTests(unittest.TestCase):
    def test_small_fixture_explicitly_incomplete(self):
        r,n=parse(csv_bytes(),False);self.assertEqual(r[0]['home_goals'],2);self.assertEqual(n,['Alpha','Beta'])
    def test_incomplete_season_rejected(self):
        with self.assertRaises(ValueError):parse(csv_bytes())
    def test_wrong_result(self):
        with self.assertRaises(ValueError):parse(csv_bytes({'FTR':'A'}),False)
    def test_negative_goals(self):
        with self.assertRaises(ValueError):parse(csv_bytes({'FTHG':'-1'}),False)
    def test_same_team(self):
        with self.assertRaises(ValueError):parse(csv_bytes({'AwayTeam':'Alpha'}),False)
    def test_wrong_division(self):
        with self.assertRaises(ValueError):parse(csv_bytes({'Div':'E1'}),False)
    def test_wrong_season(self):
        with self.assertRaises(ValueError):parse(csv_bytes({'Date':'01/01/2024'}),False)
    def test_target_above_shots(self):
        with self.assertRaises(ValueError):parse(csv_bytes({'HST':'11'}),False)
    def test_optional_missing_is_null(self):self.assertIsNone(parse(csv_bytes({'HS':''}),False)[0][0]['home_shots'])
    def test_missing_column(self):
        with self.assertRaises(ValueError):parse(b'Div,Date\nE0,15/08/2025\n',False)
    def test_duplicate_fixture(self):
        data=csv_bytes();data+=data.splitlines(keepends=True)[1]
        with self.assertRaises(ValueError):parse(data,False)
    def test_hash_mismatch(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'fixture.csv';p.write_bytes(csv_bytes())
            with self.assertRaises(ValueError):verify(p)
    def test_strict_date(self):
        for d in ['2025-2-1','2025-02-30','bad']:
            with self.assertRaises(ValueError):day(d)
    def test_full_double_round_robin_completeness(self):
        base=list(csv.DictReader(io.StringIO(csv_bytes().decode())))[0]
        s=io.StringIO(newline='');w=csv.DictWriter(s,fieldnames=REQUIRED);w.writeheader()
        for h in range(20):
            for a in range(20):
                if h!=a:w.writerow(dict(base,HomeTeam=f'Fixture{h}',AwayTeam=f'Fixture{a}'))
        rows,names=parse(s.getvalue().encode());self.assertEqual(len(rows),380);self.assertEqual(len(names),20)
        with self.assertRaises(ValueError):parse(('\n'.join(s.getvalue().splitlines()[:-1])+'\n').encode())
class AnalysisTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.db=Path(self.tmp.name)/'fixture.db'
        with connect(self.db,False) as c:
            c.executescript((ROOT/'sql/schema.sql').read_text(encoding='utf-8'))
            c.execute("INSERT INTO source_files VALUES(1,'SYNTHETIC FIXTURE','not-real','2026-01-01',1)")
            c.executemany('INSERT INTO teams VALUES(?,?)',[(1,'Alpha'),(2,'Beta'),(3,'Gamma')])
            # Alpha earns W,D,L before/after cutoffs. Gamma is catalog-only.
            c.executemany("INSERT INTO matches(source_id,source_row,played_on,kickoff_time,home_team_id,away_team_id,home_goals,away_goals,result,home_shots,away_shots) VALUES(1,?,?,'20:00',?,?,?,?,?,?,?)",[(2,'2025-08-15',1,2,2,1,'H',10,8),(3,'2025-08-20',2,1,0,0,'D',9,7)])
    def tearDown(self):self.tmp.cleanup()
    def test_join_no_multiply(self):self.assertEqual(len(queries(self.db)['team_matches']),4)
    def test_points_goals(self):
        s=queries(self.db)['standings'].set_index('name');self.assertEqual(s.loc['Alpha','points'],4);self.assertEqual(s.loc['Beta','points'],1);self.assertEqual(s.gf.sum(),s.ga.sum())
    def test_home_away(self):
        v=queries(self.db)['home_away'].set_index(['name','venue']);self.assertEqual(v.loc[('Alpha','home'),'points'],3);self.assertEqual(v.loc[('Alpha','away'),'points'],1)
    def test_historical_scope(self):
        s=queries(self.db,'2025-08-15')['standings'];self.assertEqual(s.played.sum(),2)
    def test_no_future_match(self):self.assertEqual(len(queries(self.db,'2025-08-14')['team_matches']),0)
    def test_all_teams_preserved(self):self.assertEqual(len(queries(self.db,'2025-08-01')['standings']),3)
    def test_ties_keep_same_rank(self):self.assertEqual(queries(self.db,'2025-08-01')['standings']['rank'].tolist(),[1,1,1])
    def test_no_matches_months_are_zero_future_null(self):
        t=queries(self.db,'2025-09-01')['monthly'].set_index('month');self.assertEqual(t.loc['2025-09','matches'],0);self.assertTrue(pd.isna(t.loc['2025-10','matches']))
    def test_last5_sample_size(self):self.assertEqual(queries(self.db)['last5_form'].recent_played.tolist(),[2,2])
    def test_last5_excludes_earlier_matches(self):
        with connect(self.db,False) as c:
            c.executemany('INSERT INTO teams VALUES(?,?)',[(i,f'Fixture{i}') for i in range(4,8)])
            for i in range(3,8):
                c.execute("INSERT INTO matches(source_id,source_row,played_on,kickoff_time,home_team_id,away_team_id,home_goals,away_goals,result) VALUES(1,?,?,'20:00',1,?,1,0,'H')",(i+10,f'2025-09-0{i-2}',i))
        f=queries(self.db)['last5_form'].set_index('name').loc['Alpha'];self.assertEqual(f.recent_played,5);self.assertEqual(f.last5_points,15)
    def test_pandas_matches_sql(self):
        with patch('epl_lab.analysis.quality'):reconcile(self.db)
    def test_empty_pandas_matches_sql(self):
        with patch('epl_lab.analysis.quality'):reconcile(self.db,'2025-08-01')
    def test_quality_rejects_incomplete(self):
        with self.assertRaises(ValueError):quality(self.db)
    def test_readonly(self):
        with connect(self.db) as c:
            with self.assertRaises(sqlite3.OperationalError):c.execute("INSERT INTO teams VALUES(4,'Delta')")
    def test_foreign_keys(self):
        with connect(self.db,False) as c:
            self.assertEqual(c.execute('PRAGMA foreign_keys').fetchone()[0],1)
            with self.assertRaises(sqlite3.IntegrityError):c.execute("UPDATE matches SET home_team_id=99 WHERE match_id=1")
    def test_snapshot_stats_null(self):
        x=queries(self.db)['team_matches'];self.assertTrue(x.target.isna().all())
    def test_existing_db_not_overwritten(self):
        from epl_lab.import_data import import_data
        before=self.db.read_bytes()
        with self.assertRaises(FileExistsError):import_data('missing.csv',self.db)
        self.assertEqual(before,self.db.read_bytes())
    def test_failed_import_no_published_file(self):
        from epl_lab.import_data import import_data
        dest=Path(self.tmp.name)/'bad.db'
        with patch('epl_lab.import_data.verify',return_value=csv_bytes()):
            with self.assertRaises(ValueError):import_data('unused',dest)
        self.assertFalse(dest.exists())
    def test_empty_report_still_exports(self):
        from epl_lab.analyze import analyze
        with patch('epl_lab.analysis.quality'),patch('epl_lab.analyze.quality',return_value=pd.DataFrame([{'check':'fixture','value':1}])):
            out=analyze(self.db,'2025-08-01',Path(self.tmp.name)/'out')
        self.assertEqual(len(list(out.glob('*.png'))),4);self.assertEqual(len(list(out.glob('*.csv'))),6)
if __name__=='__main__':unittest.main()
