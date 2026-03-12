import type { Band, User, Song, Chord, StemInfo, SongNote, Project, ActivityItem } from "./types";

function chord(start: number, end: number, label: string): Chord {
  return { start, end, label };
}

const MOCK_CHORDS: Chord[] = [
  // Intro (0-3)
  chord(0, 2.4, "Em"), chord(2.4, 4.8, "G"), chord(4.8, 7.2, "D"), chord(7.2, 9.6, "A"),
  // Verse 1 (4-7)
  chord(9.6, 12.0, "Em"), chord(12.0, 14.4, "C"), chord(14.4, 16.8, "G"), chord(16.8, 19.2, "D"),
  // Chorus (8-11)
  chord(19.2, 21.6, "Am"), chord(21.6, 24.0, "Em"), chord(24.0, 26.4, "B7"), chord(26.4, 28.8, "Em"),
  // Verse 2 (12-15)
  chord(28.8, 31.2, "C"), chord(31.2, 33.6, "G"), chord(33.6, 36.0, "D"), chord(36.0, 38.4, "Am"),
  // Outro (16-19)
  chord(38.4, 40.8, "Em"), chord(40.8, 43.2, "G"), chord(43.2, 45.6, "C"), chord(45.6, 48.0, "D"),
];

// Assign sections
MOCK_CHORDS.forEach((c, i) => {
  if (i <= 3) c.section = "Intro";
  else if (i <= 7) c.section = "Verse 1";
  else if (i <= 11) c.section = "Chorus";
  else if (i <= 15) c.section = "Verse 2";
  else c.section = "Outro";
});

function stem(id: string, key: string, label: string, uploader: string, src: "System" | "User", desc: string, ver: number, archived = false): StemInfo {
  return { id, stemKey: key, label, uploaderName: uploader, sourceType: src, description: desc, version: ver, isArchived: archived, createdAt: "2026-03-01T10:00:00Z" };
}

const MOCK_STEMS: StemInfo[] = [
  stem("s1", "bass", "Bass", "DeChord AI", "System", "Auto-extracted bass stem", 2),
  stem("s1a", "bass", "Bass", "DeChord AI", "System", "Initial bass extraction", 1, true),
  stem("s2", "drums", "Drums", "DeChord AI", "System", "Auto-extracted drum stem", 1),
  stem("s3", "vocals", "Vocals", "DeChord AI", "System", "Auto-extracted vocal stem", 1),
  stem("s4", "guitar", "Guitar", "Mike R.", "User", "My re-recorded guitar part", 1),
  stem("s5", "other", "Other", "DeChord AI", "System", "Remaining audio", 1),
  stem("s6", "bass", "Bass", "Jake T.", "User", "My cover attempt for practice", 3),
];

function note(id: number, type: "time" | "chord", ts: number | null, ci: number | null, text: string, author: string, avatar: string, resolved = false): SongNote {
  return {
    id,
    type,
    timestampSec: ts,
    chordIndex: ci,
    text,
    toastDurationSec: null,
    authorName: author,
    authorAvatar: avatar,
    resolved,
    createdAt: "2026-03-05T14:30:00Z",
    updatedAt: "2026-03-05T14:30:00Z",
  };
}

const MOCK_NOTES: SongNote[] = [
  note(1, "time", 5.2, null, "Killer fill right here — should we accent it more?", "Mike R.", "MR"),
  note(2, "chord", null, 3, "This A chord transition feels rushed, slow down?", "Jake T.", "JT"),
  note(3, "time", 18.5, null, "Love the groove here", "Sarah K.", "SK"),
  note(4, "chord", null, 8, "Am to Em — maybe try Am7?", "Mike R.", "MR", true),
  note(5, "time", 30.0, null, "Bridge starts — everyone pay attention to dynamics", "Jake T.", "JT"),
];

function activity(id: string, type: ActivityItem["type"], msg: string, author: string, avatar: string, song?: string): ActivityItem {
  return { id, type, message: msg, authorName: author, authorAvatar: avatar, timestamp: "2026-03-07T09:15:00Z", songTitle: song };
}

