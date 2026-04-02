import { useState, useEffect, useCallback } from 'react';
import { Plus, Trash2, RefreshCw, TrendingUp, TrendingDown, Briefcase } from 'lucide-react';
import { getPortfolio, addPortfolio, removePortfolio, getStockList } from '../api';
import { useToast } from '../context/ToastContext';

export default function Portfolio({ stockList }) {
  const toast = useToast();
  const [items, setItems]     = useState([]);
  const [loading, setLoading] = useState(false);
  const [symbol, setSymbol]   = useState('');
  const [adding, setAdding]   = useState(false);
  const [filter, setFilter]   = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    try { setItems(await getPortfolio()); }
    catch { toast('Failed to load portfolio', 'error'); }
    finally { setLoading(false); }
  }, [toast]);

  useEffect(() => { load(); }, [load]);

  const handleAdd = async () => {
    const sym = symbol.trim().toUpperCase();
    if (!sym) return;
    setAdding(true);
    try {
      await addPortfolio(sym);
      setSymbol('');
      toast(`${sym} added to portfolio`);
      load();
    } catch { toast('Failed to add stock', 'error'); }
    finally { setAdding(false); }
  };

  const handleRemove = async (sym) => {
    try {
      await removePortfolio(sym);
      toast(`${sym} removed`);
      setItems(p => p.filter(i => i.symbol !== sym));
    } catch { toast('Failed to remove', 'error'); }
  };

  const filtered = items.filter(i =>
    i.symbol.toLowerCase().includes(filter.toLowerCase()) ||
    i.name.toLowerCase().includes(filter.toLowerCase()) ||
    i.sector.toLowerCase().includes(filter.toLowerCase())
  );

  const totalChange = items.reduce((s, i) => s + (i.change || 0), 0);
  const gainers = items.filter(i => i.change_pct > 0);
  const losers  = items.filter(i => i.change_pct < 0);

  return (
    <div>
      {/* Stats */}
      <div className="grid-4 mb-20 fade-up">
        <div className="metric-card">
          <div className="label">Total Holdings</div>
          <div className="value">{items.length}</div>
        </div>
        <div className="metric-card">
          <div className="label">Gainers Today</div>
          <div className="value" style={{ color: 'var(--accent)' }}>{gainers.length}</div>
        </div>
        <div className="metric-card">
          <div className="label">Losers Today</div>
          <div className="value" style={{ color: 'var(--red)' }}>{losers.length}</div>
        </div>
        <div className="metric-card">
          <div className="label">Avg Change</div>
          <div className="value" style={{ color: totalChange >= 0 ? 'var(--accent)' : 'var(--red)' }}>
            {items.length ? (items.reduce((s,i) => s + (i.change_pct||0), 0) / items.length).toFixed(2) + '%' : '—'}
          </div>
        </div>
      </div>

      {/* Add form */}
      <div className="card mb-20 fade-up">
        <div className="card-title">Add Stock</div>
        <div className="flex gap-12 flex-wrap">
          <select className="input" style={{ flex: 1, maxWidth: 320 }} value={symbol} onChange={e => setSymbol(e.target.value)}>
            <option value="">Select from list…</option>
            {stockList.map(s => (
              <option key={s.symbol} value={s.symbol}>{s.name} ({s.symbol})</option>
            ))}
          </select>
          <span style={{ color:'var(--text-3)', alignSelf:'center', fontSize:13 }}>or</span>
          <input className="input" style={{ flex:1, maxWidth:200 }} placeholder="Type symbol e.g. ZOMATO.NS"
            value={symbol} onChange={e => setSymbol(e.target.value.toUpperCase())}
            onKeyDown={e => e.key === 'Enter' && handleAdd()}/>
          <button className="btn btn-primary" onClick={handleAdd} disabled={!symbol || adding}>
            {adding ? <><div className="spinner" style={{width:14,height:14,borderWidth:2}}/> Adding…</> : <><Plus size={15}/> Add</>}
          </button>
          <button className="btn btn-ghost" onClick={load} disabled={loading}>
            <RefreshCw size={14} className={loading ? 'spin' : ''}/>
          </button>
        </div>
      </div>

      {/* Filter */}
      {items.length > 0 && (
        <div className="flex gap-12 mb-16 items-center fade-up">
          <div className="search-wrapper" style={{ maxWidth: 280 }}>
            <input className="input" placeholder="Filter portfolio…" value={filter} onChange={e => setFilter(e.target.value)}/>
          </div>
          <span style={{ fontSize:12, color:'var(--text-3)' }}>{filtered.length} of {items.length} stocks</span>
        </div>
      )}

      {/* Table */}
      {loading ? (
        <div className="flex items-center gap-12" style={{ padding: 40 }}>
          <div className="spinner spinner-lg"/><span className="text-muted">Loading portfolio…</span>
        </div>
      ) : items.length === 0 ? (
        <div className="empty-state fade-up">
          <Briefcase size={56} style={{ margin:'0 auto 16px', display:'block' }}/>
          <p style={{ fontSize:16, fontWeight:600, color:'var(--text-2)', marginBottom:6 }}>Portfolio is empty</p>
          <p>Add stocks using the form above</p>
        </div>
      ) : (
        <div className="table-wrapper fade-up">
          <table>
            <thead>
              <tr>
                <th>Symbol</th>
                <th>Company</th>
                <th>Sector</th>
                <th>Price (₹)</th>
                <th>Change</th>
                <th>Change %</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {filtered.map(item => (
                <tr key={item.symbol}>
                  <td><span className="mono" style={{ fontWeight:600 }}>{item.symbol}</span></td>
                  <td style={{ maxWidth:200, whiteSpace:'nowrap', overflow:'hidden', textOverflow:'ellipsis' }}>{item.name}</td>
                  <td><span className="tag tag-sector">{item.sector}</span></td>
                  <td><span className="mono">₹{item.price.toLocaleString('en-IN')}</span></td>
                  <td>
                    <span className={item.change >= 0 ? 'price-pos' : 'price-neg'}>
                      {item.change >= 0 ? '+' : ''}{item.change.toFixed(2)}
                    </span>
                  </td>
                  <td>
                    <div className="flex gap-6 items-center">
                      {item.change_pct >= 0 ? <TrendingUp size={13} color="var(--accent)"/> : <TrendingDown size={13} color="var(--red)"/>}
                      <span className={item.change_pct >= 0 ? 'price-pos' : 'price-neg'}>
                        {item.change_pct >= 0 ? '+' : ''}{item.change_pct.toFixed(2)}%
                      </span>
                    </div>
                  </td>
                  <td>
                    <button className="btn-icon danger" onClick={() => handleRemove(item.symbol)}>
                      <Trash2 size={14}/>
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
