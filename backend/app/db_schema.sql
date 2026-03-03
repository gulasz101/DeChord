CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    display_name TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS songs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    original_filename TEXT,
    mime_type TEXT,
    audio_blob BLOB NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
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
    type TEXT NOT NULL CHECK(type IN ('time', 'chord')),
    timestamp_sec REAL,
    chord_index INTEGER,
    text TEXT NOT NULL,
    toast_duration_sec REAL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (song_id) REFERENCES songs(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS song_stems (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    song_id INTEGER NOT NULL,
    stem_key TEXT NOT NULL,
    relative_path TEXT NOT NULL,
    mime_type TEXT,
    duration REAL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(song_id, stem_key),
    FOREIGN KEY (song_id) REFERENCES songs(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS song_midis (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    song_id INTEGER NOT NULL,
    source_stem_key TEXT NOT NULL,
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
CREATE INDEX IF NOT EXISTS idx_analyses_song_id ON analyses(song_id);
CREATE INDEX IF NOT EXISTS idx_chords_analysis_id ON analysis_chords(analysis_id);
CREATE INDEX IF NOT EXISTS idx_notes_song_id ON notes(song_id);
CREATE INDEX IF NOT EXISTS idx_song_stems_song_id ON song_stems(song_id);
CREATE INDEX IF NOT EXISTS idx_song_midis_song_id ON song_midis(song_id);
CREATE INDEX IF NOT EXISTS idx_song_tabs_song_id ON song_tabs(song_id);
