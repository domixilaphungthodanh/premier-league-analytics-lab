PRAGMA foreign_keys=ON;
CREATE TABLE teams(team_id INTEGER PRIMARY KEY,name TEXT NOT NULL UNIQUE CHECK(length(trim(name))>0));
CREATE TABLE source_files(source_id INTEGER PRIMARY KEY,url TEXT NOT NULL,sha256 TEXT NOT NULL UNIQUE,downloaded_at TEXT NOT NULL,byte_count INTEGER NOT NULL);
CREATE TABLE matches(
 match_id INTEGER PRIMARY KEY,source_id INTEGER NOT NULL REFERENCES source_files,source_row INTEGER NOT NULL,
 played_on TEXT NOT NULL,kickoff_time TEXT NOT NULL,
 home_team_id INTEGER NOT NULL REFERENCES teams,away_team_id INTEGER NOT NULL REFERENCES teams,
 home_goals INTEGER NOT NULL CHECK(home_goals>=0),away_goals INTEGER NOT NULL CHECK(away_goals>=0),
 result TEXT NOT NULL CHECK(result IN ('H','D','A')),
 home_shots INTEGER CHECK(home_shots>=0),away_shots INTEGER CHECK(away_shots>=0),
 home_target INTEGER CHECK(home_target>=0),away_target INTEGER CHECK(away_target>=0),
 home_corners INTEGER CHECK(home_corners>=0),away_corners INTEGER CHECK(away_corners>=0),
 home_yellow INTEGER CHECK(home_yellow>=0),away_yellow INTEGER CHECK(away_yellow>=0),
 home_red INTEGER CHECK(home_red>=0),away_red INTEGER CHECK(away_red>=0),
 CHECK(home_team_id<>away_team_id),UNIQUE(home_team_id,away_team_id),UNIQUE(source_id,source_row),
 CHECK((result='H' AND home_goals>away_goals) OR (result='A' AND home_goals<away_goals) OR (result='D' AND home_goals=away_goals)),
 CHECK(home_target<=home_shots),CHECK(away_target<=away_shots));
CREATE INDEX matches_date ON matches(played_on);
CREATE TABLE metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL);
