import { BarChart3, Briefcase, Star, Microscope, Bot, User, TrendingUp, Bell, Globe, Calculator, Target } from 'lucide-react';

const NAV_ITEMS = [
  { id: 'dashboard',    icon: BarChart3,   label: 'Dashboard' },
  { id: 'portfolio',    icon: Briefcase,   label: 'Portfolio' },
  { id: 'optimizer',    icon: TrendingUp,  label: 'Optimizer' },
  { id: 'watchlist',    icon: Star,        label: 'Watchlist' },
  { id: 'fundamentals', icon: Microscope,  label: 'Fundamentals' },
  { id: 'signals',      icon: Target,      label: 'Signals' },
  { id: 'multiasset',   icon: Globe,       label: 'Multi-Asset' },
  { id: 'options',      icon: Calculator,  label: 'Options' },
  { id: 'alerts',       icon: Bell,        label: 'Alerts' },
  { id: 'assistant',    icon: Bot,         label: 'AI Assistant' },
  { id: 'profile',      icon: User,        label: 'Profile' },
];

export default function Sidebar({ active, onNav, profile }) {
  const initials = (profile?.name || 'I').charAt(0).toUpperCase();
  const avatarColor = profile?.avatar_color || '#00c896';

  return (
    <aside className="sidebar">
      {/* Brand */}
      <div className="sidebar-brand" onClick={() => onNav('dashboard')}>
        <span className="brand-icon">📈</span>
        <span className="brand-text">FinAI</span>
      </div>

      {/* Nav */}
      <nav className="sidebar-nav">
        {NAV_ITEMS.map(item => {
          const Icon = item.icon;
          return (
            <button
              key={item.id}
              className={`nav-item ${active === item.id ? 'active' : ''}`}
              onClick={() => onNav(item.id)}
              title={item.label}
            >
              <Icon size={18} />
              <span className="nav-label">{item.label}</span>
            </button>
          );
        })}
      </nav>

      {/* Profile Preview */}
      <div className="sidebar-footer" onClick={() => onNav('profile')}>
        <div className="avatar-sm" style={{ background: avatarColor }}>
          {initials}
        </div>
        <div className="footer-info">
          <div className="footer-name">{profile?.name || 'Investor'}</div>
          <div className="footer-role">{profile?.risk_profile || 'Moderate'}</div>
        </div>
      </div>
    </aside>
  );
}
