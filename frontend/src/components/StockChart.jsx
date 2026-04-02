import { useState } from 'react';
import {
  ResponsiveContainer, ComposedChart, LineChart, Line, Bar,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, Area, AreaChart, ReferenceLine
} from 'recharts';
import { Activity, BarChart2, TrendingUp } from 'lucide-react';

const PERIODS = ['1d','5d','1mo','3mo','6mo','1y','5y'];

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <div style={{
      background: 'var(--bg-2)', border: '1px solid var(--border)',
      borderRadius: 10, padding: '10px 14px', fontSize: 12,
      fontFamily: 'var(--font-mono)', minWidth: 160,
    }}>
      <div style={{ color: 'var(--text-3)', marginBottom: 6, fontSize: 11 }}>{label}</div>
      {payload.map(p => (
        <div key={p.name} style={{ color: p.color, display: 'flex', justifyContent: 'space-between', gap: 16 }}>
          <span>{p.name}</span>
          <span>₹{typeof p.value === 'number' ? p.value.toFixed(2) : p.value}</span>
        </div>
      ))}
    </div>
  );
};

const VolumeTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  const vol = payload[0]?.value;
  return (
    <div style={{ background:'var(--bg-2)', border:'1px solid var(--border)', borderRadius:10, padding:'8px 12px', fontSize:11, fontFamily:'var(--font-mono)' }}>
      <div style={{ color:'var(--text-3)' }}>{label}</div>
      <div style={{ color:'var(--blue)' }}>Vol: {vol?.toLocaleString('en-IN')}</div>
    </div>
  );
};

const RSITooltip = ({ active, payload }) => {
  if (!active || !payload?.length) return null;
  const v = payload[0]?.value;
  return (
    <div style={{ background:'var(--bg-2)', border:'1px solid var(--border)', borderRadius:10, padding:'8px 12px', fontSize:11, fontFamily:'var(--font-mono)' }}>
      <div style={{ color: v > 70 ? 'var(--red)' : v < 30 ? 'var(--accent)' : 'var(--text-1)' }}>RSI: {v?.toFixed(2)}</div>
    </div>
  );
};

function formatDate(str, period) {
  if (!str) return '';
  const d = new Date(str);
  if (period === '1d') return d.toLocaleTimeString('en-IN', { hour:'2-digit', minute:'2-digit' });
  if (period === '5d') return d.toLocaleDateString('en-IN', { day:'2-digit', month:'short' }) + ' ' + d.toLocaleTimeString('en-IN', { hour:'2-digit', minute:'2-digit', hour12:false });
  return d.toLocaleDateString('en-IN', { day:'2-digit', month:'short', year: period === '5y' ? 'numeric' : undefined });
}

