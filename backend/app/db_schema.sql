CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    display_name TEXT NOT NULL UNIQUE,
    fingerprint_token TEXT UNIQUE,
    username TEXT UNIQUE,
    is_claimed INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_credentials (
    user_id INTEGER PRIMARY KEY,
    password_hash TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS bands (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    owner_user_id INTEGER NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(name, owner_user_id),
    FOREIGN KEY (owner_user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS band_memberships (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    band_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    role TEXT NOT NULL DEFAULT 'member',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(band_id, user_id),
    FOREIGN KEY (band_id) REFERENCES bands(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    band_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(band_id, name),
    FOREIGN KEY (band_id) REFERENCES bands(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS songs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    project_id INTEGER,
    title TEXT NOT NULL,
    original_filename TEXT,
    mime_type TEXT,
    audio_blob BLOB NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS analyses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    song_id INTEGER NOT NULL,
    song_key TEXT NOT NULL,
    tempo INTEGER NOT NULL,
    duration REAL NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (song_id) REFERENCES songs(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS analysis_chords (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    analysis_id INTEGER NOT NULL,
    chord_index INTEGER NOT NULL,
    start_sec REAL NOT NULL,
    end_sec REAL NOT NULL,
    label TEXT NOT NULL,
    FOREIGN KEY (analysis_id) REFERENCES analyses(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS playback_prefs (
    song_id INTEGER PRIMARY KEY,
    speed_percent INTEGER NOT NULL DEFAULT 100,
    volume REAL NOT NULL DEFAULT 1.0,
    loop_start_index INTEGER,
    loop_end_index INTEGER,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (song_id) REFERENCES songs(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    song_id INTEGER NOT NULL,
    author_user_id INTEGER NOT NULL,
    author_name TEXT NOT NULL,
    author_avatar TEXT,
    type TEXT NOT NULL CHECK(type IN ('time', 'chord')),
    timestamp_sec REAL,
    chord_index INTEGER,
    text TEXT NOT NULL,
    toast_duration_sec REAL,
    resolved INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (author_user_id) REFERENCES users(id) ON DELETE RESTRICT,
    FOREIGN KEY (song_id) REFERENCES songs(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS song_stems (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    song_id INTEGER NOT NULL,
    stem_key TEXT NOT NULL,
    relative_path TEXT NOT NULL,
    mime_type TEXT,
    duration REAL,
    source_type TEXT NOT NULL DEFAULT 'system' CHECK(source_type IN ('system', 'user')),
    display_name TEXT,
    version_label TEXT NOT NULL DEFAULT 'legacy',
    uploaded_by_name TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(song_id, stem_key),
    FOREIGN KEY (song_id) REFERENCES songs(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS song_midis (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    song_id INTEGER NOT NULL,
    source_stem_key TEXT NOT NULL,
    source_stem_id INTEGER,
    source_stem_source_type TEXT NOT NULL DEFAULT 'system' CHECK(source_stem_source_type IN ('system', 'user')),
    source_stem_display_name TEXT,
    source_stem_version_label TEXT,
    source_stem_uploaded_by_name TEXT,
    midi_blob BLOB NOT NULL,
    midi_format TEXT NOT NULL DEFAULT 'mid',
    engine TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'complete',
    error_message TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(song_id, source_stem_key),
    FOREIGN KEY (song_id) REFERENCES songs(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS song_tabs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    song_id INTEGER NOT NULL,
    source_midi_id INTEGER NOT NULL,
    tab_blob BLOB NOT NULL,
    tab_format TEXT NOT NULL DEFAULT 'gp5',
    tuning TEXT NOT NULL,
    strings INTEGER NOT NULL,
    generator_version TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'complete',
    error_message TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(song_id, source_midi_id),
    FOREIGN KEY (song_id) REFERENCES songs(id) ON DELETE CASCADE,
    FOREIGN KEY (source_midi_id) REFERENCES song_midis(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_songs_user_id ON songs(user_id);
CREATE INDEX IF NOT EXISTS idx_songs_project_id ON songs(project_id);
CREATE INDEX IF NOT EXISTS idx_bands_owner_user_id ON bands(owner_user_id);
CREATE INDEX IF NOT EXISTS idx_band_memberships_band_id ON band_memberships(band_id);
CREATE INDEX IF NOT EXISTS idx_band_memberships_user_id ON band_memberships(user_id);
CREATE INDEX IF NOT EXISTS idx_projects_band_id ON projects(band_id);
CREATE INDEX IF NOT EXISTS idx_analyses_song_id ON analyses(song_id);
CREATE INDEX IF NOT EXISTS idx_chords_analysis_id ON analysis_chords(analysis_id);
CREATE INDEX IF NOT EXISTS idx_notes_song_id ON notes(song_id);
CREATE INDEX IF NOT EXISTS idx_song_stems_song_id ON song_stems(song_id);
CREATE INDEX IF NOT EXISTS idx_song_midis_song_id ON song_midis(song_id);
CREATE INDEX IF NOT EXISTS idx_song_tabs_song_id ON song_tabs(song_id);
