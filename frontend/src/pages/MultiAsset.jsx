import { useState, useEffect } from 'react';
import {
  getTreasuryYields, getYieldCurve, getCommodities, getCommodityHistory,
  getForexRates, getForexHistory, getCorrelation, getAssetPerformance,
} from '../api';
import {
  LineChart, Line, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  CartesianGrid, Legend, AreaChart, Area,
} from 'recharts';

const TABS = ['bonds', 'commodities', 'forex', 'crossAsset'];

export default function MultiAsset() {
  const [tab, setTab] = useState('bonds');

  return (
    <div className="multi-asset-page">
      <h2>🌐 Multi-Asset Analysis</h2>
      <p className="page-subtitle">Bonds, Commodities, Forex & Cross-Asset Correlation</p>

      <div className="tab-row">
        <button className={`tab-btn ${tab === 'bonds' ? 'active' : ''}`} onClick={() => setTab('bonds')}>🏦 Bonds</button>
        <button className={`tab-btn ${tab === 'commodities' ? 'active' : ''}`} onClick={() => setTab('commodities')}>🪙 Commodities</button>
        <button className={`tab-btn ${tab === 'forex' ? 'active' : ''}`} onClick={() => setTab('forex')}>💱 Forex</button>
        <button className={`tab-btn ${tab === 'crossAsset' ? 'active' : ''}`} onClick={() => setTab('crossAsset')}>📊 Cross-Asset</button>
      </div>

      {tab === 'bonds' && <BondsTab />}
      {tab === 'commodities' && <CommoditiesTab />}
      {tab === 'forex' && <ForexTab />}
      {tab === 'crossAsset' && <CrossAssetTab />}
    </div>
  );
}

