import {
  Bell,
  Boxes,
  ChevronDown,
  FileText,
  Home,
  Menu,
  MessageSquare,
  Play,
  Search,
  Settings,
  Sparkles,
  X,
} from "lucide-react";
import { useState } from "react";
import { NavLink, Route, Routes, useLocation, useNavigate } from "react-router-dom";

import { CapabilitiesPage } from "./pages/CapabilitiesPage";
import { DiscoverPage } from "./pages/DiscoverPage";
import { HomePage } from "./pages/HomePage";
import { InterventionsPage } from "./pages/InterventionsPage";
import { RunsPage } from "./pages/RunsPage";
import { EvidencePage, SessionsPage, SettingsPage, TeachPage } from "./pages/UtilityPages";

const navigation = [
  { label: "Home", to: "/", icon: Home },
  { label: "Discover", to: "/discover", icon: Search },
  { label: "Runs", to: "/runs", icon: Play },
  { label: "Capabilities", to: "/capabilities", icon: Boxes },
  { label: "Sessions", to: "/sessions", icon: MessageSquare },
  { label: "Evidence", to: "/evidence", icon: FileText },
  { label: "Settings", to: "/settings", icon: Settings },
] as const;

const routeTitles: Record<string, string> = {
  "/": "Home",
  "/discover": "Discover",
  "/runs": "Runs",
  "/capabilities": "Capabilities",
  "/sessions": "Sessions",
  "/evidence": "Evidence",
  "/settings": "Settings",
  "/teach": "Teach",
};

function Logo() {
  return (
    <NavLink className="brand" to="/" aria-label="Capability Runner home">
      <span className="brand-mark" aria-hidden="true">
        <span />
      </span>
      <span>Capability<br />Runner</span>
    </NavLink>
  );
}

function Shell() {
  const [menuOpen, setMenuOpen] = useState(false);
  const [search, setSearch] = useState("");
  const location = useLocation();
  const navigate = useNavigate();
  const detailUsesHome = /^\/runs\/.+/.test(location.pathname) || location.pathname.startsWith("/interventions/");
  const exactTitle = routeTitles[location.pathname];
  const title = exactTitle ?? (location.pathname.startsWith("/capabilities") ? "Capabilities" : location.pathname.startsWith("/runs") || location.pathname.startsWith("/interventions") ? "Home" : "Capability Runner");

  return (
    <div className="app-shell">
      <aside className={menuOpen ? "sidebar sidebar-open" : "sidebar"}>
        <div className="sidebar-head">
          <Logo />
          <button className="icon-button mobile-only" type="button" onClick={() => setMenuOpen(false)} aria-label="Close navigation">
            <X size={20} />
          </button>
        </div>
        <nav className="primary-nav" aria-label="Primary navigation">
          {navigation.map(({ label, to, icon: Icon }) => (
            <NavLink key={to} to={to} end={to === "/"} className={({ isActive }) => ((to === "/" && (isActive || detailUsesHome)) || (to !== "/" && isActive && !detailUsesHome)) ? "active" : ""} onClick={() => setMenuOpen(false)}>
              <Icon size={21} strokeWidth={2} />
              <span>{label}</span>
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-motto">
          <Sparkles size={25} />
          <p>Automate<br />a more capable<br />enterprise.</p>
        </div>
      </aside>

      {menuOpen && <button className="scrim" type="button" aria-label="Close navigation" onClick={() => setMenuOpen(false)} />}

      <div className="workspace">
        <header className="topbar">
          <button className="icon-button mobile-only menu-button" type="button" onClick={() => setMenuOpen(true)} aria-label="Open navigation">
            <Menu size={21} />
          </button>
          <h1>{title}</h1>
          <form className="global-search" onSubmit={(event) => { event.preventDefault(); navigate(`/capabilities?query=${encodeURIComponent(search)}`); }}>
            <Search size={18} aria-hidden="true" />
            <span className="sr-only">Search</span>
            <input type="search" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search capabilities, runs, or anything..." />
          </form>
          <button className="notification-button" type="button" aria-label="Notifications">
            <Bell size={21} />
            <span />
          </button>
          <div className="profile">
            <span className="avatar">J</span>
            <span className="profile-copy"><strong>Local Operator</strong><small>Reviewer</small></span>
            <ChevronDown size={17} />
          </div>
        </header>
        <main className="page-canvas">
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/discover" element={<DiscoverPage />} />
            <Route path="/capabilities" element={<CapabilitiesPage />} />
            <Route path="/capabilities/:capabilityId" element={<CapabilitiesPage />} />
            <Route path="/runs" element={<RunsPage />} />
            <Route path="/runs/:runId" element={<RunsPage />} />
            <Route path="/interventions" element={<InterventionsPage />} />
            <Route path="/interventions/:interventionId" element={<InterventionsPage />} />
            <Route path="/teach" element={<TeachPage />} />
            <Route path="/sessions" element={<SessionsPage />} />
            <Route path="/evidence" element={<EvidencePage />} />
            <Route path="/settings" element={<SettingsPage />} />
            <Route path="*" element={<NotFoundPage />} />
          </Routes>
        </main>
      </div>
    </div>
  );
}

function NotFoundPage() {
  return <section className="panel placeholder page-enter"><div className="action-icon"><Boxes size={28} /></div><h2>Page not found</h2><p>The requested product route does not exist.</p></section>;
}

export function App() {
  return <Shell />;
}