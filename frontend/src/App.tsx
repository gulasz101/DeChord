import { useCallback, useEffect, useState } from "react";
import {
  claimIdentity,
  createBand,
  createProject,
  getJobStatus,
  getResult,
  getSong,
  getSongTabs,
  uploadAudio,
  uploadSongStem,
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
import type { ProcessMode, TabGenerationQuality } from "./lib/types";
import type { Band, Project, Song, StemInfo, User, SongNote, Chord } from "./redesign/lib/types";
import { LandingPage } from "./redesign/pages/LandingPage";
import { BandSelectPage } from "./redesign/pages/BandSelectPage";
import { ProjectHomePage } from "./redesign/pages/ProjectHomePage";
import { ProcessingJourneyPage } from "./redesign/pages/ProcessingJourneyPage";
import { SongLibraryPage } from "./redesign/pages/SongLibraryPage";
import { SongDetailPage } from "./redesign/pages/SongDetailPage";
import { PlayerPage } from "./redesign/pages/PlayerPage";

type Route =
  | { page: "landing" }
  | { page: "bands" }
  | { page: "project"; band: Band; project: Project | null }
  | { page: "songs"; band: Band; project: Project }
  | {
      page: "processing-journey";
      band: Band;
      project: Project;
      songId: number;
      jobId: string;
      retryCount: number;
      uploadFilename: string;
      processMode: ProcessMode;
      tabGenerationQuality: TabGenerationQuality;
      journey: {
        songTitle: string | null;
        uploadFilename: string;
        status: "queued" | "processing" | "complete" | "error";
        stage: import("./lib/types").JobStage | null;
        progressPct: number;
        stageHistory: import("./lib/types").JobStage[];
        message: string | null;
        error: string | null;
      };
    }
  | { page: "song-detail"; band: Band; project: Project; song: Song }
  | { page: "player"; band: Band; project: Project; song: Song };

type ProcessingJourneyRoute = Extract<Route, { page: "processing-journey" }>;

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

function mapStem(stem: {
  stem_key: string;
  source_type?: "system" | "user";
  display_name?: string;
  version_label?: string;
  uploaded_by_name?: string | null;
  is_archived?: boolean;
  relative_path: string;
  mime_type: string | null;
  duration: number | null;
  created_at?: string;
}, index: number): StemInfo {
  const parsedVersion = stem.version_label ? Number.parseInt(stem.version_label.replace(/\D+/g, ""), 10) : Number.NaN;
  const sourceType = stem.source_type === "user" ? "User" : "System";
  return {
    id: `${stem.stem_key}-${index + 1}`,
    stemKey: stem.stem_key,
    label: stem.display_name?.trim() || stem.stem_key.charAt(0).toUpperCase() + stem.stem_key.slice(1),
    uploaderName: stem.uploaded_by_name ?? (sourceType === "System" ? "System" : null),
    sourceType,
    description: stem.relative_path,
    version: Number.isFinite(parsedVersion) ? parsedVersion : index + 1,
    isArchived: stem.is_archived ?? false,
    createdAt: stem.created_at ?? new Date().toISOString(),
  };
}

function mapSongTab(tab: Awaited<ReturnType<typeof getSongTabs>>["tab"]): Song["tab"] {
  if (!tab) {
    return null;
  }

  return {
    sourceStemKey: tab.source_stem_key,
    sourceDisplayName: tab.source_display_name ?? null,
    sourceType: tab.source_type === "user" ? "User" : "System",
    status: tab.status,
    generatorVersion: tab.generator_version,
    updatedAt: tab.updated_at,
    errorMessage: tab.error_message,
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

function mergeSongWithDetails(
  song: Song,
  songDetail: Awaited<ReturnType<typeof getSong>>,
  stemsDetail: Awaited<ReturnType<typeof listSongStems>>,
  tabsDetail: Awaited<ReturnType<typeof getSongTabs>>,
  user: User,
): Song {
  return {
    ...song,
    title: songDetail.song.title || song.title,
    key: songDetail.analysis?.key ?? song.key,
    tempo: songDetail.analysis?.tempo ?? song.tempo,
    duration: songDetail.analysis?.duration ?? song.duration,
    status: mapChordStatus(Boolean(songDetail.analysis)),
    chords: (songDetail.analysis?.chords ?? []).map(mapChord),
    stems: stemsDetail.stems.map(mapStem),
    tab: mapSongTab(tabsDetail.tab),
    notes: songDetail.notes.map((n) => mapNote(n, user)),
    updatedAt: songDetail.song.created_at,
  };
}

function mapSongMetaToSong(raw: {
  id: number;
  project_id: number;
  title: string;
  original_filename: string | null;
  created_at: string;
}): Song {
  return mapProjectSongSummaryToSong({
    ...raw,
    key: null,
    tempo: null,
    duration: null,
  });
}

function mapJobStatusToJourney(
  currentJourney: ProcessingJourneyRoute["journey"],
  uploadFilename: string,
  status: {
    status: "queued" | "processing" | "complete" | "error";
    stage?: import("./lib/types").JobStage;
    stage_history?: import("./lib/types").JobStage[];
    progress_pct?: number;
    message?: string;
    error?: string;
  },
) {
  return {
    ...currentJourney,
    uploadFilename,
    status: status.status,
    stage: status.stage ?? currentJourney.stage,
    progressPct: status.progress_pct ?? currentJourney.progressPct,
    stageHistory: status.stage_history && status.stage_history.length > 0
      ? status.stage_history
      : currentJourney.stageHistory,
    message: status.message ?? currentJourney.message,
    error: status.status === "error" ? (status.error ?? status.message ?? currentJourney.error) : null,
  };
}

function getJourneyErrorMessage(error: unknown): string {
  if (error instanceof Error) {
    if (error.message === "Processing job no longer available after reset") {
      return "This processing job was lost after a reset. DeChord cannot recover in-progress jobs yet.";
    }
    if (error.message === "Processing result no longer available after reset") {
      return "The finished job result was lost after a reset. Retry refresh or return to the library.";
    }
    return error.message;
  }
  return "Processing status is temporarily unavailable.";
}

async function loadBandHierarchy(currentUser: User | null): Promise<Band[]> {
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

  return mappedBands;
}

export default function App() {
  const [route, setRoute] = useState<Route>({ page: "landing" });
  const [user, setUser] = useState<User | null>(null);
  const [bands, setBands] = useState<Band[]>([]);
  const [identityUserId, setIdentityUserId] = useState<number | null>(null);
  const [isClaimed, setIsClaimed] = useState(false);

  const refreshBands = useCallback(async (currentUser: User) => {
    const loadedBands = await loadBandHierarchy(currentUser);
    setBands(loadedBands);
    return loadedBands;
  }, []);

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
      await refreshBands(mappedUser);
    } catch {
      setUser(null);
      setBands([]);
      setIdentityUserId(null);
      setIsClaimed(false);
    }
  }, [refreshBands]);

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
        const [songDetail, stemsDetail, tabsDetail] = await Promise.all([
          getSong(songId),
          listSongStems(songId),
          getSongTabs(songId),
        ]);
        return {
          ...mergeSongWithDetails(song, songDetail, stemsDetail, tabsDetail, user),
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
      case "processing-journey":
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
    const currentSong = route.song;
    const detailed = await loadSongDetails(currentSong);
    setRoute((current) => {
      if (current.page !== "song-detail" || current.song.id !== currentSong.id) {
        return current;
      }
      return { page: "song-detail", band: current.band, project: current.project, song: detailed };
    });
  }, [loadSongDetails, route]);

  const findBandInHierarchy = useCallback((loadedBands: Band[], bandId: string) => {
    return loadedBands.find((band) => band.id === bandId) ?? null;
  }, []);

  const findProjectInBand = useCallback((band: Band | null, projectId: string) => {
    return band?.projects.find((project) => project.id === projectId) ?? null;
  }, []);

  useEffect(() => {
    if (route.page !== "processing-journey" || !user) return;

    const processingRoute = route;

    let cancelled = false;
    let timeoutHandle: number | null = null;

    const failJourney = (error: unknown) => {
      setRoute((current) => {
        if (current.page !== "processing-journey" || current.jobId !== processingRoute.jobId) {
          return current;
        }
        return {
          ...current,
          journey: {
            ...current.journey,
            status: "error",
            stage: current.journey.stage ?? "error",
            progressPct: current.journey.progressPct,
            error: getJourneyErrorMessage(error),
            message: current.journey.message ?? "Processing failed",
            stageHistory: current.journey.stageHistory.includes("error")
              ? current.journey.stageHistory
              : [...current.journey.stageHistory, "error"],
          },
        };
      });
    };

    const poll = async () => {
      try {
        const status = await getJobStatus(processingRoute.jobId);
        if (cancelled) return;

        setRoute((current) => {
          if (current.page !== "processing-journey" || current.jobId !== processingRoute.jobId) {
            return current;
          }
          return {
            ...current,
            journey: mapJobStatusToJourney(current.journey, processingRoute.uploadFilename, status),
          };
        });

        if (status.status === "error") {
          return;
        }

        if (status.status === "complete") {
          const result = await getResult(processingRoute.jobId);
          if (cancelled) return;

          const loadedBands = await refreshBands(user);
          if (cancelled) return;

          const refreshedBand = findBandInHierarchy(loadedBands, processingRoute.band.id) ?? processingRoute.band;
          const refreshedProject = findProjectInBand(refreshedBand, processingRoute.project.id) ?? processingRoute.project;
          const summarySong = refreshedProject.songs.find((song) => song.id === String(result.song_id));
          const baseSong = summarySong ?? mapSongMetaToSong({
            id: result.song_id,
            project_id: Number(refreshedProject.id),
            title: processingRoute.journey.songTitle ?? processingRoute.uploadFilename,
            original_filename: processingRoute.uploadFilename,
            created_at: new Date().toISOString(),
          });
          const detailedSong = await loadSongDetails(baseSong);
          if (cancelled) return;

          setRoute({
            page: "song-detail",
            band: refreshedBand,
            project: refreshedProject,
            song: detailedSong,
          });
          return;
        }

        timeoutHandle = window.setTimeout(() => {
          void poll();
        }, 1000);
      } catch (error) {
        if (!cancelled) {
          failJourney(error);
        }
      }
    };

    void poll();

    return () => {
      cancelled = true;
      if (timeoutHandle !== null) {
        window.clearTimeout(timeoutHandle);
      }
    };
  }, [
    findBandInHierarchy,
    findProjectInBand,
    loadSongDetails,
    refreshBands,
    route.page,
    route.page === "processing-journey" ? route.jobId : null,
    route.page === "processing-journey" ? route.retryCount : null,
    user,
  ]);

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
          onCreateBand={async ({ name }) => {
            if (!user) return;
            await createBand({ name });
            await refreshBands(user);
          }}
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
          onSelectBand={(band) => {
            const firstProject = band.projects[0];
            setRoute({ page: "project", band, project: firstProject ?? null });
          }}
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
          onCreateProject={async ({ name, description }) => {
            if (!user) return;
            const created = await createProject(Number(route.band.id), { name, description });
            const loadedBands = await refreshBands(user);
            const refreshedBand = findBandInHierarchy(loadedBands, route.band.id);
            const refreshedProject = findProjectInBand(refreshedBand, String(created.project.id));
            if (!refreshedBand) return;
            setRoute({ page: "project", band: refreshedBand, project: refreshedProject });
          }}
          onOpenSongs={() => {
            if (!route.project) return;
            setRoute({ page: "songs", band: route.band, project: route.project });
          }}
          onBack={goBack}
        />
      );
    case "songs":
      return (
        <SongLibraryPage
          user={user}
          band={route.band}
          project={route.project}
          onUploadSong={async (file, processMode, tabGenerationQuality) => {
            if (!user) return;
            const upload = await uploadAudio(file, processMode, tabGenerationQuality, Number(route.project.id));
            setRoute({
              page: "processing-journey",
              band: route.band,
              project: route.project,
              songId: upload.song_id,
              jobId: upload.job_id,
              retryCount: 0,
              uploadFilename: file.name,
              processMode,
              tabGenerationQuality,
              journey: {
                songTitle: null,
                uploadFilename: file.name,
                status: "queued",
                stage: "queued",
                progressPct: 0,
                stageHistory: ["queued"],
                message: "Queued",
                error: null,
              },
            });
          }}
          onSelectSong={(song) => {
            void (async () => {
              const detailed = await loadSongDetails(song);
              setRoute({ page: "song-detail", band: route.band, project: route.project, song: detailed });
            })();
          }}
          onBack={goBack}
        />
      );
    case "processing-journey":
      return (
        <ProcessingJourneyPage
          band={route.band}
          project={route.project}
          journey={route.journey}
          onBack={goBack}
          onRetryRefresh={() => {
            setRoute((current) => {
              if (current.page !== "processing-journey") return current;
              return {
                ...current,
                retryCount: current.retryCount + 1,
                journey: {
                  ...current.journey,
                  status: "queued",
                  error: null,
                  message: "Retrying processing refresh...",
                },
              };
            });
          }}
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
          onUploadStem={async ({ stemKey, file }) => {
            const songId = Number(route.song.id);
            if (Number.isNaN(songId)) return;
            await uploadSongStem(songId, { stemKey, file });
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
