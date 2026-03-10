import { useCallback, useEffect, useState } from "react";
import {
  claimIdentity,
  getSong,
  regenerateSongStems,
  regenerateSongTabs,
  getStemDownloadUrl,
  getStemsZipDownloadUrl,
  listBandProjects,
  listBands,
  listProjectSongs,
  listSongStems,
  resolveIdentity,
} from "./lib/api";
import { MOCK_BANDS } from "./redesign/lib/mockData";
import type { Band, Project, Song, StemInfo, User, SongNote, Chord } from "./redesign/lib/types";
import { LandingPage } from "./redesign/pages/LandingPage";
import { BandSelectPage } from "./redesign/pages/BandSelectPage";
import { ProjectHomePage } from "./redesign/pages/ProjectHomePage";
import { SongLibraryPage } from "./redesign/pages/SongLibraryPage";
import { SongDetailPage } from "./redesign/pages/SongDetailPage";
import { PlayerPage } from "./redesign/pages/PlayerPage";

type Route =
  | { page: "landing" }
  | { page: "bands" }
  | { page: "project"; band: Band; project: Project }
  | { page: "songs"; band: Band; project: Project }
  | { page: "song-detail"; band: Band; project: Project; song: Song }
  | { page: "player"; band: Band; project: Project; song: Song };

function avatarFromName(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  const first = parts[0]?.[0] ?? "U";
  const second = parts[1]?.[0] ?? "";
  return `${first}${second}`.toUpperCase();
}

