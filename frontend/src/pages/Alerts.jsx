import { useState, useEffect, useRef } from 'react';
import { createAlert, getAlerts, deleteAlert, toggleAlert, getNotifications, markRead, getUnreadCount } from '../api';

const ALERT_TYPES = [
  { value: 'price_above', label: '📈 Price Above', desc: 'Triggers when price crosses above threshold' },
  { value: 'price_below', label: '📉 Price Below', desc: 'Triggers when price drops below threshold' },
  { value: 'rsi_overbought', label: '🔴 RSI Overbought', desc: 'Triggers when RSI exceeds threshold (default 70)' },
  { value: 'rsi_oversold', label: '🟢 RSI Oversold', desc: 'Triggers when RSI drops below threshold (default 30)' },
  { value: 'volume_spike', label: '📊 Volume Spike', desc: 'Triggers at N× average volume (default 2×)' },
  { value: 'ma_crossover', label: '✖️ MA Crossover', desc: 'Triggers on 20/50 MA golden or death cross' },
  { value: 'bollinger_breakout', label: '💥 Bollinger Breakout', desc: 'Triggers when price breaks Bollinger Bands' },
  { value: 'percent_change', label: '📢 % Change', desc: 'Triggers on daily move exceeding threshold %' },
];

export default function Alerts({ stockList }) {
  const [alerts, setAlerts] = useState([]);
  const [notifications, setNotifications] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [tab, setTab] = useState('alerts');

  // Form state
  const [symbol, setSymbol] = useState('');
  const [alertType, setAlertType] = useState('price_above');
  const [threshold, setThreshold] = useState('');
  const [condition, setCondition] = useState('');
  const [creating, setCreating] = useState(false);

  const fetchAlerts = async () => {
    try {
      const data = await getAlerts();
      setAlerts(data);
    } catch (e) { console.error(e); }
  };

  const fetchNotifications = async () => {
    try {
      const data = await getNotifications();
      setNotifications(data);
    } catch (e) { console.error(e); }
  };

  useEffect(() => {
    Promise.all([fetchAlerts(), fetchNotifications()]).finally(() => setLoading(false));
  }, []);

  const handleCreate = async () => {
    if (!symbol) return;
    setCreating(true);
    try {
      await createAlert({
        symbol: symbol.toUpperCase(),
        alert_type: alertType,
        threshold: threshold ? parseFloat(threshold) : null,
        condition,
      });
      setShowForm(false);
      setSymbol(''); setThreshold(''); setCondition('');
      fetchAlerts();
    } catch (e) {
      alert('Failed to create alert: ' + (e.response?.data?.detail || e.message));
    } finally {
      setCreating(false);
    }
  };

  const handleDelete = async (id) => {
    try { await deleteAlert(id); fetchAlerts(); } catch (e) { console.error(e); }
  };

  const handleToggle = async (id) => {
    try { await toggleAlert(id); fetchAlerts(); } catch (e) { console.error(e); }
  };

  const handleMarkRead = async (id) => {
    try { await markRead(id); fetchNotifications(); } catch (e) { console.error(e); }
  };

  const activeAlerts = alerts.filter(a => a.status === 'active');
  const triggeredAlerts = alerts.filter(a => a.status === 'triggered');
  const disabledAlerts = alerts.filter(a => a.status === 'disabled');

  if (loading) return <div className="loading-state"><div className="loading-spinner"></div><p>Loading alerts...</p></div>;

  return (
    <div className="alerts-page">
      <div className="page-header-row">
        <div>
          <h2>🔔 Market Alerts</h2>
          <p className="page-subtitle">Set price alerts, RSI levels, volume spikes, and pattern triggers</p>
        </div>
        <button className="btn-primary" onClick={() => setShowForm(!showForm)}>
          {showForm ? '✕ Cancel' : '➕ New Alert'}
        </button>
      </div>

      {/* Create Alert Form */}
      {showForm && (
        <div className="card alert-form">
          <h3>Create Alert</h3>
          <div className="form-grid">
            <div>
              <label className="field-label">Symbol</label>
              <input type="text" placeholder="e.g. RELIANCE.NS" value={symbol}
                     onChange={e => setSymbol(e.target.value)} className="text-input" />
            </div>
            <div>
              <label className="field-label">Alert Type</label>
              <select value={alertType} onChange={e => setAlertType(e.target.value)} className="select-input">
                {ALERT_TYPES.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
              </select>
              <div className="field-hint">{ALERT_TYPES.find(t => t.value === alertType)?.desc}</div>
            </div>
            <div>
              <label className="field-label">Threshold</label>
              <input type="number" step="0.01" placeholder="e.g. 2500" value={threshold}
                     onChange={e => setThreshold(e.target.value)} className="number-input" />
            </div>
            <div>
              <label className="field-label">Note (optional)</label>
              <input type="text" placeholder="Reminder note" value={condition}
                     onChange={e => setCondition(e.target.value)} className="text-input" />
            </div>
          </div>
          <button className="btn-primary" onClick={handleCreate} disabled={creating || !symbol}>
            {creating ? '⏳ Creating...' : '✅ Create Alert'}
          </button>
        </div>
      )}

      {/* Tabs */}
      <div className="tab-row">
        <button className={`tab-btn ${tab === 'alerts' ? 'active' : ''}`} onClick={() => setTab('alerts')}>
          Alerts ({alerts.length})
        </button>
        <button className={`tab-btn ${tab === 'notifications' ? 'active' : ''}`} onClick={() => setTab('notifications')}>
          Notifications ({notifications.filter(n => !n.is_read).length} new)
        </button>
      </div>

      {tab === 'alerts' && (
        <div className="alerts-sections">
          {/* Active */}
          {activeAlerts.length > 0 && (
            <div className="alert-section">
              <h3 className="section-title">🟢 Active ({activeAlerts.length})</h3>
              {activeAlerts.map(a => (
                <div key={a.id} className="alert-card active">
                  <div className="alert-info">
                    <span className="alert-symbol">{a.symbol}</span>
                    <span className="alert-type-badge">{ALERT_TYPES.find(t => t.value === a.alert_type)?.label || a.alert_type}</span>
                    {a.threshold && <span className="alert-threshold">@ {a.threshold}</span>}
                    {a.condition && <span className="alert-note">{a.condition}</span>}
                  </div>
                  <div className="alert-actions">
                    <button className="btn-sm btn-warning" onClick={() => handleToggle(a.id)}>⏸ Pause</button>
                    <button className="btn-sm btn-danger" onClick={() => handleDelete(a.id)}>🗑</button>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Triggered */}
          {triggeredAlerts.length > 0 && (
            <div className="alert-section">
              <h3 className="section-title">⚡ Triggered ({triggeredAlerts.length})</h3>
              {triggeredAlerts.map(a => (
                <div key={a.id} className="alert-card triggered">
                  <div className="alert-info">
                    <span className="alert-symbol">{a.symbol}</span>
                    <span className="alert-type-badge">{a.alert_type}</span>
                    <span className="alert-triggered-val">Value: {a.triggered_value}</span>
                    <span className="alert-time">{a.triggered_at && new Date(a.triggered_at).toLocaleString()}</span>
                  </div>
                  <div className="alert-actions">
                    <button className="btn-sm btn-primary" onClick={() => handleToggle(a.id)}>🔄 Reactivate</button>
                    <button className="btn-sm btn-danger" onClick={() => handleDelete(a.id)}>🗑</button>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Disabled */}
          {disabledAlerts.length > 0 && (
            <div className="alert-section">
              <h3 className="section-title">⏸ Paused ({disabledAlerts.length})</h3>
              {disabledAlerts.map(a => (
                <div key={a.id} className="alert-card disabled">
                  <div className="alert-info">
                    <span className="alert-symbol">{a.symbol}</span>
                    <span className="alert-type-badge">{a.alert_type}</span>
                    {a.threshold && <span className="alert-threshold">@ {a.threshold}</span>}
                  </div>
                  <div className="alert-actions">
                    <button className="btn-sm btn-primary" onClick={() => handleToggle(a.id)}>▶ Resume</button>
                    <button className="btn-sm btn-danger" onClick={() => handleDelete(a.id)}>🗑</button>
                  </div>
                </div>
              ))}
            </div>
          )}

          {alerts.length === 0 && (
            <div className="card empty-state">
              <div className="empty-icon">🔔</div>
              <h3>No alerts yet</h3>
              <p>Create your first alert to get notified about price movements and signals</p>
            </div>
          )}
        </div>
      )}

      {tab === 'notifications' && (
        <div className="notifications-list">
          {notifications.length === 0 ? (
            <div className="card empty-state">
              <div className="empty-icon">📭</div>
              <h3>No notifications</h3>
              <p>Triggered alerts will appear here</p>
            </div>
          ) : (
            notifications.map(n => (
              <div key={n.id} className={`notification-card ${n.is_read ? 'read' : 'unread'}`}>
                <div className="notif-message">{n.message}</div>
                <div className="notif-meta">
                  <span className="notif-time">{new Date(n.created_at).toLocaleString()}</span>
                  {!n.is_read && (
                    <button className="btn-sm btn-primary" onClick={() => handleMarkRead(n.id)}>Mark Read</button>
                  )}
                </div>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}
