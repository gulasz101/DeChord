import { useCallback, useEffect, useMemo, useState } from "react";
import {
  claimIdentity,
  createBand,
  updateBand,
  createProject,
  createSongNote,
  deleteSongNote,
  getProjectActivity,
  getJobStatus,
  getResult,
  pollUntilComplete,
  getSong,
  getSongTabs,
  listBandMembers,
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
  resolveSongNote,
  resolveIdentity,
  savePlaybackPrefs,
  setApiIdentityUserId,
  updateSongNote,
  updateProject,
} from "./lib/api";
import type { JobStatus, PlaybackPrefs, ProcessMode, TabGenerationQuality } from "./lib/types";
import type { Band, Project, Song, StemInfo, User, SongNote, Chord } from "./redesign/lib/types";
import { LandingPage } from "./redesign/pages/LandingPage";
import { BandSelectPage } from "./redesign/pages/BandSelectPage";
import { ProjectHomePage } from "./redesign/pages/ProjectHomePage";
import { ProcessingJourneyPage } from "./redesign/pages/ProcessingJourneyPage";
import { SongLibraryPage } from "./redesign/pages/SongLibraryPage";
import { SongDetailPage } from "./redesign/pages/SongDetailPage";
import { PlayerPage } from "./redesign/pages/PlayerPage";
import { deriveStemWarning } from "./lib/uploadWarnings";

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
    tabSourceUrl: null,
    playbackPrefs: {
      speedPercent: 100,
      volume: 1,
      loopStartIndex: null,
      loopEndIndex: null,
    },
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
  type: "time" | "chord" | "general";
  timestamp_sec: number | null;
  chord_index: number | null;
  text: string;
  toast_duration_sec: number | null;
  resolved: boolean;
  author_name: string | null;
  author_avatar: string | null;
  author_user_id: number | null;
  parent_id: number | null;
  created_at: string;
  updated_at: string;
}): SongNote {
  return {
    id: note.id,
    type: note.type,
    timestampSec: note.timestamp_sec,
    chordIndex: note.chord_index,
    text: note.text,
    toastDurationSec: note.toast_duration_sec,
    authorName: note.author_name,
    authorAvatar: note.author_avatar,
    userId: note.author_user_id,
    resolved: note.resolved,
    parentId: note.parent_id,
    createdAt: note.created_at,
    updatedAt: note.updated_at,
  };
}

function mapChord(chord: { start: number; end: number; label: string }): Chord {
  return {
    start: chord.start,
    end: chord.end,
    label: chord.label,
  };
}

function mapBandMember(member: Awaited<ReturnType<typeof listBandMembers>>["members"][number]): Band["members"][number] {
  return {
    id: member.id,
    name: member.name,
    role: member.role,
    avatar: member.avatar,
    presenceState: member.presenceState,
    instrument: member.role,
    isOnline: member.presenceState !== "not_live",
  };
}

function mapActivityType(eventType: string): Project["recentActivity"][number]["type"] {
  switch (eventType) {
    case "song_created":
      return "song_added";
    case "stem_uploaded":
    case "stems_regenerated":
      return "stem_upload";
    case "note_created":
      return "comment";
    case "note_resolved":
      return "comment_resolved";
    default:
      return "status_change";
  }
}

function mapActivityItem(activity: Awaited<ReturnType<typeof getProjectActivity>>["activity"][number]): Project["recentActivity"][number] {
  return {
    id: String(activity.id),
    type: mapActivityType(activity.event_type),
    message: activity.message,
    authorName: activity.author_name,
    authorAvatar: activity.author_avatar ?? avatarFromName(activity.author_name),
    timestamp: activity.timestamp,
    songTitle: activity.song_title ?? undefined,
  };
}

