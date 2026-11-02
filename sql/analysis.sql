-- Một dòng mỗi trận; JOIN cùng bảng teams hai lần.
SELECT m.played_on,h.name home,a.name away,m.home_goals,m.away_goals
FROM matches m JOIN teams h ON h.team_id=m.home_team_id
JOIN teams a ON a.team_id=m.away_team_id
ORDER BY m.played_on,m.kickoff_time,m.match_id LIMIT 20;

-- Hai dòng mỗi trận; điểm nhìn của từng đội.
WITH sides AS (
 SELECT home_team_id team_id,home_goals gf,away_goals ga FROM matches
 UNION ALL SELECT away_team_id,away_goals,home_goals FROM matches)
SELECT t.name,COUNT(*) played,SUM(gf) gf,SUM(ga) ga,
SUM(CASE WHEN gf>ga THEN 3 WHEN gf=ga THEN 1 ELSE 0 END) points
FROM sides s JOIN teams t USING(team_id) GROUP BY t.team_id,t.name
ORDER BY points DESC,SUM(gf-ga) DESC,SUM(gf) DESC,t.name;
