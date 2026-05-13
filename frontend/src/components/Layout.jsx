import React, { useEffect } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { 
  LayoutDashboard, 
  Search, 
  CheckSquare, 
  Send, 
  MessageSquare, 
  User as UserIcon,
  Circle,
  AlertTriangle
} from 'lucide-react';
import { useProfile } from '../hooks/useProfile';
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

function cn(...inputs) {
  return twMerge(clsx(inputs));
}

const SidebarItem = ({ to, icon: Icon, label, active }) => (
  <Link
    to={to}
    className={cn(
      "flex items-center gap-3 px-4 py-3 rounded-lg transition-all duration-200 group",
      active 
        ? "bg-[#6C63FF]/10 text-[#6C63FF]" 
        : "text-zinc-400 hover:text-white hover:bg-zinc-800/50"
    )}
  >
    <Icon className={cn("w-5 h-5", active ? "text-[#6C63FF]" : "text-zinc-500 group-hover:text-zinc-300")} />
    <span className="font-medium text-sm">{label}</span>
    {active && <Circle className="w-1.5 h-1.5 fill-[#6C63FF] text-[#6C63FF] ml-auto" />}
  </Link>
);

const Layout = ({ children }) => {
  const location = useLocation();
  const navigate = useNavigate();
  const { profile, completenessScore, missingFields, loading } = useProfile();
  
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (['INPUT', 'TEXTAREA'].includes(e.target.tagName)) return;
      const key = e.key.toLowerCase();
      if (key === 'd') navigate('/discover');
      if (key === 'r') navigate('/review');
      if (key === 'a') navigate('/apply');
      if (key === 'i') navigate('/interview');
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [navigate]);

  const navItems = [
    { to: "/", icon: LayoutDashboard, label: "Dashboard" },
    { to: "/discover", icon: Search, label: "Discovery" },
    { to: "/review", icon: CheckSquare, label: "Review" },
    { to: "/apply", icon: Send, label: "Apply" },
    { to: "/interview", icon: MessageSquare, label: "Interview" },
  ];

  return (
    <div className="flex h-screen bg-[#0A0A0B] text-zinc-100 font-sans selection:bg-[#6C63FF]/30">
      {/* Sidebar */}
      <aside className="w-64 border-r border-zinc-800/50 flex flex-col bg-[#0D0D0E]">
        <div className="p-6 flex items-center gap-3">
          <div className="w-8 h-8 rounded bg-[#6C63FF] flex items-center justify-center">
            <Send className="w-5 h-5 text-white" />
          </div>
          <span className="font-bold text-xl tracking-tight text-white">AutoApply</span>
        </div>

        <nav className="flex-1 px-3 py-4 flex flex-col gap-1">
          {navItems.map((item) => (
            <SidebarItem 
              key={item.to} 
              {...item} 
              active={location.pathname === item.to || (item.to !== "/" && location.pathname.startsWith(item.to))} 
            />
          ))}
        </nav>

        <div className="p-4 border-t border-zinc-800/50">
          <div className="flex items-center gap-3 p-3 rounded-xl bg-zinc-900/50 border border-zinc-800/30">
            <div className="w-10 h-10 rounded-full bg-zinc-800 flex items-center justify-center border border-zinc-700">
              <UserIcon className="w-5 h-5 text-zinc-400" />
            </div>
            <div className="flex flex-col min-w-0">
              <span className="text-sm font-semibold text-white truncate">
                {loading ? "Loading..." : profile?.personal_info?.full_name || "Zied Cherif"}
              </span>
              <div className="flex items-center gap-2">
                <div className="flex-1 h-1 bg-zinc-800 rounded-full overflow-hidden">
                  <div 
                    className="h-full bg-[#6C63FF] transition-all duration-1000" 
                    style={{ width: `${completenessScore}%` }} 
                  />
                </div>
                <span className="text-[10px] font-mono text-zinc-500">{completenessScore}%</span>
              </div>
            </div>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <div className="flex-1 flex flex-col min-w-0">
        
        {completenessScore !== null && completenessScore < 70 && !loading && (
          <div className="bg-amber-500/10 border-b border-amber-500/20 px-6 py-3 flex items-center justify-between shrink-0">
             <div className="flex items-center gap-3">
                <AlertTriangle className="w-5 h-5 text-amber-500" />
                <p className="text-sm text-amber-200">
                  <span className="font-bold">Wait! Your profile is incomplete.</span> Better base data equals dramatically better performance. You are missing {missingFields?.length || 5}+ fields.
                </p>
             </div>
             <button onClick={() => navigate('/')} className="text-sm font-bold text-amber-400 hover:text-amber-300 hover:underline">Complete it now →</button>
          </div>
        )}

        <header className="h-16 border-b border-zinc-800/50 flex items-center justify-between px-8 bg-[#0D0D0E]/50 backdrop-blur-xl">
          <div className="text-zinc-500 font-mono text-xs uppercase tracking-widest">
            {new Date().toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}
          </div>
          <div className="flex items-center gap-4">
            <div className="px-3 py-1 rounded-full bg-green-500/10 border border-green-500/20 text-green-500 text-[10px] font-bold uppercase tracking-wider">
              System Live
            </div>
          </div>
        </header>

        <main className="flex-1 overflow-y-auto p-8 custom-scrollbar">
          <div className="max-w-6xl mx-auto">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
};

export default Layout;
