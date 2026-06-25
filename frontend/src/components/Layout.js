import { NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { LayoutDashboard, TrendingUp, CalendarDays, FilePlus2, Users, LogOut, Activity } from "lucide-react";

const navItems = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, testid: "nav-dashboard", end: true },
  { to: "/trends", label: "Trends", icon: TrendingUp, testid: "nav-trends" },
  { to: "/meetings", label: "Meetings", icon: CalendarDays, testid: "nav-meetings" },
  { to: "/data-entry", label: "Data Entry", icon: FilePlus2, testid: "nav-data-entry", admin: true },
  { to: "/users", label: "Users", icon: Users, testid: "nav-users", admin: true },
];

export default function Layout({ children }) {
  const { user, isAdmin, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
    navigate("/login");
  };

  return (
    <div className="min-h-screen bg-background">
      <header className="sticky top-0 z-40 border-b border-border bg-white/80 backdrop-blur-xl">
        <div className="max-w-[1600px] mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex h-16 items-center justify-between gap-4">
            <div className="flex items-center gap-8">
              <div className="flex items-center gap-2.5" data-testid="app-logo">
                <div className="h-9 w-9 rounded-md bg-black flex items-center justify-center">
                  <Activity className="h-5 w-5 text-white" strokeWidth={2.5} />
                </div>
                <div className="leading-tight">
                  <div className="font-semibold tracking-tight text-[15px]">COLLECTIQ</div>
                  <div className="text-[10px] uppercase tracking-[0.2em] text-muted-foreground">Collection Intelligence</div>
                </div>
              </div>
              <nav className="hidden md:flex items-center gap-1">
                {navItems.filter((n) => !n.admin || isAdmin).map((n) => (
                  <NavLink
                    key={n.to}
                    to={n.to}
                    end={n.end}
                    data-testid={n.testid}
                    className={({ isActive }) =>
                      `flex items-center gap-2 px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                        isActive ? "bg-black text-white" : "text-muted-foreground hover:bg-secondary hover:text-foreground"
                      }`
                    }
                  >
                    <n.icon className="h-4 w-4" />
                    {n.label}
                  </NavLink>
                ))}
              </nav>
            </div>
            <div className="flex items-center gap-3">
              <div className="hidden sm:flex flex-col items-end leading-tight">
                <span className="text-sm font-medium" data-testid="current-user-name">{user?.name}</span>
                <span className="text-[11px] text-muted-foreground">{user?.email}</span>
              </div>
              <Badge
                variant="outline"
                className={`uppercase text-[10px] tracking-wider ${isAdmin ? "border-black text-black" : "border-border text-muted-foreground"}`}
                data-testid="role-badge"
              >
                {user?.role}
              </Badge>
              <Button variant="ghost" size="icon" onClick={handleLogout} data-testid="logout-button" title="Log out">
                <LogOut className="h-4 w-4" />
              </Button>
            </div>
          </div>
          {/* mobile nav */}
          <nav className="md:hidden flex items-center gap-1 overflow-x-auto pb-2">
            {navItems.filter((n) => !n.admin || isAdmin).map((n) => (
              <NavLink
                key={n.to}
                to={n.to}
                end={n.end}
                className={({ isActive }) =>
                  `flex items-center gap-1.5 px-2.5 py-1.5 rounded-md text-xs font-medium whitespace-nowrap ${
                    isActive ? "bg-black text-white" : "text-muted-foreground bg-secondary"
                  }`
                }
              >
                <n.icon className="h-3.5 w-3.5" />
                {n.label}
              </NavLink>
            ))}
          </nav>
        </div>
      </header>
      <main className="max-w-[1600px] mx-auto px-4 sm:px-6 lg:px-8 py-8">{children}</main>
    </div>
  );
}
