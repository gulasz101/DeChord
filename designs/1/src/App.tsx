import { useState, useCallback } from "react";
import type { Band, Project, Song, User } from "./lib/types";
import { MOCK_BANDS, MOCK_USER } from "./lib/mockData";
import { LandingPage } from "./pages/LandingPage";
import { AuthPage } from "./pages/AuthPage";
import { BandSelectPage } from "./pages/BandSelectPage";
import { ProjectHomePage } from "./pages/ProjectHomePage";
import { SongLibraryPage } from "./pages/SongLibraryPage";
import { SongDetailPage } from "./pages/SongDetailPage";
import { PlayerPage } from "./pages/PlayerPage";

type Route =
  | { page: "landing" }
  | { page: "auth"; mode: "signin" | "register" | "invite" }
  | { page: "bands" }
  | { page: "project"; band: Band; project: Project }
  | { page: "songs"; band: Band; project: Project }
  | { page: "song-detail"; band: Band; project: Project; song: Song }
  | { page: "player"; band: Band; project: Project; song: Song };

export default function App() {
  const [route, setRoute] = useState<Route>({ page: "landing" });
  const [user, setUser] = useState<User | null>(null);

  const navigate = useCallback((r: Route) => setRoute(r), []);

  const handleAuth = useCallback(() => {
    setUser(MOCK_USER);
    navigate({ page: "bands" });
  }, [navigate]);

  const goBack = useCallback(() => {
    switch (route.page) {
      case "auth": navigate({ page: "landing" }); break;
      case "bands": navigate({ page: "landing" }); break;
      case "project": navigate({ page: "bands" }); break;
      case "songs": {
        const r = route as Extract<Route, { page: "songs" }>;
        navigate({ page: "project", band: r.band, project: r.project });
        break;
      }
      case "song-detail": {
        const r = route as Extract<Route, { page: "song-detail" }>;
        navigate({ page: "songs", band: r.band, project: r.project });
        break;
      }
      case "player": {
        const r = route as Extract<Route, { page: "player" }>;
        navigate({ page: "song-detail", band: r.band, project: r.project, song: r.song });
        break;
      }
    }
  }, [route, navigate]);

  switch (route.page) {
    case "landing":
      return <LandingPage onGetStarted={() => navigate({ page: "auth", mode: "register" })} onSignIn={() => navigate({ page: "auth", mode: "signin" })} />;
    case "auth":
      return <AuthPage mode={route.mode} onComplete={handleAuth} onBack={goBack} />;
    case "bands":
      return <BandSelectPage user={user!} bands={MOCK_BANDS} onSelectBand={(band) => navigate({ page: "project", band, project: band.projects[0] })} onSignOut={() => { setUser(null); navigate({ page: "landing" }); }} />;
    case "project":
      return <ProjectHomePage user={user!} band={route.band} project={route.project} onSelectProject={(p) => navigate({ page: "project", band: route.band, project: p })} onOpenSongs={() => navigate({ page: "songs", band: route.band, project: route.project })} onBack={goBack} />;
    case "songs":
      return <SongLibraryPage user={user!} band={route.band} project={route.project} onSelectSong={(s) => navigate({ page: "song-detail", band: route.band, project: route.project, song: s })} onBack={goBack} />;
    case "song-detail":
      return <SongDetailPage user={user!} band={route.band} project={route.project} song={route.song} onOpenPlayer={() => navigate({ page: "player", band: route.band, project: route.project, song: route.song })} onBack={goBack} />;
    case "player":
      return <PlayerPage user={user!} band={route.band} project={route.project} song={route.song} onBack={goBack} />;
  }
}