const songs: Song[] = [
  {
    id: "song-1", title: "The Trooper", artist: "Iron Maiden", key: "Em", tempo: 160, duration: 48.0,
    status: "ready", chords: MOCK_CHORDS, stems: MOCK_STEMS, notes: MOCK_NOTES, updatedAt: "2026-03-07T12:00:00Z",
  },
  {
    id: "song-2", title: "Hysteria", artist: "Muse", key: "Am", tempo: 94, duration: 225.0,
    status: "ready", chords: MOCK_CHORDS.map((c, i) => ({ ...c, label: ["Am", "E", "Dm", "Am", "F", "C", "G", "Am"][i % 8] })),
    stems: MOCK_STEMS.slice(0, 4), notes: MOCK_NOTES.slice(0, 2), updatedAt: "2026-03-06T18:00:00Z",
  },
  {
    id: "song-3", title: "Schism", artist: "Tool", key: "Dm", tempo: 87, duration: 412.0,
    status: "processing", chords: [], stems: [], notes: [], updatedAt: "2026-03-07T14:00:00Z",
  },
  {
    id: "song-4", title: "YYZ", artist: "Rush", key: "A", tempo: 104, duration: 265.0,
    status: "needs_review", chords: MOCK_CHORDS.slice(0, 8).map((c, i) => ({ ...c, label: ["A", "Bm", "E", "F#m", "D", "A", "E", "A"][i] })),
    stems: MOCK_STEMS.slice(0, 3), notes: [MOCK_NOTES[0]], updatedAt: "2026-03-05T10:00:00Z",
  },
  {
    id: "song-5", title: "Orion", artist: "Metallica", key: "Em", tempo: 120, duration: 507.0,
    status: "uploaded", chords: [], stems: [], notes: [], updatedAt: "2026-03-07T16:00:00Z",
  },
];

const projects: Project[] = [
  {
    id: "proj-1", name: "Summer Setlist 2026", description: "Songs we're preparing for the summer gig season",
    songs: songs.slice(0, 3), unreadCount: 3,
    recentActivity: [
      activity("a1", "stem_upload", "uploaded a new bass stem", "Jake T.", "JT", "The Trooper"),
      activity("a2", "comment", "left a comment on chord progression", "Mike R.", "MR", "Hysteria"),
      activity("a3", "status_change", "Song processing complete", "DeChord", "DC", "The Trooper"),
      activity("a4", "song_added", "added a new song", "Sarah K.", "SK", "Schism"),
    ],
  },
  {
    id: "proj-2", name: "Covers Night", description: "Classic covers for the acoustic set",
    songs: songs.slice(3), unreadCount: 1,
    recentActivity: [
      activity("a5", "stem_upload", "uploaded guitar stem", "Mike R.", "MR", "YYZ"),
      activity("a6", "comment_resolved", "resolved a comment", "Jake T.", "JT", "YYZ"),
    ],
  },
];

export const MOCK_BANDS: Band[] = [
  {
    id: "band-1", name: "The Rust Belt", avatarColor: "#b45309",
    members: [
      { id: "u1", name: "Jake T.", role: "member", instrument: "Bass", avatar: "JT", presenceState: "not_live", isOnline: true },
      { id: "u2", name: "Mike R.", role: "member", instrument: "Guitar", avatar: "MR", presenceState: "not_live", isOnline: true },
      { id: "u3", name: "Sarah K.", role: "member", instrument: "Drums", avatar: "SK", presenceState: "not_live", isOnline: false },
      { id: "u4", name: "Tom L.", role: "member", instrument: "Vocals", avatar: "TL", presenceState: "not_live", isOnline: false },
    ],
    projects,
  },
  {
    id: "band-2", name: "Midnight Signal", avatarColor: "#6b7234",
    members: [
      { id: "u1", name: "Jake T.", role: "member", instrument: "Bass", avatar: "JT", presenceState: "not_live", isOnline: true },
      { id: "u5", name: "Ava P.", role: "member", instrument: "Keys", avatar: "AP", presenceState: "not_live", isOnline: false },
      { id: "u6", name: "Dan W.", role: "member", instrument: "Guitar", avatar: "DW", presenceState: "not_live", isOnline: true },
    ],
    projects: [{
      id: "proj-3", name: "Demo Sessions", description: "Working on original material",
      songs: [songs[0]], unreadCount: 0,
      recentActivity: [activity("a7", "song_added", "added a new song", "Ava P.", "AP", "Demo Track 1")],
    }],
  },
];

export const MOCK_USER: User = {
  id: "u1", name: "Jake T.", email: "jake@example.com", instrument: "Bass", avatar: "JT",
};
