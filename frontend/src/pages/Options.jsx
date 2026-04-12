import { useState } from 'react';
import { priceOption, getStrategies, computeTemplateStrategy } from '../api';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, ReferenceLine, Area, AreaChart } from 'recharts';

const STRATEGIES = [
  { value: 'long_call', label: 'Long Call', icon: '📈' },
  { value: 'long_put', label: 'Long Put', icon: '📉' },
  { value: 'covered_call', label: 'Covered Call', icon: '🛡️' },
  { value: 'straddle', label: 'Straddle', icon: '⬆️⬇️' },
  { value: 'strangle', label: 'Strangle', icon: '↕️' },
  { value: 'bull_call_spread', label: 'Bull Call Spread', icon: '🐂' },
  { value: 'bear_put_spread', label: 'Bear Put Spread', icon: '🐻' },
  { value: 'iron_condor', label: 'Iron Condor', icon: '🦅' },
  { value: 'butterfly', label: 'Butterfly', icon: '🦋' },
];

export default function Options() {
  const [tab, setTab] = useState('pricer');

  return (
    <div className="options-page">
      <h2>📊 Options Pricing & Strategies</h2>
      <p className="page-subtitle">Black-Scholes pricing, Greeks, and multi-leg P&L diagrams</p>

      <div className="tab-row">
        <button className={`tab-btn ${tab === 'pricer' ? 'active' : ''}`} onClick={() => setTab('pricer')}>💰 Options Pricer</button>
        <button className={`tab-btn ${tab === 'strategies' ? 'active' : ''}`} onClick={() => setTab('strategies')}>📐 Strategy Builder</button>
      </div>

      {tab === 'pricer' && <PricerTab />}
      {tab === 'strategies' && <StrategyTab />}
    </div>
  );
}