function applyProjectCollaborationToBand(
  band: Band,
  projectId: string,
  recentActivity: Project["recentActivity"],
  unreadCount: number,
): Band {
  return {
    ...band,
    projects: band.projects.map((project) => (
      project.id === projectId
        ? {
            ...project,
            recentActivity,
            unreadCount,
          }
        : project
    )),
  };
}

function updateRouteProjectCollaboration(
  current: Route,
  bandId: string,
  projectId: string,
  recentActivity: Project["recentActivity"],
  unreadCount: number,
): Route {
  switch (current.page) {
    case "project": {
      if (!current.project || current.band.id !== bandId || current.project.id !== projectId) {
        return current;
      }
      const band = applyProjectCollaborationToBand(current.band, projectId, recentActivity, unreadCount);
      return {
        page: "project",
        band,
        project: band.projects.find((project) => project.id === projectId) ?? current.project,
      };
    }
    case "songs":
    case "song-detail":
    case "player":
    case "processing-journey": {
      if (current.band.id !== bandId || current.project.id !== projectId) {
        return current;
      }
      const band = applyProjectCollaborationToBand(current.band, projectId, recentActivity, unreadCount);
      const project = band.projects.find((candidate) => candidate.id === projectId) ?? current.project;
      return {
        ...current,
        band,
        project,
      };
    }
    default:
      return current;
  }
}

function mergeSongWithDetails(
  song: Song,
  songDetail: Awaited<ReturnType<typeof getSong>>,
  stemsDetail: Awaited<ReturnType<typeof listSongStems>>,
  tabsDetail: Awaited<ReturnType<typeof getSongTabs>>,
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
    notes: songDetail.notes.map(mapNote),
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
      return "The finished job result was lost after a reset. Refresh the library or return to the library.";
    }
    return error.message;
  }
  return "Processing status is temporarily unavailable.";
}

function getJourneyResetLossState(error: unknown): { message: string; error: string } | null {
  if (!(error instanceof Error)) {
    return null;
  }
  if (error.message === "Processing job no longer available after reset") {
    return {
      message: "Reset removed this in-progress job. Re-upload the song or return to the library.",
      error: "This processing job was lost after a reset. DeChord cannot recover in-progress jobs yet.",
    };
  }
  if (error.message === "Processing result no longer available after reset") {
    return {
      message: "Reset removed the saved result for this job. Refresh the library or return to the library.",
      error: "The finished job result was lost after a reset. Refresh the library or return to the library.",
    };
  }
  return null;
}

function isJourneyResetLossError(error: string | null): boolean {
  return error === "This processing job was lost after a reset. DeChord cannot recover in-progress jobs yet."
    || error === "The finished job result was lost after a reset. Refresh the library or return to the library.";
}

function isTransientJourneyPollingError(error: unknown): boolean {
  return error instanceof Error && error.message === "Failed to fetch";
}

