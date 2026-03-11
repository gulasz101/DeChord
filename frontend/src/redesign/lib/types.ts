import type { JobStage } from "../../lib/types";

export interface Chord {
  start: number;
  end: number;
  label: string;
  section?: string;
}

export interface ChordSection {
  name: string;
  startIndex: number;
  endIndex: number;
}

export interface StemInfo {
  id: string;
  stemKey: string;
  label: string;
  uploaderName: string | null;
  sourceType: "System" | "User";
  description: string;
  version: number;
  isArchived: boolean;
  createdAt: string;
}

export interface SongTabSummary {
  sourceStemKey: string;
  sourceDisplayName: string | null;
  sourceType: "System" | "User";
  status: string;
  generatorVersion: string;
  updatedAt: string;
  errorMessage?: string | null;
}

export interface SongNote {
  id: number;
  type: "time" | "chord";
  timestampSec: number | null;
  chordIndex: number | null;
  text: string;
  authorName: string;
  authorAvatar: string;
  resolved: boolean;
  createdAt: string;
}

export interface Song {
  id: string;
  title: string;
  artist: string;
  key: string;
  tempo: number;
  duration: number;
  status: "uploaded" | "processing" | "ready" | "failed" | "needs_review";
  chords: Chord[];
  stems: StemInfo[];
  tab?: SongTabSummary | null;
  notes: SongNote[];
  updatedAt: string;
}

export interface Project {
  id: string;
  name: string;
  description: string;
  songs: Song[];
  recentActivity: ActivityItem[];
  unreadCount: number;
}

export interface Band {
  id: string;
  name: string;
  members: BandMember[];
  projects: Project[];
  avatarColor: string;
}

export interface BandMember {
  id: string;
  name: string;
  instrument: string;
  avatar: string;
  isOnline: boolean;
}

export interface ActivityItem {
  id: string;
  type: "stem_upload" | "comment" | "status_change" | "song_added" | "comment_resolved";
  message: string;
  authorName: string;
  authorAvatar: string;
  timestamp: string;
  songTitle?: string;
}

export interface User {
  id: string;
  name: string;
  email: string;
  instrument: string;
  avatar: string;
}

export interface ProcessingJourney {
  songTitle: string | null;
  uploadFilename: string;
  status: "queued" | "processing" | "complete" | "error";
  stage: JobStage | null;
  progressPct: number;
  stageHistory: JobStage[];
  message: string | null;
  error: string | null;
}