function PricerTab() {
  const [spot, setSpot] = useState(2500);
  const [strike, setStrike] = useState(2600);
  const [expiry, setExpiry] = useState(0.25);
  const [vol, setVol] = useState(0.25);
  const [rate, setRate] = useState(0.065);
  const [optType, setOptType] = useState('call');
  const [model, setModel] = useState('black_scholes');
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const calculate = async () => {
    setLoading(true);
    try {
      const data = await priceOption({
        spot, strike, expiry_years: expiry, volatility: vol,
        rate, option_type: optType, model, steps: 100,
      });
      setResult(data);
    } catch (e) {
      alert('Error: ' + (e.response?.data?.detail || e.message));
    } finally {
      setLoading(false);
    }
  };

  const greekGauge = (label, value, min, max, color) => {
    const pct = Math.min(Math.max(((value - min) / (max - min)) * 100, 0), 100);
    return (
      <div className="greek-gauge">
        <div className="greek-label">{label}</div>
        <div className="greek-bar-wrap">
          <div className="greek-bar" style={{ width: `${pct}%`, background: color }}></div>
        </div>
        <div className="greek-value">{value}</div>
      </div>
    );
  };

  return (
    <div className="pricer-section">
      <div className="pricer-grid">
        <div className="card pricer-form">
          <h3>Option Parameters</h3>
          <div className="option-type-toggle">
            <button className={`toggle-btn ${optType === 'call' ? 'active call' : ''}`}
                    onClick={() => setOptType('call')}>📈 CALL</button>
            <button className={`toggle-btn ${optType === 'put' ? 'active put' : ''}`}
                    onClick={() => setOptType('put')}>📉 PUT</button>
          </div>

          <div className="form-grid-2col">
            <div>
              <label className="field-label">Spot Price (₹)</label>
              <input type="number" value={spot} onChange={e => setSpot(parseFloat(e.target.value) || 0)} className="number-input" />
            </div>
            <div>
              <label className="field-label">Strike Price (₹)</label>
              <input type="number" value={strike} onChange={e => setStrike(parseFloat(e.target.value) || 0)} className="number-input" />
            </div>
            <div>
              <label className="field-label">Expiry (years)</label>
              <input type="number" step="0.01" value={expiry} onChange={e => setExpiry(parseFloat(e.target.value) || 0)} className="number-input" />
            </div>
            <div>
              <label className="field-label">Volatility (%)</label>
              <input type="number" step="0.01" value={(vol * 100).toFixed(0)} onChange={e => setVol(parseFloat(e.target.value) / 100 || 0)} className="number-input" />
            </div>
            <div>
              <label className="field-label">Risk-free Rate (%)</label>
              <input type="number" step="0.1" value={(rate * 100).toFixed(1)} onChange={e => setRate(parseFloat(e.target.value) / 100 || 0)} className="number-input" />
            </div>
            <div>
              <label className="field-label">Model</label>
              <select value={model} onChange={e => setModel(e.target.value)} className="select-input">
                <option value="black_scholes">Black-Scholes</option>
                <option value="binomial">Binomial Tree</option>
              </select>
            </div>
          </div>

          <button className="btn-primary full-width" onClick={calculate} disabled={loading}>
            {loading ? '⏳ Calculating...' : '🧮 Calculate Price'}
          </button>
        </div>

        {result && (
          <div className="card pricer-result">
            <h3>Results — {model === 'black_scholes' ? 'Black-Scholes' : 'Binomial Tree'}</h3>
            <div className="option-price-hero">
              <div className="hero-label">{optType.toUpperCase()} Premium</div>
              <div className="hero-value">₹{result.price}</div>
            </div>

            <h4>Greeks</h4>
            <div className="greeks-grid">
              {greekGauge('Δ Delta', result.delta, -1, 1, '#00c896')}
              {greekGauge('Γ Gamma', result.gamma, 0, 0.05, '#4b77d1')}
              {greekGauge('Θ Theta', result.theta, -5, 0, '#e74c3c')}
              {greekGauge('ν Vega', result.vega, 0, 50, '#9b59b6')}
              {greekGauge('ρ Rho', result.rho, -10, 10, '#f7931a')}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function StrategyTab() {
  const [strategy, setStrategy] = useState('straddle');
  const [spot, setSpot] = useState(2500);
  const [strike, setStrike] = useState(2500);
  const [premium, setPremium] = useState(100);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const calculate = async () => {
    setLoading(true);
    try {
      const data = await computeTemplateStrategy({ strategy, spot, strike, premium });
      setResult(data);
    } catch (e) {
      alert('Error: ' + (e.response?.data?.detail || e.message));
    } finally {
      setLoading(false);
    }
  };

  const payoffData = result ? result.spot_prices.map((s, i) => ({
    spot: s,
    payoff: result.payoffs[i],
  })) : [];

  return (
    <div className="strategy-section">
      <div className="strategy-selector">
        {STRATEGIES.map(s => (
          <div key={s.value}
               className={`strategy-chip ${strategy === s.value ? 'active' : ''}`}
               onClick={() => setStrategy(s.value)}>
            <span className="chip-icon">{s.icon}</span>
            <span className="chip-label">{s.label}</span>
          </div>
        ))}
      </div>

      <div className="card">
        <h3>{STRATEGIES.find(s => s.value === strategy)?.icon} {STRATEGIES.find(s => s.value === strategy)?.label}</h3>
        <div className="form-grid">
          <div>
            <label className="field-label">Spot Price (₹)</label>
            <input type="number" value={spot} onChange={e => setSpot(parseFloat(e.target.value) || 0)} className="number-input" />
          </div>
          <div>
            <label className="field-label">Strike Price (₹)</label>
            <input type="number" value={strike} onChange={e => setStrike(parseFloat(e.target.value) || 0)} className="number-input" />
          </div>
          <div>
            <label className="field-label">Premium (₹)</label>
            <input type="number" value={premium} onChange={e => setPremium(parseFloat(e.target.value) || 0)} className="number-input" />
          </div>
        </div>
        <button className="btn-primary" onClick={calculate} disabled={loading}>
          {loading ? '⏳...' : '📊 Compute Payoff'}
        </button>
      </div>

      {result && (
        <>
          <div className="metrics-row">
            <div className="metric-card accent-green">
              <div className="metric-value">₹{result.max_profit}</div>
              <div className="metric-label">Max Profit</div>
            </div>
            <div className="metric-card accent-red">
              <div className="metric-value">₹{result.max_loss}</div>
              <div className="metric-label">Max Loss</div>
            </div>
            {result.breakevens.map((b, i) => (
              <div key={i} className="metric-card accent-blue">
                <div className="metric-value">₹{b}</div>
                <div className="metric-label">Breakeven {result.breakevens.length > 1 ? i + 1 : ''}</div>
              </div>
            ))}
          </div>

          <div className="card">
            <h3>P&L Payoff Diagram</h3>
            <div className="chart-container" style={{ height: 350 }}>
              <ResponsiveContainer>
                <AreaChart data={payoffData} margin={{ top: 10, right: 30, bottom: 20, left: 10 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#333" />
                  <XAxis dataKey="spot" stroke="#999" label={{ value: 'Spot Price (₹)', position: 'bottom', fill: '#999' }} />
                  <YAxis stroke="#999" label={{ value: 'P&L (₹)', angle: -90, position: 'insideLeft', fill: '#999' }} />
                  <Tooltip formatter={(v) => `₹${v}`} />
                  <ReferenceLine y={0} stroke="#666" strokeDasharray="5 5" />
                  <ReferenceLine x={spot} stroke="#f7931a" strokeDasharray="3 3" label={{ value: 'Spot', fill: '#f7931a' }} />
                  <defs>
                    <linearGradient id="payoffGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#00c896" stopOpacity={0.3}/>
                      <stop offset="95%" stopColor="#e74c3c" stopOpacity={0.3}/>
                    </linearGradient>
                  </defs>
                  <Area type="monotone" dataKey="payoff" stroke="#00c896" fill="url(#payoffGrad)"
                        strokeWidth={2} name="P&L" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
