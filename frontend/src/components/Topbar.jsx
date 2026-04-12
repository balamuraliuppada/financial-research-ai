import { useState, useEffect, useRef } from 'react';
import { RefreshCw, Bell } from 'lucide-react';
import { getUnreadCount, getNotifications, markRead } from '../api';

const PAGE_TITLES = {
  dashboard: 'Stock Dashboard',
  portfolio: 'Portfolio',
  optimizer: 'Portfolio Optimizer',
  watchlist: 'Watchlist',
  fundamentals: 'Fundamentals & Sectors',
  signals: 'Trading Signals',
  multiasset: 'Multi-Asset Analysis',
  options: 'Options Pricing',
  alerts: 'Market Alerts',
  assistant: 'AI Assistant',
  profile: 'Your Profile',
};

export default function Topbar({ page, onRefresh }) {
  const [unread, setUnread] = useState(0);
  const [showNotifs, setShowNotifs] = useState(false);
  const [notifications, setNotifications] = useState([]);
  const notifRef = useRef(null);

  useEffect(() => {
    const fetchUnread = () => {
      getUnreadCount().then(setUnread).catch(() => {});
    };
    fetchUnread();
    const interval = setInterval(fetchUnread, 30000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    const handleClickOutside = (e) => {
      if (notifRef.current && !notifRef.current.contains(e.target)) {
        setShowNotifs(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const openNotifs = async () => {
    setShowNotifs(!showNotifs);
    if (!showNotifs) {
      try {
        const data = await getNotifications(false);
        setNotifications(data.slice(0, 10));
      } catch (e) { console.error(e); }
    }
  };

  const handleMarkRead = async (id) => {
    try {
      await markRead(id);
      setNotifications(prev => prev.map(n => n.id === id ? { ...n, is_read: true } : n));
      setUnread(prev => Math.max(0, prev - 1));
    } catch (e) { console.error(e); }
  };

  return (
    <header className="topbar">
      <h1 className="topbar-title">{PAGE_TITLES[page] || 'Dashboard'}</h1>
      <div className="topbar-actions">
        {/* Notification Bell */}
        <div className="notif-wrapper" ref={notifRef}>
          <button className="icon-btn notif-btn" onClick={openNotifs} title="Notifications">
            <Bell size={18} />
            {unread > 0 && <span className="notif-badge">{unread > 9 ? '9+' : unread}</span>}
          </button>

          {showNotifs && (
            <div className="notif-dropdown">
              <div className="notif-header">Notifications</div>
              {notifications.length === 0 ? (
                <div className="notif-empty">No notifications</div>
              ) : (
                notifications.map(n => (
                  <div key={n.id} className={`notif-item ${n.is_read ? 'read' : 'unread'}`}>
                    <div className="notif-msg">{n.message}</div>
                    <div className="notif-footer">
                      <span className="notif-time">{new Date(n.created_at).toLocaleString()}</span>
                      {!n.is_read && (
                        <button className="notif-mark" onClick={() => handleMarkRead(n.id)}>✓</button>
                      )}
                    </div>
                  </div>
                ))
              )}
            </div>
          )}
        </div>

        <button className="icon-btn" onClick={onRefresh} title="Refresh">
          <RefreshCw size={16} />
        </button>
      </div>
    </header>
  );
}