export default function StockChart({ data, period, onPeriodChange, loading }) {
  const [view, setView] = useState('price');

  const chartData = (data?.candles || []).map(c => ({
    ...c,
    date: formatDate(c.Date, period),
  }));

  const views = [
    { id: 'price',  label: 'Price',  icon: TrendingUp },
    { id: 'volume', label: 'Volume', icon: BarChart2 },
    { id: 'rsi',    label: 'RSI',    icon: Activity },
  ];

  return (
    <div className="chart-wrapper fade-up">
      <div className="chart-header">
        <div>
          <div className="chart-title">{data?.name || '—'}</div>
          <div style={{ fontSize: 12, color: 'var(--text-3)', fontFamily: 'var(--font-mono)', marginTop: 2 }}>{data?.symbol}</div>
        </div>
        <div className="flex gap-12 flex-wrap">
          <div className="tab-bar">
            {views.map(v => (
              <button key={v.id} className={`tab-btn ${view === v.id ? 'active' : ''}`} onClick={() => setView(v.id)}>
                {v.label}
              </button>
            ))}
          </div>
          <div className="period-bar">
            {PERIODS.map(p => (
              <button key={p} className={`period-btn ${period === p ? 'active' : ''}`} onClick={() => onPeriodChange(p)}>
                {p.toUpperCase()}
              </button>
            ))}
          </div>
        </div>
      </div>

      {loading ? (
        <div style={{ height: 300, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <div className="spinner spinner-lg" />
        </div>
      ) : chartData.length === 0 ? (
        <div className="empty-state" style={{ height: 300 }}><p>No chart data available</p></div>
      ) : (
        <>
          {view === 'price' && (
            <ResponsiveContainer width="100%" height={320}>
              <ComposedChart data={chartData} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
                <defs>
                  <linearGradient id="priceGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%"  stopColor="var(--accent)" stopOpacity={0.2}/>
                    <stop offset="95%" stopColor="var(--accent)" stopOpacity={0}/>
                  </linearGradient>
                  <linearGradient id="bbGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%"  stopColor="var(--blue)" stopOpacity={0.05}/>
                    <stop offset="95%" stopColor="var(--blue)" stopOpacity={0.01}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" vertical={false}/>
                <XAxis dataKey="date" tick={{ fill:'var(--text-3)', fontSize:10, fontFamily:'var(--font-mono)' }} tickLine={false} axisLine={false} interval="preserveStartEnd"/>
                <YAxis tick={{ fill:'var(--text-3)', fontSize:10, fontFamily:'var(--font-mono)' }} tickLine={false} axisLine={false} tickFormatter={v => `₹${v}`} width={70} domain={['auto','auto']}/>
                <Tooltip content={<CustomTooltip />} />
                <Legend iconSize={10} iconType="circle" wrapperStyle={{ fontSize: 12, fontFamily: 'var(--font-mono)', paddingTop: 12 }}/>
                {chartData[0]?.BB_upper && (
                  <>
                    <Area type="monotone" dataKey="BB_upper" fill="url(#bbGrad)" stroke="rgba(75,145,247,0.3)" strokeWidth={1} dot={false} name="BB Upper" strokeDasharray="4 2"/>
                    <Area type="monotone" dataKey="BB_lower" fill="url(#bbGrad)" stroke="rgba(75,145,247,0.3)" strokeWidth={1} dot={false} name="BB Lower" strokeDasharray="4 2"/>
                  </>
                )}
                <Area type="monotone" dataKey="Close" stroke="var(--accent)" strokeWidth={2} fill="url(#priceGrad)" dot={false} name="Price" activeDot={{ r:4, fill:'var(--accent)' }}/>
                {chartData[0]?.MA20 && <Line type="monotone" dataKey="MA20" stroke="var(--accent2)" strokeWidth={1.5} dot={false} name="MA20" strokeDasharray="6 3"/>}
                {chartData[0]?.MA50 && <Line type="monotone" dataKey="MA50" stroke="var(--blue)" strokeWidth={1.5} dot={false} name="MA50" strokeDasharray="6 3"/>}
              </ComposedChart>
            </ResponsiveContainer>
          )}

          {view === 'volume' && (
            <ResponsiveContainer width="100%" height={280}>
              <ComposedChart data={chartData} margin={{ top:5, right:10, left:0, bottom:5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" vertical={false}/>
                <XAxis dataKey="date" tick={{ fill:'var(--text-3)', fontSize:10, fontFamily:'var(--font-mono)' }} tickLine={false} axisLine={false} interval="preserveStartEnd"/>
                <YAxis tick={{ fill:'var(--text-3)', fontSize:10, fontFamily:'var(--font-mono)' }} tickLine={false} axisLine={false} tickFormatter={v => (v/1e6).toFixed(1)+'M'} width={60}/>
                <Tooltip content={<VolumeTooltip />}/>
                <Bar dataKey="Volume" fill="var(--blue)" opacity={0.7} name="Volume" radius={[2,2,0,0]}/>
              </ComposedChart>
            </ResponsiveContainer>
          )}

          {view === 'rsi' && (
            <div>
              <div style={{ fontSize:11, color:'var(--text-3)', fontFamily:'var(--font-mono)', padding:'0 0 8px 70px' }}>
                RSI (14) — Overbought &gt; 70 · Oversold &lt; 30
              </div>
              <ResponsiveContainer width="100%" height={220}>
                <LineChart data={chartData} margin={{ top:5, right:10, left:0, bottom:5 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" vertical={false}/>
                  <XAxis dataKey="date" tick={{ fill:'var(--text-3)', fontSize:10, fontFamily:'var(--font-mono)' }} tickLine={false} axisLine={false} interval="preserveStartEnd"/>
                  <YAxis domain={[0,100]} tick={{ fill:'var(--text-3)', fontSize:10, fontFamily:'var(--font-mono)' }} tickLine={false} axisLine={false} width={40}/>
                  <Tooltip content={<RSITooltip />}/>
                  <ReferenceLine y={70} stroke="var(--red)"    strokeDasharray="4 4" strokeWidth={1}/>
                  <ReferenceLine y={30} stroke="var(--accent)" strokeDasharray="4 4" strokeWidth={1}/>
                  <ReferenceLine y={50} stroke="var(--text-3)" strokeDasharray="2 4" strokeWidth={1}/>
                  <Line type="monotone" dataKey="RSI" stroke="var(--accent2)" strokeWidth={2} dot={false} name="RSI"/>
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}
        </>
      )}
    </div>
  );
}
