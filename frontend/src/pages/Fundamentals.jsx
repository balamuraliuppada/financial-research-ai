import { useState, useCallback } from 'react';
import { BarChart2, Search, TrendingUp } from 'lucide-react';
import { getFundamentals, getSectors, getSectorComparison } from '../api';
import { useToast } from '../context/ToastContext';
import {
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Cell
} from 'recharts';

const SECTORS = [
  'Information Technology','Banking & Finance','Energy & Conglomerates','Automobile',
  'Pharmaceuticals','FMCG','Metals & Mining','Infrastructure','Telecom',
];

function FundCard({ label, value, note }) {
  const isNA = !value || value === 'N/A';
  return (
    <div className="metric-card">
      <div className="label">{label}</div>
      <div className="value" style={{ fontSize: 16, color: isNA ? 'var(--text-3)' : 'var(--text-1)' }}>{value || 'N/A'}</div>
      {note && <div className="sub neu">{note}</div>}
    </div>
  );
}

const SectorTip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <div style={{ background:'var(--bg-2)', border:'1px solid var(--border)', borderRadius:10, padding:'10px 14px', fontSize:12, fontFamily:'var(--font-mono)' }}>
      <div style={{ color:'var(--text-3)', marginBottom:6 }}>{label}</div>
      {payload.map(p => <div key={p.name} style={{ color:p.fill }}>P/E: {p.value?.toFixed(2)}</div>)}
    </div>
  );
};

