import { RefreshCw } from 'lucide-react';

const PAGE_TITLES = {
  dashboard:    'Market Dashboard',
  portfolio:    'My Portfolio',
  watchlist:    'Watchlist',
  fundamentals: 'Fundamental Analysis',
  assistant:    'AI Assistant',
  profile:      'My Profile',
};

const PAGE_SUBS = {
  dashboard:    'Real-time NSE/BSE stock data with technical analysis',
  portfolio:    'Track your holdings with live P&L',
  watchlist:    'Monitor stocks youre interested in',
  fundamentals: 'Deep financial metrics & sector comparisons',
  assistant:    'Powered by Gemini 2.5 Flash + LangGraph',
  profile:      'Manage your investor profile & preferences',
};

export default function Topbar({ page, onRefresh }) {
  return (
    <div className="topbar">
      <div style={{ flex:1 }}>
        <div style={{ fontFamily:'var(--font-display)', fontWeight:700, fontSize:17, lineHeight:1.2 }}>
          {PAGE_TITLES[page]}
        </div>
        <div style={{ fontSize:11, color:'var(--text-3)', marginTop:1 }}>
          {PAGE_SUBS[page]}
        </div>
      </div>
      <button className="btn-icon" onClick={onRefresh} title="Refresh page">
        <RefreshCw size={15}/>
      </button>
    </div>
  );
}
