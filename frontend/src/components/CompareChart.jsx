import { useEffect, useState } from 'react';
import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend } from 'recharts';
import { getCompare } from '../api';

const Tip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <div style={{ background:'var(--bg-2)', border:'1px solid var(--border)', borderRadius:10, padding:'10px 14px', fontSize:12, fontFamily:'var(--font-mono)' }}>
      <div style={{ color:'var(--text-3)', marginBottom:6 }}>{label}</div>
      {payload.map(p => (
        <div key={p.name} style={{ color:p.color }}>{p.name}: {p.value?.toFixed(2)}</div>
      ))}
    </div>
  );
};

export default function CompareChart({ symbol1, symbol2, period, name1, name2 }) {
  const [data, setData]   = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!symbol1 || !symbol2) return;
    setLoading(true);
    getCompare(symbol1, symbol2, period)
      .then(res => {
        const s1 = res.stock1.data, s2 = res.stock2.data;
        const len = Math.min(s1.length, s2.length);
        const merged = Array.from({ length: len }, (_, i) => ({
          date: s1[i]?.Date?.slice(0, 10) || '',
          [symbol1]: s1[i]?.Normalised,
          [symbol2]: s2[i]?.Normalised,
        }));
        setData(merged);
      })
      .catch(() => setData([]))
      .finally(() => setLoading(false));
  }, [symbol1, symbol2, period]);

  if (loading) return <div className="flex items-center gap-8"><div className="spinner"/><span className="text-muted text-sm">Loading comparison…</span></div>;
  if (!data.length) return null;

  return (
    <div>
      <div style={{ fontSize:11, color:'var(--text-3)', fontFamily:'var(--font-mono)', marginBottom:8 }}>Normalised to 100 at start of period</div>
      <ResponsiveContainer width="100%" height={260}>
        <LineChart data={data} margin={{ top:5, right:10, left:0, bottom:5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" vertical={false}/>
          <XAxis dataKey="date" tick={{ fill:'var(--text-3)', fontSize:10, fontFamily:'var(--font-mono)' }} tickLine={false} axisLine={false} interval="preserveStartEnd"/>
          <YAxis tick={{ fill:'var(--text-3)', fontSize:10, fontFamily:'var(--font-mono)' }} tickLine={false} axisLine={false} domain={['auto','auto']} width={45}/>
          <Tooltip content={<Tip />}/>
          <Legend iconSize={10} iconType="circle" wrapperStyle={{ fontSize:12, fontFamily:'var(--font-mono)', paddingTop:8 }}/>
          <Line type="monotone" dataKey={symbol1} stroke="var(--accent)" strokeWidth={2} dot={false} name={name1}/>
          <Line type="monotone" dataKey={symbol2} stroke="var(--accent2)" strokeWidth={2} dot={false} name={name2}/>
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
