import { useEffect, useState } from 'react';
import { LayoutDashboard, Briefcase, Star, BarChart2, Bot, User, TrendingUp } from 'lucide-react';
import { getMarketStatus } from '../api';

const NAV = [
  { id: 'dashboard',    label: 'Dashboard',    icon: LayoutDashboard },
  { id: 'portfolio',    label: 'Portfolio',    icon: Briefcase },
  { id: 'watchlist',   label: 'Watchlist',    icon: Star },
  { id: 'fundamentals',label: 'Fundamentals', icon: BarChart2 },
  { id: 'assistant',   label: 'AI Assistant', icon: Bot },
  { id: 'profile',     label: 'Profile',      icon: User },
];

export default function Sidebar({ active, onNav, profile }) {
  const [market, setMarket] = useState(null);
  const [time, setTime]     = useState(new Date());

  useEffect(() => {
    getMarketStatus().then(setMarket).catch(() => {});
    const t = setInterval(() => {
      setTime(new Date());
      getMarketStatus().then(setMarket).catch(() => {});
    }, 30000);
    return () => clearInterval(t);
  }, []);

  const ist = time.toLocaleString('en-IN', { timeZone: 'Asia/Kolkata', hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: true });
  const date = time.toLocaleDateString('en-IN', { timeZone: 'Asia/Kolkata', day: '2-digit', month: 'short', year: 'numeric' });

  const initials = (profile?.name || 'IN').split(' ').map(w => w[0]).join('').slice(0,2).toUpperCase();
  const avatarColor = profile?.avatar_color || '#00d296';

  return (
    <aside className="sidebar">
      <div className="sidebar-logo">
        <div className="flex items-center gap-8 mb-8">
          <TrendingUp size={22} color="var(--accent)" />
          <h1>Fin<span>AI</span></h1>
        </div>
        {market && (
          <div className={`market-badge ${market.is_open ? 'open' : 'closed'}`}>
            <span className="dot"/>
            NSE/BSE {market.is_open ? 'OPEN' : 'CLOSED'}
          </div>
        )}
      </div>

      <nav className="sidebar-nav">
        <ul>
          {NAV.map(({ id, label, icon: Icon }) => (
            <li key={id}>
              <div className={`nav-item ${active === id ? 'active' : ''}`} onClick={() => onNav(id)}>
                <Icon size={17} />
                {label}
              </div>
            </li>
          ))}
        </ul>
      </nav>

      {/* Profile quick-view */}
      <div
        className="flex items-center gap-8 cursor-pointer"
        style={{ padding: '14px 20px', borderTop: '1px solid var(--border)', borderBottom: '1px solid var(--border)' }}
        onClick={() => onNav('profile')}
      >
        <div className="avatar-sm" style={{ background: avatarColor }}>{initials}</div>
        <div>
          <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-1)', lineHeight: 1.2 }}>{profile?.name || 'Investor'}</div>
          <div style={{ fontSize: 11, color: 'var(--text-3)', fontFamily: 'var(--font-mono)' }}>{profile?.risk_profile || 'Moderate'}</div>
        </div>
      </div>

      <div className="sidebar-time">
        <div style={{ color: 'var(--text-2)', fontWeight: 500 }}>{ist}</div>
        <div>{date} IST</div>
        {market && <div style={{ marginTop: 4 }}>Mkt: {market.open_time} – {market.close_time}</div>}
      </div>
    </aside>
  );
}