function BondsTab() {
  const [yields, setYields] = useState([]);
  const [curve, setCurve] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([getTreasuryYields(), getYieldCurve()])
      .then(([y, c]) => { setYields(y); setCurve(c); })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="loading-state"><div className="loading-spinner"></div></div>;

  return (
    <div className="asset-section">
      {/* Yield Cards */}
      <div className="metrics-row">
        {yields.map(y => (
          <div key={y.id} className="metric-card">
            <div className="metric-value">{y.yield_pct}%</div>
            <div className="metric-label">{y.name}</div>
            <div className={`metric-change ${y.change >= 0 ? 'up' : 'down'}`}>
              {y.change >= 0 ? '▲' : '▼'} {Math.abs(y.change)}
            </div>
          </div>
        ))}
      </div>

      {/* Yield Curve */}
      {curve && curve.points && curve.points.length > 0 && (
        <div className="card">
          <h3>US Treasury Yield Curve</h3>
          <div className={`yield-shape-badge ${curve.shape}`}>
            {curve.shape === 'normal' ? '✅ Normal' : curve.shape === 'inverted' ? '⚠️ Inverted' : '➖ Flat'}
          </div>
          <p className="shape-desc">{curve.description}</p>
          <div className="chart-container" style={{ height: 300 }}>
            <ResponsiveContainer>
              <AreaChart data={curve.points} margin={{ top: 10, right: 30, bottom: 20, left: 10 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#333" />
                <XAxis dataKey="maturity" stroke="#999" />
                <YAxis stroke="#999" label={{ value: 'Yield (%)', angle: -90, position: 'insideLeft', fill: '#999' }} />
                <Tooltip />
                <Area type="monotone" dataKey="yield_pct" stroke="#00c896" fill="rgba(0,200,150,0.2)" strokeWidth={2}
                      name="Yield (%)" dot={{ r: 5, fill: '#00c896' }} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}
    </div>
  );
}

function CommoditiesTab() {
  const [commodities, setCommodities] = useState([]);
  const [selected, setSelected] = useState(null);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getCommodities().then(setCommodities).catch(console.error).finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (selected) {
      getCommodityHistory(selected, '3mo').then(setHistory).catch(console.error);
    }
  }, [selected]);

  if (loading) return <div className="loading-state"><div className="loading-spinner"></div></div>;

  return (
    <div className="asset-section">
      <div className="commodity-grid">
        {commodities.map(c => (
          <div key={c.id} className={`commodity-card ${selected === c.id ? 'selected' : ''}`}
               onClick={() => setSelected(c.id)}>
            <div className="commodity-name">{c.name}</div>
            <div className="commodity-price">${c.price.toLocaleString()}</div>
            <div className={`commodity-change ${c.change >= 0 ? 'up' : 'down'}`}>
              {c.change >= 0 ? '▲' : '▼'} ${Math.abs(c.change)} ({c.change_pct.toFixed(2)}%)
            </div>
            <div className="commodity-unit">{c.unit}</div>
          </div>
        ))}
      </div>

      {selected && history.length > 0 && (
        <div className="card">
          <h3>{commodities.find(c => c.id === selected)?.name || selected} — 3 Month History</h3>
          <div className="chart-container" style={{ height: 300 }}>
            <ResponsiveContainer>
              <AreaChart data={history} margin={{ top: 10, right: 30, bottom: 20, left: 10 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#333" />
                <XAxis dataKey="date" stroke="#999" tickFormatter={d => d.slice(5)} />
                <YAxis stroke="#999" />
                <Tooltip />
                <Area type="monotone" dataKey="close" stroke="#f7931a" fill="rgba(247,147,26,0.15)" strokeWidth={2} name="Price" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}
    </div>
  );
}

function ForexTab() {
  const [pairs, setPairs] = useState([]);
  const [selected, setSelected] = useState(null);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getForexRates().then(setPairs).catch(console.error).finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (selected) {
      getForexHistory(selected, '3mo').then(setHistory).catch(console.error);
    }
  }, [selected]);

  if (loading) return <div className="loading-state"><div className="loading-spinner"></div></div>;

  return (
    <div className="asset-section">
      <div className="forex-grid">
        {pairs.map(p => (
          <div key={p.pair} className={`forex-card ${selected === p.pair ? 'selected' : ''}`}
               onClick={() => setSelected(p.pair)}>
            <div className="forex-pair">{p.name}</div>
            <div className="forex-rate">{p.rate.toFixed(4)}</div>
            <div className={`forex-change ${p.change >= 0 ? 'up' : 'down'}`}>
              {p.change >= 0 ? '▲' : '▼'} {Math.abs(p.change).toFixed(4)} ({p.change_pct.toFixed(2)}%)
            </div>
          </div>
        ))}
      </div>

      {selected && history.length > 0 && (
        <div className="card">
          <h3>{pairs.find(p => p.pair === selected)?.name || selected} — 3 Month History</h3>
          <div className="chart-container" style={{ height: 300 }}>
            <ResponsiveContainer>
              <LineChart data={history} margin={{ top: 10, right: 30, bottom: 20, left: 10 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#333" />
                <XAxis dataKey="date" stroke="#999" tickFormatter={d => d.slice(5)} />
                <YAxis stroke="#999" domain={['auto', 'auto']} />
                <Tooltip />
                <Line type="monotone" dataKey="rate" stroke="#4b77d1" strokeWidth={2} dot={false} name="Rate" />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}
    </div>
  );
}

function CrossAssetTab() {
  const [correlation, setCorrelation] = useState(null);
  const [performance, setPerformance] = useState([]);
  const [period, setPeriod] = useState('1y');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    Promise.all([getCorrelation(period), getAssetPerformance(period)])
      .then(([c, p]) => { setCorrelation(c); setPerformance(p); })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [period]);

  if (loading) return <div className="loading-state"><div className="loading-spinner"></div></div>;

  return (
    <div className="asset-section">
      <div className="config-row">
        <select value={period} onChange={e => setPeriod(e.target.value)} className="select-input">
          <option value="6mo">6 Months</option>
          <option value="1y">1 Year</option>
          <option value="2y">2 Years</option>
        </select>
      </div>

      {/* Performance Comparison */}
      {performance.length > 0 && (
        <div className="card">
          <h3>Asset Class Performance</h3>
          <div className="performance-bars">
            {performance.map((p, i) => (
              <div key={i} className="perf-row">
                <span className="perf-label">{p.label}</span>
                <div className="perf-bar-wrap">
                  <div className={`perf-bar ${p.total_return_pct >= 0 ? 'positive' : 'negative'}`}
                       style={{ width: `${Math.min(Math.abs(p.total_return_pct), 100)}%` }}>
                  </div>
                </div>
                <span className={`perf-value ${p.total_return_pct >= 0 ? 'up' : 'down'}`}>
                  {p.total_return_pct >= 0 ? '+' : ''}{p.total_return_pct}%
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Correlation Matrix */}
      {correlation && correlation.matrix && correlation.labels && (
        <div className="card">
          <h3>Cross-Asset Correlation</h3>
          <div className="corr-matrix">
            <table>
              <thead>
                <tr>
                  <th></th>
                  {correlation.labels.map(l => <th key={l}>{l}</th>)}
                </tr>
              </thead>
              <tbody>
                {correlation.matrix.map((row, i) => (
                  <tr key={i}>
                    <td className="corr-label">{correlation.labels[i]}</td>
                    {row.map((val, j) => (
                      <td key={j} className="corr-cell" style={{
                        background: val > 0
                          ? `rgba(0,200,150,${Math.abs(val) * 0.7})`
                          : `rgba(231,76,60,${Math.abs(val) * 0.7})`,
                        color: Math.abs(val) > 0.5 ? '#fff' : '#ccc',
                      }}>
                        {val.toFixed(2)}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