function getOrCreateFingerprint(): string {
  if (typeof window === "undefined") {
    return "server-render-fingerprint";
  }
  const key = "dechord.fingerprint";
  const existing = window.localStorage.getItem(key);
  if (existing) return existing;
  const token = `fp-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
  window.localStorage.setItem(key, token);
  return token;
}

function mapChordStatus(hasAnalysis: boolean): Song["status"] {
  return hasAnalysis ? "ready" : "uploaded";
}

function mapProjectSongSummaryToSong(raw: {
  id: number;
  project_id: number;
  title: string;
  original_filename: string | null;
  created_at: string;
  key: string | null;
  tempo: number | null;
  duration: number | null;
}): Song {
  return {
    id: String(raw.id),
    title: raw.title,
    artist: "Unknown Artist",
    key: raw.key ?? "N/A",
    tempo: raw.tempo ?? 0,
    duration: raw.duration ?? 0,
    status: mapChordStatus(Boolean(raw.key || raw.tempo || raw.duration)),
    chords: [],
    stems: [],
    notes: [],
    updatedAt: raw.created_at,
  };
}

function mapStem(stem: { stem_key: string; relative_path: string; mime_type: string | null; duration: number | null }, index: number): StemInfo {
  return {
    id: `${stem.stem_key}-${index + 1}`,
    stemKey: stem.stem_key,
    label: stem.stem_key.charAt(0).toUpperCase() + stem.stem_key.slice(1),
    uploaderName: "System",
    sourceType: "System",
    description: stem.relative_path,
    version: 1,
    isArchived: false,
    createdAt: new Date().toISOString(),
  };
}

function mapNote(note: {
  id: number;
  type: "time" | "chord";
  timestamp_sec: number | null;
  chord_index: number | null;
  text: string;
}, user: User): SongNote {
  return {
    id: note.id,
    type: note.type,
    timestampSec: note.timestamp_sec,
    chordIndex: note.chord_index,
    text: note.text,
    authorName: user.name,
    authorAvatar: user.avatar,
    resolved: false,
    createdAt: new Date().toISOString(),
  };
}

function mapChord(chord: { start: number; end: number; label: string }): Chord {
  return {
    start: chord.start,
    end: chord.end,
    label: chord.label,
  };
}

async function loadBandHierarchy(currentUser: User | null): Promise<Band[]> {
  try {
    const bandsResponse = await listBands();
    const mappedBands: Band[] = [];

    for (const band of bandsResponse.bands) {
      const projectsResponse = await listBandProjects(band.id);
      const mappedProjects: Project[] = [];

      for (const project of projectsResponse.projects) {
        const songsResponse = await listProjectSongs(project.id);
        const songs = songsResponse.songs.map(mapProjectSongSummaryToSong);
        mappedProjects.push({
          id: String(project.id),
          name: project.name,
          description: project.description ?? "",
          songs,
          recentActivity: [],
          unreadCount: 0,
        });
      }

      mappedBands.push({
        id: String(band.id),
        name: band.name,
        avatarColor: "#7c3aed",
        projects: mappedProjects,
        members: currentUser
          ? [
              {
                id: currentUser.id,
                name: currentUser.name,
                instrument: currentUser.instrument,
                avatar: currentUser.avatar,
                isOnline: true,
              },
            ]
          : [],
      });
    }

    if (mappedBands.length > 0) {
      return mappedBands;
    }
  } catch {
    // Fall back to mock data when API is not fully ready.
  }

  return MOCK_BANDS;
}

export default function App() {
  const [route, setRoute] = useState<Route>({ page: "landing" });
  const [user, setUser] = useState<User | null>(null);
  const [bands, setBands] = useState<Band[]>([]);
  const [identityUserId, setIdentityUserId] = useState<number | null>(null);
  const [isClaimed, setIsClaimed] = useState(false);

  const bootstrap = useCallback(async () => {
    try {
      const fingerprint = getOrCreateFingerprint();
      const identity = await resolveIdentity(fingerprint);
      const mappedUser: User = {
        id: String(identity.user.id),
        name: identity.user.display_name,
        email: identity.user.username ? `${identity.user.username}@dechord.local` : `${identity.user.id}@guest.local`,
        instrument: "Bass",
        avatar: avatarFromName(identity.user.display_name),
      };
      setUser(mappedUser);
      setIdentityUserId(identity.user.id);
      setIsClaimed(identity.user.is_claimed);
      const loadedBands = await loadBandHierarchy(mappedUser);
      setBands(loadedBands);
    } catch {
      const fallbackUser: User = {
        id: "guest-1",
        name: "Guest Musician",
        email: "guest@dechord.local",
        instrument: "Bass",
        avatar: "GM",
      };
      setUser(fallbackUser);
      setIdentityUserId(null);
      setIsClaimed(false);
      const loadedBands = await loadBandHierarchy(fallbackUser);
      setBands(loadedBands);
    }
  }, []);

  useEffect(() => {
    const handle = window.setTimeout(() => {
      void bootstrap();
    }, 0);
    return () => {
      window.clearTimeout(handle);
    };
  }, [bootstrap]);

  const loadSongDetails = useCallback(
    async (song: Song): Promise<Song> => {
      const songId = Number(song.id);
      if (Number.isNaN(songId) || !user) return song;

      try {
        const [songDetail, stemsDetail] = await Promise.all([
          getSong(songId),
          listSongStems(songId),
        ]);
        return {
          ...song,
          key: songDetail.analysis?.key ?? song.key,
          tempo: songDetail.analysis?.tempo ?? song.tempo,
          duration: songDetail.analysis?.duration ?? song.duration,
          status: mapChordStatus(Boolean(songDetail.analysis)),
          chords: (songDetail.analysis?.chords ?? []).map(mapChord),
          stems: stemsDetail.stems.map(mapStem),
          notes: songDetail.notes.map((n) => mapNote(n, user)),
        };
      } catch {
        return song;
      }
    },
    [user],
  );

  const goBack = useCallback(() => {
    switch (route.page) {
      case "bands":
        setRoute({ page: "landing" });
        break;
      case "project":
        setRoute({ page: "bands" });
        break;
      case "songs":
        setRoute({ page: "project", band: route.band, project: route.project });
        break;
      case "song-detail":
        setRoute({ page: "songs", band: route.band, project: route.project });
        break;
      case "player":
        setRoute({ page: "song-detail", band: route.band, project: route.project, song: route.song });
        break;
      default:
        setRoute({ page: "landing" });
    }
  }, [route]);

  const refreshSongDetailRoute = useCallback(async () => {
    if (route.page !== "song-detail") return;
    const detailed = await loadSongDetails(route.song);
    setRoute({ page: "song-detail", band: route.band, project: route.project, song: detailed });
  }, [loadSongDetails, route]);

  if (!user) {
    return <LandingPage onGetStarted={() => setRoute({ page: "bands" })} onSignIn={() => setRoute({ page: "bands" })} />;
  }

  switch (route.page) {
    case "landing":
      return <LandingPage onGetStarted={() => setRoute({ page: "bands" })} onSignIn={() => setRoute({ page: "bands" })} />;
    case "bands":
      return (
        <BandSelectPage
          user={user}
          bands={bands}
          isClaimed={isClaimed}
          onClaimAccount={() => {
            if (identityUserId === null || typeof window === "undefined") return;
            const username = window.prompt("Choose a username");
            if (!username) return;
            const password = window.prompt("Choose a password (min 8 chars)");
            if (!password || password.length < 8) return;
            void (async () => {
              try {
                const claimed = await claimIdentity({
                  user_id: identityUserId,
                  username,
                  password,
                });
                setIsClaimed(claimed.user.is_claimed);
              } catch {
                // Keep current state when claim fails.
              }
            })();
          }}
          onSelectBand={(band) => setRoute({ page: "project", band, project: band.projects[0] })}
          onSignOut={() => {
            setRoute({ page: "landing" });
          }}
        />
      );
    case "project":
      return (
        <ProjectHomePage
          user={user}
          band={route.band}
          project={route.project}
          onSelectProject={(project) => setRoute({ page: "project", band: route.band, project })}
          onOpenSongs={() => setRoute({ page: "songs", band: route.band, project: route.project })}
          onBack={goBack}
        />
      );
    case "songs":
      return (
        <SongLibraryPage
          user={user}
          band={route.band}
          project={route.project}
          onSelectSong={(song) => {
            void (async () => {
              const detailed = await loadSongDetails(song);
              setRoute({ page: "song-detail", band: route.band, project: route.project, song: detailed });
            })();
          }}
          onBack={goBack}
        />
      );
    case "song-detail":
      return (
        <SongDetailPage
          user={user}
          band={route.band}
          project={route.project}
          song={route.song}
          onDownloadStem={(stemKey) => {
            const songId = Number(route.song.id);
            if (Number.isNaN(songId) || typeof window === "undefined") return;
            window.location.assign(getStemDownloadUrl(songId, stemKey));
          }}
          onDownloadAllStems={() => {
            const songId = Number(route.song.id);
            if (Number.isNaN(songId) || typeof window === "undefined") return;
            window.location.assign(getStemsZipDownloadUrl(songId));
          }}
          onGenerateStems={async () => {
            const songId = Number(route.song.id);
            if (Number.isNaN(songId)) return;
            await regenerateSongStems(songId);
            await refreshSongDetailRoute();
          }}
          onGenerateBassTab={async (sourceStemKey) => {
            const songId = Number(route.song.id);
            if (Number.isNaN(songId)) return;
            await regenerateSongTabs(songId, { source_stem_key: sourceStemKey });
            await refreshSongDetailRoute();
          }}
          onOpenPlayer={() => setRoute({ page: "player", band: route.band, project: route.project, song: route.song })}
          onBack={goBack}
        />
      );
    case "player":
      return (
        <PlayerPage
          user={user}
          band={route.band}
          project={route.project}
          song={route.song}
          onBack={goBack}
        />
      );
    default:
      return <LandingPage onGetStarted={() => setRoute({ page: "bands" })} onSignIn={() => setRoute({ page: "bands" })} />;
  }
}
