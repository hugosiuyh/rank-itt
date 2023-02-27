DROP TABLE IF EXISTS d_user;
DROP TABLE IF EXISTS d_match;
DROP TABLE IF EXISTS d_score;
DROP TABLE IF EXISTS d_skill;

CREATE TABLE d_user (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  username TEXT UNIQUE NOT NULL,
  password TEXT NOT NULL,
  first_name TEXT NOT NULL,
  created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE d_match (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  self_user_id INTEGER NOT NULL,
  opponent_user_id INTEGER NOT NULL,
  type TEXT NOT NULL DEFAULT 'Singles',
  is_reviewed INTEGER NOT NULL,
  created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (self_user_id) REFERENCES d_user (id),
  FOREIGN KEY (opponent_user_id) REFERENCES d_user (id)
);

CREATE TABLE d_score (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  match_id INTEGER NOT NULL,
  user_id INTEGER NOT NULL,
  score INTEGER NOT NULL,
  is_winner INTEGER NOT NULL,
  is_reviewed INTEGER NOT NULL,
  created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (match_id) REFERENCES d_match (id),
  FOREIGN KEY (user_id) REFERENCES d_user (id)
);

CREATE TABLE d_skill (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  skill NUMERIC NOT NULL,
  uncertainty NUMERIC NOT NULL,
  created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES d_user (id)
);