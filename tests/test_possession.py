"""Synthetic possession fixtures, never a substitute for the real 379-match import."""
import csv,io,sqlite3,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import pandas as pd
from epl_lab.db import ROOT,connect
from epl_lab.analysis import queries,reconcile
from epl_lab.possession import DDL,basis_points,parse_sources

def encoded(rows,fields):
    s=io.StringIO();w=csv.DictWriter(s,fieldnames=fields);w.writeheader();w.writerows(rows);return s.getvalue().encode()

class PossessionTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.db=Path(self.tmp.name)/'fixture.db'
        with connect(self.db,False) as c:
            c.executescript((ROOT/'sql/schema.sql').read_text(encoding='utf-8')+DDL)
            c.execute("INSERT INTO source_files VALUES(1,'SYNTHETIC','fixture','2026-01-01',1)")
            c.executemany('INSERT INTO teams VALUES(?,?)',[(1,'Alpha'),(2,'Beta')])
            c.executemany("INSERT INTO matches(source_id,source_row,played_on,kickoff_time,home_team_id,away_team_id,home_goals,away_goals,result) VALUES(1,?,?,'20:00',?,?,1,0,'H')",[(2,'2025-08-15',1,2),(3,'2025-08-20',2,1)])
            c.execute("INSERT INTO possession_sources VALUES('fixture.csv','synthetic','fixture','test','2026-01-01')")
            c.executemany("INSERT INTO match_possession VALUES(?,'fixture.csv',?,?,?,?,'valid','')",[(1,2,'f1',6000,4000),(2,3,'f2',5000,5000)])
    def tearDown(self):self.tmp.cleanup()
    def test_average_equal_match_weights(self):
        t=queries(self.db)['standings'].set_index('name');self.assertEqual(t.loc['Alpha','avg_possession_pct'],55);self.assertEqual(t.loc['Beta','avg_possession_pct'],45)
    def test_coverage_count(self):
        t=queries(self.db)['standings'];self.assertTrue(t.possession_matches.eq(2).all());self.assertTrue(t.possession_missing.eq(0).all())
    def test_home_away(self):
        t=queries(self.db)['home_away'].set_index(['name','venue']);self.assertEqual(t.loc[('Alpha','home'),'avg_possession_pct'],60);self.assertEqual(t.loc[('Alpha','away'),'avg_possession_pct'],50)
    def test_historical_cutoff(self):
        t=queries(self.db,'2025-08-15')['standings'].set_index('name');self.assertEqual(t.loc['Alpha','avg_possession_pct'],60);self.assertEqual(t.loc['Alpha','possession_matches'],1)
    def test_missing_excluded_not_zero(self):
        with connect(self.db,False) as c:c.execute("UPDATE match_possession SET home_bp=NULL,away_bp=NULL,status='missing',reason='fixture' WHERE match_id=2")
        t=queries(self.db)['standings'].set_index('name');self.assertEqual(t.loc['Alpha','avg_possession_pct'],60);self.assertEqual(t.loc['Alpha','possession_matches'],1);self.assertEqual(t.loc['Alpha','possession_missing'],1)
    def test_all_missing_null_not_zero(self):
        with connect(self.db,False) as c:c.execute("UPDATE match_possession SET home_bp=NULL,away_bp=NULL,status='missing',reason='fixture'")
        t=queries(self.db)['standings'];self.assertTrue(t.avg_possession_pct.isna().all());self.assertTrue(t.possession_matches.eq(0).all())
    def test_pandas_and_sql_match_with_possession(self):
        with patch('epl_lab.analysis.quality'):reconcile(self.db)
    def test_empty_historical_possession(self):
        with patch('epl_lab.analysis.quality'):t=reconcile(self.db,'2025-08-01')
        self.assertTrue(t['standings'].avg_possession_pct.isna().all())
    def test_basis_points_decimal(self):self.assertEqual(basis_points('63.6'),6360)
    def test_bad_percentage(self):
        for x in ['-1','101','NaN','Infinity','60.001']:
            with self.assertRaises(ValueError):basis_points(x)
    def test_bad_sum_database_constraint(self):
        with connect(self.db,False) as c:
            with self.assertRaises(sqlite3.IntegrityError):c.execute('UPDATE match_possession SET home_bp=7000 WHERE match_id=1')
    def test_source_score_conflict_quarantined(self):
        teams=encoded([{'code':'3','name':'Alpha'},{'code':'7','name':'Beta'}],['code','name'])
        r=dict(home_team='3.0',away_team='7.0',kickoff_time='2025-08-15T19:00:00+00:00',home_score='0',away_score='0',finished='True',home_possession='60',away_possession='40',match_id='fake-1')
        matches={('Alpha','Beta'):{'match_id':1,'played_on':'2025-08-15','home_goals':1,'away_goals':0}}
        result=parse_sources({'teams.csv':teams,'GW1.csv':encoded([r],list(r))},matches)
        self.assertEqual(result[0][6],'score_conflict');self.assertIsNone(result[0][4]);self.assertIsNone(result[0][5])
    def test_invalid_sum_stops_parse(self):
        teams=encoded([{'code':'3','name':'Alpha'},{'code':'7','name':'Beta'}],['code','name'])
        r=dict(home_team='3',away_team='7',kickoff_time='2025-08-15T19:00:00+00:00',home_score='1',away_score='0',finished='True',home_possession='60',away_possession='50',match_id='fake-1')
        with self.assertRaises(ValueError):parse_sources({'teams.csv':teams,'GW1.csv':encoded([r],list(r))},{('Alpha','Beta'):{'match_id':1,'played_on':'2025-08-15','home_goals':1,'away_goals':0}})
if __name__=='__main__':unittest.main()