export default function Fundamentals({ stockList }) {
  const toast = useToast();
  const [tab, setTab]               = useState('single');
  const [stockSym, setStockSym]     = useState('');
  const [fundData, setFundData]     = useState(null);
  const [loadFund, setLoadFund]     = useState(false);
  const [sector, setSector]         = useState('');
  const [sectorData, setSectorData] = useState(null);
  const [loadSector, setLoadSector] = useState(false);
  const [chartMetric, setChartMetric] = useState('P/E');

  const fetchFundamentals = useCallback(async () => {
    if (!stockSym) return;
    setLoadFund(true);
    try {
      const d = await getFundamentals(stockSym);
      setFundData(d);
    } catch { toast('Failed to load fundamentals', 'error'); }
    finally { setLoadFund(false); }
  }, [stockSym, toast]);

  const fetchSector = useCallback(async () => {
    if (!sector) return;
    setLoadSector(true);
    try {
      const d = await getSectorComparison(sector);
      setSectorData(d.rows || []);
    } catch { toast('Failed to load sector data', 'error'); }
    finally { setLoadSector(false); }
  }, [sector, toast]);

  const sections = [
    {
      title: 'Valuation',
      keys: ['P/E Ratio (TTM)','Forward P/E','P/B Ratio','P/S Ratio','EV/EBITDA'],
    },
    {
      title: 'Profitability',
      keys: ['Profit Margin','Operating Margin','Return on Equity (ROE)','Return on Assets (ROA)'],
    },
    {
      title: 'Debt & Liquidity',
      keys: ['Debt-to-Equity','Current Ratio','Quick Ratio'],
    },
    {
      title: 'Growth & EPS',
      keys: ['Revenue Growth (YoY)','Earnings Growth (YoY)','EPS (TTM)','EPS (Forward)'],
    },
    {
      title: 'Market Data',
      keys: ['Market Cap','Enterprise Value','Dividend Yield','52-Week High','52-Week Low','Beta'],
    },
  ];

  const sectorChartData = sectorData
    ? sectorData.map(r => ({
        name: (r.Company || r.Symbol || '').split(' ').slice(0,2).join(' '),
        value: parseFloat(r[chartMetric]) || 0,
      })).filter(r => r.value)
    : [];

  const COLORS = ['var(--accent)','var(--accent2)','var(--blue)','#a78bfa','#f472b6','#34d399','#fb923c'];

  return (
    <div>
      <div className="tab-bar mb-20 fade-up">
        <button className={`tab-btn ${tab==='single'?'active':''}`} onClick={()=>setTab('single')}>Single Stock</button>
        <button className={`tab-btn ${tab==='sector'?'active':''}`} onClick={()=>setTab('sector')}>Sector Compare</button>
      </div>

      {/* Single Stock */}
      {tab === 'single' && (
        <div>
          <div className="card mb-20 fade-up">
            <div className="card-title">Select Stock</div>
            <div className="flex gap-12 flex-wrap">
              <select className="input" style={{ flex:1, maxWidth:360 }} value={stockSym} onChange={e => setStockSym(e.target.value)}>
                <option value="">Choose a stock…</option>
                {stockList.map(s => <option key={s.symbol} value={s.symbol}>{s.name} ({s.symbol})</option>)}
              </select>
              <button className="btn btn-primary" onClick={fetchFundamentals} disabled={!stockSym || loadFund}>
                {loadFund ? <><div className="spinner" style={{width:14,height:14,borderWidth:2}}/> Loading…</> : <><BarChart2 size={15}/> Analyse</>}
              </button>
            </div>
          </div>

          {!fundData && !loadFund && (
            <div className="empty-state fade-up">
              <BarChart2 size={48} style={{ margin:'0 auto 14px', display:'block' }}/>
              <p style={{ fontSize:15, fontWeight:600, color:'var(--text-2)', marginBottom:4 }}>Select a stock to view fundamentals</p>
              <p>P/E, debt ratios, growth metrics, EPS and more</p>
            </div>
          )}

          {fundData && (
            <div className="fade-up">
              {sections.map(sec => (
                <div key={sec.title} className="mb-20">
                  <div style={{ fontSize:12, fontWeight:600, color:'var(--text-3)', textTransform:'uppercase', letterSpacing:1, marginBottom:10, fontFamily:'var(--font-mono)' }}>
                    {sec.title}
                  </div>
                  <div className="metric-grid">
                    {sec.keys.map(k => <FundCard key={k} label={k} value={fundData[k]}/>)}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Sector Comparison */}
      {tab === 'sector' && (
        <div>
          <div className="card mb-20 fade-up">
            <div className="card-title">Select Sector</div>
            <div className="flex gap-12 flex-wrap">
              <select className="input" style={{ flex:1, maxWidth:360 }} value={sector} onChange={e => setSector(e.target.value)}>
                <option value="">Choose a sector…</option>
                {SECTORS.map(s => <option key={s} value={s}>{s}</option>)}
              </select>
              <button className="btn btn-primary" onClick={fetchSector} disabled={!sector || loadSector}>
                {loadSector ? <><div className="spinner" style={{width:14,height:14,borderWidth:2}}/> Loading…</> : 'Compare'}
              </button>
            </div>
          </div>

          {sectorData && sectorData.length > 0 && (
            <>
              {/* Chart */}
              <div className="chart-wrapper mb-20 fade-up">
                <div className="chart-header">
                  <div className="chart-title">Sector Comparison — {sector}</div>
                  <div className="tab-bar">
                    {['P/E','P/B','ROE (%)','D/E','Net Margin (%)','Revenue Growth (%)'].map(m => (
                      <button key={m} className={`tab-btn ${chartMetric===m?'active':''}`} onClick={()=>setChartMetric(m)}>{m}</button>
                    ))}
                  </div>
                </div>
                {sectorChartData.length > 0 ? (
                  <ResponsiveContainer width="100%" height={280}>
                    <BarChart data={sectorChartData} margin={{ top:5, right:10, left:0, bottom:40 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" vertical={false}/>
                      <XAxis dataKey="name" tick={{ fill:'var(--text-3)', fontSize:11, fontFamily:'var(--font-mono)' }} tickLine={false} axisLine={false} angle={-20} textAnchor="end" interval={0}/>
                      <YAxis tick={{ fill:'var(--text-3)', fontSize:11, fontFamily:'var(--font-mono)' }} tickLine={false} axisLine={false} width={45}/>
                      <Tooltip content={<SectorTip />}/>
                      <Bar dataKey="value" radius={[6,6,0,0]}>
                        {sectorChartData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]}/>)}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                ) : <div className="text-muted text-sm" style={{ padding:20 }}>No chart data for {chartMetric}</div>}
              </div>

              {/* Table */}
              <div className="table-wrapper fade-up">
                <table>
                  <thead>
                    <tr>
                      <th>Company</th>
                      <th>Symbol</th>
                      <th>P/E</th>
                      <th>P/B</th>
                      <th>ROE (%)</th>
                      <th>D/E</th>
                      <th>Net Margin (%)</th>
                      <th>Rev Growth (%)</th>
                      <th>Market Cap</th>
                    </tr>
                  </thead>
                  <tbody>
                    {sectorData.map(row => (
                      <tr key={row.Symbol}>
                        <td style={{ fontWeight:600 }}>{row.Company}</td>
                        <td><span className="mono text-dim">{row.Symbol}</span></td>
                        {['P/E','P/B','ROE (%)','D/E','Net Margin (%)','Revenue Growth (%)'].map(k => (
                          <td key={k}>
                            <span className="mono">{row[k] ?? 'N/A'}</span>
                          </td>
                        ))}
                        <td><span className="mono">{row['Market Cap']}</span></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}

          {sectorData && sectorData.length === 0 && (
            <div className="empty-state fade-up"><p>No data for this sector</p></div>
          )}

          {!sectorData && !loadSector && (
            <div className="empty-state fade-up">
              <TrendingUp size={48} style={{ margin:'0 auto 14px', display:'block' }}/>
              <p style={{ fontSize:15, fontWeight:600, color:'var(--text-2)', marginBottom:4 }}>Select a sector to compare</p>
              <p>Side-by-side P/E, ROE, D/E, margins for all stocks in a sector</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