async function loadBandHierarchy(includeArchived = false): Promise<Band[]> {
  const bandsResponse = await listBands(includeArchived);
  const mappedBands: Band[] = [];

  for (const band of bandsResponse.bands) {
    const [membersResponse, projectsResponse] = await Promise.all([
      listBandMembers(band.id),
      listBandProjects(band.id),
    ]);
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
        unreadCount: project.unread_count,
      });
    }

    mappedBands.push({
      id: String(band.id),
      name: band.name,
      avatarColor: "#7c3aed",
      projects: mappedProjects,
      members: membersResponse.members.map(mapBandMember),
      archived_at: band.archived_at,
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
  const [showArchivedBands, setShowArchivedBands] = useState(false);
  const [showArchivedProjects, setShowArchivedProjects] = useState(false);
  const [songUploadLoading, setSongUploadLoading] = useState(false);
  const [songUploadStatus, setSongUploadStatus] = useState<Pick<JobStatus, "message" | "progress_pct" | "stage_progress_pct"> | null>(null);
  const [songUploadWarning, setSongUploadWarning] = useState<string | null>(null);
  const [songUploadError, setSongUploadError] = useState<string | null>(null);
  const [stemUploadLoading, setStemUploadLoading] = useState(false);
  const [stemUploadError, setStemUploadError] = useState<string | null>(null);

  const refreshBands = useCallback(async (includeArchived = false) => {
    const loadedBands = await loadBandHierarchy(includeArchived);
    setBands(loadedBands);
    return loadedBands;
  }, []);

  const applyProjectCollaborationState = useCallback((
    bandId: string,
    projectId: string,
    recentActivity: Project["recentActivity"],
    unreadCount: number,
    sourceBands?: Band[],
  ) => {
    const updateBands = (candidateBands: Band[]) => candidateBands.map((band) => (
      band.id === bandId
        ? applyProjectCollaborationToBand(band, projectId, recentActivity, unreadCount)
        : band
    ));

    const nextBands = sourceBands ? updateBands(sourceBands) : null;
    if (nextBands) {
      setBands(nextBands);
    } else {
      setBands((currentBands) => updateBands(currentBands));
    }

    setRoute((current) => updateRouteProjectCollaboration(current, bandId, projectId, recentActivity, unreadCount));
    return nextBands;
  }, []);

  const refreshProjectCollaboration = useCallback(async (bandId: string, projectId: string) => {
    const [activityResponse, loadedBands] = await Promise.all([
      getProjectActivity(Number(projectId)),
      refreshBands(),
    ]);
    const recentActivity = activityResponse.activity.map(mapActivityItem);
    applyProjectCollaborationState(
      bandId,
      projectId,
      recentActivity,
      activityResponse.unread_count,
      loadedBands,
    );
    return { activityResponse, recentActivity };
  }, [applyProjectCollaborationState, refreshBands]);

  const markProjectActivityRead = useCallback(async (projectId: string) => {
    const headers = identityUserId === null ? undefined : { "X-DeChord-User-Id": String(identityUserId) };
    const response = await fetch(`/api/projects/${projectId}/activity/read`, {
      method: "POST",
      ...(headers ? { headers } : {}),
    });
    if (!response.ok) {
      throw new Error("Failed to mark project activity as read");
    }
    return response.json() as Promise<{ unread_count: number }>;
  }, [identityUserId]);

  const updateSongEverywhere = useCallback((songId: string, updater: (song: Song) => Song) => {
    setBands((currentBands) => currentBands.map((band) => ({
      ...band,
      projects: band.projects.map((project) => ({
        ...project,
        songs: project.songs.map((song) => (
          song.id === songId ? updater(song) : song
        )),
      })),
    })));

    setRoute((currentRoute) => {
      if ((currentRoute.page !== "song-detail" && currentRoute.page !== "player") || currentRoute.song.id !== songId) {
        return currentRoute;
      }
      return {
        ...currentRoute,
        song: updater(currentRoute.song),
      };
    });
  }, []);

  const bootstrap = useCallback(async () => {
    try {
      const fingerprint = getOrCreateFingerprint();
      const identity = await resolveIdentity(fingerprint);
      setApiIdentityUserId(identity.user.id);
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
      await refreshBands();
    } catch {
      setApiIdentityUserId(null);
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
          ...mergeSongWithDetails(song, songDetail, stemsDetail, tabsDetail),
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

  const refreshPlayerRoute = useCallback(async () => {
    if (route.page !== "player") return;
    const currentSong = route.song;
    const detailed = await loadSongDetails(currentSong);
    setRoute((current) => {
      if (current.page !== "player" || current.song.id !== currentSong.id) {
        return current;
      }
      return { page: "player", band: current.band, project: current.project, song: detailed };
    });
  }, [loadSongDetails, route]);

  const openPlayerForSong = useCallback(async (band: Band, project: Project, song: Song) => {
    const detailed = await loadSongDetails(song);

    setRoute((current) => {
      if (
        current.page !== "song-detail"
        || current.band.id !== band.id
        || current.project.id !== project.id
        || current.song.id !== song.id
      ) {
        return current;
      }

      return { page: "player", band, project, song: detailed };
    });
  }, [loadSongDetails]);

  const findBandInHierarchy = useCallback((loadedBands: Band[], bandId: string) => {
    return loadedBands.find((band) => band.id === bandId) ?? null;
  }, []);

  const findProjectInBand = useCallback((band: Band | null, projectId: string) => {
    return band?.projects.find((project) => project.id === projectId) ?? null;
  }, []);

  const activeProjectBandId = route.page === "project" ? route.band.id : null;
  const activeProjectId = route.page === "project" && route.project ? route.project.id : null;

  useEffect(() => {
    if (route.page !== "project" || !route.project || activeProjectBandId === null || activeProjectId === null) return;

    let cancelled = false;
    const bandId = activeProjectBandId;
    const projectId = activeProjectId;

    void (async () => {
      try {
        const activityResponse = await getProjectActivity(Number(projectId));
        if (cancelled) return;

        const recentActivity = activityResponse.activity.map(mapActivityItem);
        applyProjectCollaborationState(bandId, projectId, recentActivity, activityResponse.unread_count);

        const markedRead = await markProjectActivityRead(projectId);
        if (cancelled) return;

        applyProjectCollaborationState(bandId, projectId, recentActivity, markedRead.unread_count);
        await refreshBands();
      } catch {
        // Leave existing route state untouched when collaboration hydration fails.
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [activeProjectBandId, activeProjectId, applyProjectCollaborationState, markProjectActivityRead, refreshBands]);

  useEffect(() => {
    if (route.page !== "processing-journey" || !user) return;

    const processingRoute = route;

    let cancelled = false;
    let timeoutHandle: number | null = null;

    const failJourney = (error: unknown) => {
      const resetLoss = getJourneyResetLossState(error);
      setRoute((current) => {
        if (current.page !== "processing-journey" || current.jobId !== processingRoute.jobId) {
          return current;
        }
        return {
          ...current,
          journey: {
            ...current.journey,
            status: "error",
            stage: "error",
            progressPct: current.journey.progressPct,
            error: resetLoss?.error ?? getJourneyErrorMessage(error),
            message: resetLoss?.message ?? "Processing failed",
            stageHistory: current.journey.stageHistory.includes("error")
              ? current.journey.stageHistory
              : [...current.journey.stageHistory, "error"],
          },
        };
      });
    };

    const poll = async () => {
      let status;

      try {
        status = await getJobStatus(processingRoute.jobId);
      } catch (error) {
        if (cancelled) return;

        if (isTransientJourneyPollingError(error)) {
          timeoutHandle = window.setTimeout(() => {
            void poll();
          }, 1000);
          return;
        }

        failJourney(error);
        return;
      }

      try {
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

          const loadedBands = await refreshBands();
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

  const handleSongUpload = useCallback(async (
    band: Band,
    project: Project,
    file: File,
    processMode: ProcessMode,
    tabGenerationQuality: TabGenerationQuality,
  ) => {
    if (!user) return;
    setSongUploadLoading(true);
    setSongUploadStatus(null);
    setSongUploadWarning(null);
    setSongUploadError(null);

    try {
      const upload = await uploadAudio(file, processMode, tabGenerationQuality);
      const analysisResult = await pollUntilComplete(upload.job_id, (status) => {
        setSongUploadStatus({
          message: status.message ?? status.progress ?? "Processing...",
          progress_pct: status.progress_pct ?? 0,
          stage_progress_pct: status.stage_progress_pct ?? 0,
        });
        const warning = deriveStemWarning(status);
        if (warning) setSongUploadWarning(warning);
      });

      const refreshedBands = await loadBandHierarchy(user);
      setBands(refreshedBands);
      const refreshedBand = refreshedBands.find((candidate) => candidate.id === band.id) ?? band;
      const refreshedProject = refreshedBand.projects.find((candidate) => candidate.id === project.id) ?? project;
      const uploadedSongId = String(analysisResult.song_id ?? upload.song_id);
      const refreshedSong = refreshedProject.songs.find((candidate) => candidate.id === uploadedSongId)
        ?? mapProjectSongSummaryToSong({
          id: Number(uploadedSongId),
          project_id: Number(refreshedProject.id),
          title: file.name.replace(/\.[^.]+$/, "") || "Untitled",
          original_filename: file.name,
          created_at: new Date().toISOString(),
          key: analysisResult.key,
          tempo: analysisResult.tempo,
          duration: analysisResult.duration,
        });
      const detailedSong = await loadSongDetails(refreshedSong);
      setRoute({ page: "song-detail", band: refreshedBand, project: refreshedProject, song: detailedSong });
    } catch (error) {
      setSongUploadError(error instanceof Error ? error.message : "Upload failed");
    } finally {
      setSongUploadLoading(false);
    }
  }, [loadSongDetails, user]);

  const handleStemUpload = useCallback(async (
    band: Band,
    project: Project,
    song: Song,
    payload: { file: File; stemName: string; description: string },
  ) => {
    const songId = Number(song.id);
    if (Number.isNaN(songId)) return;
    setStemUploadLoading(true);
    setStemUploadError(null);
    try {
      await uploadSongStem(songId, payload);
      const refreshedSong = await loadSongDetails(song);
      setRoute({ page: "song-detail", band, project, song: refreshedSong });
    } catch (error) {
      setStemUploadError(error instanceof Error ? error.message : "Stem upload failed");
    } finally {
      setStemUploadLoading(false);
    }
  }, [loadSongDetails]);

  const handlePlaybackPrefsSave = useCallback(async (
    routeSong: Song,
    prefs: PlaybackPrefs,
  ) => {
    const songId = Number(routeSong.id);
    if (Number.isNaN(songId)) return;

    await savePlaybackPrefs(songId, prefs);
    const mappedPrefs = {
      speedPercent: prefs.speed_percent,
      volume: prefs.volume,
      loopStartIndex: prefs.loop_start_index,
      loopEndIndex: prefs.loop_end_index,
    };
    updateSongEverywhere(routeSong.id, (song) => ({ ...song, playbackPrefs: mappedPrefs }));
  }, [updateSongEverywhere]);

  const handleCreateNote = useCallback(async (
    routeSong: Song,
    payload: {
      type: "time" | "chord";
      text: string;
      timestamp_sec?: number;
      chord_index?: number;
    },
  ) => {
    if (!user) return;
    const songId = Number(routeSong.id);
    if (Number.isNaN(songId)) return;

    const created = await createSongNote(songId, payload);
    const mapped = mapNote(created, user);
    updateSongEverywhere(routeSong.id, (song) => ({
      ...song,
      notes: [...song.notes, mapped],
    }));
  }, [updateSongEverywhere, user]);

  const handleUpdateNote = useCallback(async (
    routeSong: Song,
    noteId: number,
    payload: { text?: string },
  ) => {
    await updateSongNote(noteId, payload);
    updateSongEverywhere(routeSong.id, (song) => ({
      ...song,
      notes: song.notes.map((note) => (
        note.id === noteId
          ? { ...note, text: payload.text ?? note.text }
          : note
      )),
    }));
  }, [updateSongEverywhere]);

  const handleDeleteNote = useCallback(async (
    routeSong: Song,
    noteId: number,
  ) => {
    await deleteSongNote(noteId);
    updateSongEverywhere(routeSong.id, (song) => ({
      ...song,
      notes: song.notes.filter((note) => note.id !== noteId),
    }));
  }, [updateSongEverywhere]);

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
            await refreshBands();
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
          onRenameBand={async (bandId, newName) => {
            await updateBand(Number(bandId), { name: newName });
            await refreshBands(showArchivedBands);
          }}
          onArchiveBand={async (bandId, archived) => {
            await updateBand(Number(bandId), { archived });
            await refreshBands(showArchivedBands);
          }}
          showArchived={showArchivedBands}
          onToggleShowArchived={() => {
            const next = !showArchivedBands;
            setShowArchivedBands(next);
            void refreshBands(next);
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
            const loadedBands = await refreshBands();
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
          onRenameProject={async (projectId, newName) => {
            await updateProject(Number(projectId), { name: newName });
            const loaded = await refreshBands(showArchivedBands);
            const refreshedBand = loaded?.find((b) => b.id === route.band.id);
            if (refreshedBand) setRoute((r) => r.page === "project" ? { ...r, band: refreshedBand } : r);
          }}
          onArchiveProject={async (projectId, archived) => {
            await updateProject(Number(projectId), { archived });
            const loaded = await refreshBands(showArchivedBands);
            const refreshedBand = loaded?.find((b) => b.id === route.band.id);
            if (refreshedBand) setRoute((r) => r.page === "project" ? { ...r, band: refreshedBand } : r);
          }}
          showArchivedProjects={showArchivedProjects}
          onToggleShowArchivedProjects={() => {
            const next = !showArchivedProjects;
            setShowArchivedProjects(next);
            void refreshBands(showArchivedBands);
          }}
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
          uploadLoading={songUploadLoading}
          uploadStatus={songUploadStatus}
          uploadWarning={songUploadWarning}
          uploadError={songUploadError}
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
      if (isJourneyResetLossError(route.journey.error)) {
        return (
          <div className="me-mesh min-h-screen" style={{ background: "linear-gradient(160deg, #0a0e27 0%, #111638 40%, #0a0e27 100%)" }}>
            <main className="mx-auto flex min-h-screen max-w-3xl items-center px-8 py-10">
              <section
                className="w-full border p-8"
                style={{ borderRadius: "4px", borderColor: "rgba(239, 68, 68, 0.25)", background: "rgba(255, 255, 255, 0.03)", backdropFilter: "blur(10px)" }}
              >
                <p className="text-xs font-semibold uppercase tracking-[0.22em]" style={{ color: "#fca5a5" }}>Processing Journey</p>
                <h1 className="mt-4 text-4xl" style={{ fontFamily: "Playfair Display, serif", color: "#e2e2f0" }}>
                  {route.journey.songTitle ?? route.uploadFilename}
                </h1>
                <p className="mt-2 text-sm" style={{ color: "#7a7a90" }}>{route.uploadFilename}</p>
                <p className="mt-6 text-base" style={{ color: "#fecaca" }}>{route.journey.message}</p>
                <p className="mt-3 text-sm" style={{ color: "#fca5a5" }}>{route.journey.error}</p>
                <div className="mt-8 flex flex-wrap gap-3">
                  <button
                    onClick={goBack}
                    className="border px-5 py-2.5 text-sm font-medium transition-all hover:bg-white/5"
                    style={{ borderRadius: "3px", borderColor: "rgba(192, 192, 192, 0.12)", color: "#c0c0c0" }}
                  >
                    Back to Library
                  </button>
                </div>
              </section>
            </main>
          </div>
        );
      }

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
          onUploadStem={(payload) => {
            void handleStemUpload(route.band, route.project, route.song, payload);
          }}
          uploadStemLoading={stemUploadLoading}
          uploadStemError={stemUploadError}
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
            await refreshProjectCollaboration(route.band.id, route.project.id);
          }}
          onUploadStem={async ({ stemKey, file }) => {
            const songId = Number(route.song.id);
            if (Number.isNaN(songId)) return;
            await uploadSongStem(songId, { stemKey, file });
            await refreshSongDetailRoute();
            await refreshProjectCollaboration(route.band.id, route.project.id);
          }}
          onGenerateBassTab={async (sourceStemKey) => {
            const songId = Number(route.song.id);
            if (Number.isNaN(songId)) return;
            await regenerateSongTabs(songId, { source_stem_key: sourceStemKey });
            await refreshSongDetailRoute();
          }}
          onCreateNote={async ({ text }: { type: "general"; text: string }) => {
            const songId = Number(route.song.id);
            if (Number.isNaN(songId)) return;
            await createSongNote(songId, { type: "general", text });
            await refreshSongDetailRoute();
          }}
          onCreateReply={async (parentId: number, text: string) => {
            const songId = Number(route.song.id);
            if (Number.isNaN(songId)) return;
            await createSongNote(songId, { type: "general", text, parent_id: parentId });
            await refreshSongDetailRoute();
          }}
          onEditNote={async (noteId, payload: { text: string; toastDurationSec?: number }) => {
            await updateSongNote(noteId, { text: payload.text, toast_duration_sec: payload.toastDurationSec });
            await refreshSongDetailRoute();
            await refreshProjectCollaboration(route.band.id, route.project.id);
          }}
          onResolveNote={async (noteId, resolved) => {
            await resolveSongNote(noteId, resolved);
            await refreshSongDetailRoute();
            await refreshProjectCollaboration(route.band.id, route.project.id);
          }}
          onDeleteNote={async (noteId) => {
            await deleteSongNote(noteId);
            await refreshSongDetailRoute();
            await refreshProjectCollaboration(route.band.id, route.project.id);
          }}
          onOpenPlayer={() => {
            void openPlayerForSong(route.band, route.project, route.song);
          }}
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
          onCreateNote={(payload) => {
            void handleCreateNote(route.song, payload);
          }}
          onUpdateNote={(noteId, payload) => {
            void handleUpdateNote(route.song, noteId, payload);
          }}
          onDeleteNote={(noteId) => {
            void handleDeleteNote(route.song, noteId);
          }}
          onSavePlaybackPrefs={(prefs) => {
            void handlePlaybackPrefsSave(route.song, prefs);
          }}
          onCreateNote={async ({ type, text, timestampSec, chordIndex, toastDurationSec }: {
            type: "time" | "chord";
            text: string;
            timestampSec?: number;
            chordIndex?: number;
            toastDurationSec?: number;
          }) => {
            const songId = Number(route.song.id);
            if (Number.isNaN(songId)) return;
            await createSongNote(songId, {
              type,
              text,
              timestamp_sec: timestampSec,
              chord_index: chordIndex,
              toast_duration_sec: toastDurationSec,
            });
            await refreshPlayerRoute();
            await refreshProjectCollaboration(route.band.id, route.project.id);
          }}
          onEditNote={async (noteId, payload: { text: string; toastDurationSec?: number }) => {
            await updateSongNote(noteId, { text: payload.text, toast_duration_sec: payload.toastDurationSec });
            await refreshPlayerRoute();
            await refreshProjectCollaboration(route.band.id, route.project.id);
          }}
          onResolveNote={async (noteId, resolved) => {
            await resolveSongNote(noteId, resolved);
            await refreshPlayerRoute();
            await refreshProjectCollaboration(route.band.id, route.project.id);
          }}
          onDeleteNote={async (noteId) => {
            await deleteSongNote(noteId);
            await refreshPlayerRoute();
            await refreshProjectCollaboration(route.band.id, route.project.id);
          }}
          currentUserId={identityUserId}
          onCreateReply={async (parentId: number, text: string) => {
            await createSongNote(parseInt(route.song.id), {
              type: "general",
              text,
              parent_id: parentId,
            });
            await refreshPlayerRoute();
            await refreshProjectCollaboration(route.band.id, route.project.id);
          }}
          onBack={goBack}
        />
      );
    default:
      return <LandingPage onGetStarted={() => setRoute({ page: "bands" })} onSignIn={() => setRoute({ page: "bands" })} />;
  }
}
