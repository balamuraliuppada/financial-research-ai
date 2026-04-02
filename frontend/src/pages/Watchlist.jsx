import { useState, useEffect, useCallback, useRef } from 'react';
import { Star, Trash2, Plus, RefreshCw, TrendingUp, TrendingDown, Edit2, Check, X } from 'lucide-react';
import { getWatchlist, addWatchlist, removeWatchlist, updateNote, getStockList } from '../api';
import { useToast } from '../context/ToastContext';

const SECTORS = [
  'Information Technology','Banking & Finance','Energy & Conglomerates','Automobile',
  'Pharmaceuticals','FMCG','Metals & Mining','Infrastructure','Telecom','Energy & Oil','Energy & Power',''
];

function NoteCell({ symbol, note, onSave }) {
  const [editing, setEditing] = useState(false);
  const [val, setVal]         = useState(note || '');
  const ref = useRef();

  const save = () => {
    onSave(symbol, val);
    setEditing(false);
  };
  const cancel = () => { setVal(note || ''); setEditing(false); };

  useEffect(() => { if (editing) ref.current?.focus(); }, [editing]);

  if (editing) return (
    <div className="flex gap-6 items-center">
      <input ref={ref} className="input" style={{ padding:'5px 10px', fontSize:12 }} value={val}
        onChange={e => setVal(e.target.value)} onKeyDown={e => { if(e.key==='Enter') save(); if(e.key==='Escape') cancel(); }}/>
      <button className="btn-icon" onClick={save}><Check size={13} color="var(--accent)"/></button>
      <button className="btn-icon" onClick={cancel}><X size={13}/></button>
    </div>
  );

  return (
    <div className="flex gap-6 items-center" style={{ cursor:'pointer' }} onClick={() => setEditing(true)}>
      <span style={{ fontSize:12, color: val ? 'var(--text-1)' : 'var(--text-3)', maxWidth:200, overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap' }}>
        {val || 'Add note…'}
      </span>
      <Edit2 size={11} color="var(--text-3)"/>
    </div>
  );
}

export default function Watchlist({ stockList }) {
  const toast = useToast();
  const [items, setItems]     = useState([]);
  const [loading, setLoading] = useState(false);
  const [filter, setFilter]   = useState('');
  // Add form
  const [formOpen, setFormOpen] = useState(false);
  const [sym, setSym]           = useState('');
  const [name, setName]         = useState('');
  const [sector, setSector]     = useState('');
  const [note, setNote]         = useState('');
  const [adding, setAdding]     = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try { setItems(await getWatchlist()); }
    catch { toast('Failed to load watchlist', 'error'); }
    finally { setLoading(false); }
  }, [toast]);

  useEffect(() => { load(); }, [load]);

  // Auto-fill name when symbol selected from dropdown
  const handleSymSelect = (s) => {
    setSym(s);
    const found = stockList.find(x => x.symbol === s);
    if (found) { setName(found.name); setSector(found.sector); }
  };

  const handleAdd = async () => {
    const s = sym.trim().toUpperCase();
    if (!s) return;
    setAdding(true);
    try {
      await addWatchlist({ symbol: s, name, sector, note });
      setSym(''); setName(''); setSector(''); setNote(''); setFormOpen(false);
      toast(`${s} added to watchlist`);
      load();
    } catch { toast('Failed to add to watchlist', 'error'); }
    finally { setAdding(false); }
  };

  const handleRemove = async (s) => {
    try {
      await removeWatchlist(s);
      toast(`${s} removed from watchlist`);
      setItems(p => p.filter(i => i.symbol !== s));
    } catch { toast('Failed to remove', 'error'); }
  };

  const handleNote = async (s, n) => {
    try {
      await updateNote(s, n);
      setItems(p => p.map(i => i.symbol === s ? { ...i, note: n } : i));
      toast('Note saved');
    } catch { toast('Failed to save note', 'error'); }
  };

  const filtered = items.filter(i =>
    i.symbol.toLowerCase().includes(filter.toLowerCase()) ||
    (i.name||'').toLowerCase().includes(filter.toLowerCase()) ||
    (i.sector||'').toLowerCase().includes(filter.toLowerCase())
  );

  return (
    <div>
      {/* Stats */}
      <div className="grid-4 mb-20 fade-up">
        <div className="metric-card"><div className="label">Watching</div><div className="value">{items.length}</div></div>
        <div className="metric-card"><div className="label">Gaining</div><div className="value" style={{ color:'var(--accent)' }}>{items.filter(i=>i.change_pct>0).length}</div></div>
        <div className="metric-card"><div className="label">Declining</div><div className="value" style={{ color:'var(--red)' }}>{items.filter(i=>i.change_pct<0).length}</div></div>
        <div className="metric-card"><div className="label">Sectors</div><div className="value">{new Set(items.map(i=>i.sector).filter(Boolean)).size}</div></div>
      </div>

      {/* Toolbar */}
      <div className="flex justify-between items-center mb-16 flex-wrap gap-12 fade-up">
        <div className="flex gap-10 items-center flex-wrap">
          <div className="search-wrapper" style={{ maxWidth:280 }}>
            <input className="input" placeholder="Filter watchlist…" value={filter} onChange={e => setFilter(e.target.value)}/>
          </div>
          <span style={{ fontSize:12, color:'var(--text-3)' }}>{filtered.length} stocks</span>
        </div>
        <div className="flex gap-8">
          <button className="btn btn-ghost btn-sm" onClick={load}><RefreshCw size={14}/> Refresh</button>
          <button className="btn btn-primary btn-sm" onClick={() => setFormOpen(v=>!v)}><Plus size={14}/> Add Stock</button>
        </div>
      </div>

      {/* Add form */}
      {formOpen && (
        <div className="card mb-20 fade-up">
          <div className="card-title">Add to Watchlist</div>
          <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr 1fr', gap:14, marginBottom:14 }}>
            <div className="input-group">
              <label className="input-label">Symbol *</label>
              <select className="input" value={sym} onChange={e => handleSymSelect(e.target.value)}>
                <option value="">Select stock…</option>
                {stockList.map(s => <option key={s.symbol} value={s.symbol}>{s.name}</option>)}
              </select>
              <input className="input" style={{ marginTop:6 }} placeholder="Or type e.g. ZOMATO.NS"
                value={sym} onChange={e => setSym(e.target.value.toUpperCase())}/>
            </div>
            <div className="input-group">
              <label className="input-label">Company Name</label>
              <input className="input" value={name} onChange={e => setName(e.target.value)} placeholder="Auto-filled or custom"/>
            </div>
            <div className="input-group">
              <label className="input-label">Sector</label>
              <select className="input" value={sector} onChange={e => setSector(e.target.value)}>
                <option value="">Select sector…</option>
                {SECTORS.filter(Boolean).map(s => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>
          </div>
          <div className="input-group mb-16">
            <label className="input-label">Note</label>
            <input className="input" value={note} onChange={e => setNote(e.target.value)} placeholder="Why are you watching this? e.g. 'Waiting for breakout above ₹1500'"/>
          </div>
          <div className="flex gap-8">
            <button className="btn btn-primary" onClick={handleAdd} disabled={!sym || adding}>
              {adding ? <><div className="spinner" style={{width:14,height:14,borderWidth:2}}/> Adding…</> : <><Star size={14}/> Add to Watchlist</>}
            </button>
            <button className="btn btn-ghost" onClick={() => { setFormOpen(false); setSym(''); setName(''); setSector(''); setNote(''); }}>
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Table */}
      {loading ? (
        <div className="flex items-center gap-12" style={{ padding:40 }}>
          <div className="spinner spinner-lg"/><span className="text-muted">Loading watchlist…</span>
        </div>
      ) : items.length === 0 ? (
        <div className="empty-state fade-up">
          <Star size={56} style={{ margin:'0 auto 16px', display:'block' }}/>
          <p style={{ fontSize:16, fontWeight:600, color:'var(--text-2)', marginBottom:6 }}>Watchlist is empty</p>
          <p>Click "Add Stock" to start tracking stocks</p>
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
                <th>Note</th>
                <th>Added</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {filtered.map(item => (
                <tr key={item.symbol}>
                  <td><span className="mono" style={{ fontWeight:600 }}>{item.symbol}</span></td>
                  <td style={{ maxWidth:180, whiteSpace:'nowrap', overflow:'hidden', textOverflow:'ellipsis' }}>{item.name || '—'}</td>
                  <td>{item.sector ? <span className="tag tag-sector">{item.sector}</span> : '—'}</td>
                  <td>
                    <span className="mono" style={{ fontWeight:600 }}>
                      {item.price ? `₹${item.price.toLocaleString('en-IN')}` : '—'}
                    </span>
                  </td>
                  <td>
                    {item.change !== 0 ? (
                      <span className={item.change >= 0 ? 'price-pos' : 'price-neg'}>
                        {item.change >= 0 ? '+' : ''}{item.change?.toFixed(2)}
                      </span>
                    ) : <span className="text-dim">—</span>}
                  </td>
                  <td>
                    {item.change_pct !== 0 ? (
                      <div className="flex gap-6 items-center">
                        {item.change_pct >= 0 ? <TrendingUp size={12} color="var(--accent)"/> : <TrendingDown size={12} color="var(--red)"/>}
                        <span className={item.change_pct >= 0 ? 'price-pos' : 'price-neg'}>
                          {item.change_pct >= 0 ? '+' : ''}{item.change_pct?.toFixed(2)}%
                        </span>
                      </div>
                    ) : <span className="text-dim">—</span>}
                  </td>
                  <td style={{ minWidth:180 }}>
                    <NoteCell symbol={item.symbol} note={item.note} onSave={handleNote}/>
                  </td>
                  <td style={{ whiteSpace:'nowrap' }}>
                    <span style={{ fontSize:11, color:'var(--text-3)', fontFamily:'var(--font-mono)' }}>
                      {item.added_at ? new Date(item.added_at).toLocaleDateString('en-IN') : '—'}
                    </span>
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
