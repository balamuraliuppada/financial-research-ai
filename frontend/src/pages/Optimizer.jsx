import { useState, useEffect } from 'react';
import { optimizePortfolio, getStockList } from '../api';
import { PieChart, Pie, Cell, ScatterChart, Scatter, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Legend } from 'recharts';

const COLORS = ['#00c896','#4b77d1','#f7931a','#e74c3c','#9b59b6','#1abc9c','#e67e22','#2ecc71','#3498db','#e91e63'];
const STRATEGIES = [
  { value: 'max_sharpe', label: '✨ Maximum Sharpe Ratio', desc: 'Best risk-adjusted return' },
  { value: 'min_volatility', label: '🛡️ Minimum Volatility', desc: 'Lowest portfolio risk' },
  { value: 'risk_parity', label: '⚖️ Risk Parity', desc: 'Equal risk contribution' },
  { value: 'equal_weight', label: '📊 Equal Weight', desc: 'Simple 1/N allocation' },
  { value: 'black_litterman', label: '🧠 Black-Litterman', desc: 'Bayesian equilibrium model' },
];

export default function Optimizer({ stockList }) {
  const [symbols, setSymbols] = useState([]);
  const [strategy, setStrategy] = useState('max_sharpe');
  const [period, setPeriod] = useState('1y');
  const [riskFree, setRiskFree] = useState(0.065);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const [searchTerm, setSearchTerm] = useState('');
  const stocks = stockList || [];

  const filteredStocks = stocks.filter(s =>
    s.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    s.symbol.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const toggleSymbol = (sym) => {
    setSymbols(prev => prev.includes(sym) ? prev.filter(s => s !== sym) : [...prev, sym]);
  };

  const runOptimization = async () => {
    if (symbols.length < 2) { setError('Select at least 2 stocks'); return; }
    setLoading(true); setError('');
    try {
      const data = await optimizePortfolio({
        symbols, strategy, period, risk_free: riskFree, include_frontier: true,
      });
      setResult(data);
    } catch (e) {
      setError(e.response?.data?.detail || 'Optimization failed');
    } finally {
      setLoading(false);
    }
  };

  const pieData = result ? Object.entries(result.optimal.weights)
    .filter(([,w]) => w > 0.001)
    .map(([sym, w]) => ({ name: sym.replace('.NS',''), value: Math.round(w * 10000) / 100 })) : [];

  return (
    <div className="optimizer-page">
      <h2>📐 Portfolio Optimizer</h2>
      <p className="page-subtitle">Modern Portfolio Theory — find your optimal allocation</p>

      <div className="optimizer-grid">
        {/* Config Panel */}
        <div className="card optimizer-config">
          <h3>Configuration</h3>

          <label className="field-label">Strategy</label>
          <div className="strategy-cards">
            {STRATEGIES.map(s => (
              <div key={s.value}
                   className={`strategy-card ${strategy === s.value ? 'active' : ''}`}
                   onClick={() => setStrategy(s.value)}>
                <div className="strategy-label">{s.label}</div>
                <div className="strategy-desc">{s.desc}</div>
              </div>
            ))}
          </div>

          <div className="config-row">
            <div>
              <label className="field-label">Period</label>
              <select value={period} onChange={e => setPeriod(e.target.value)} className="select-input">
                <option value="6mo">6 Months</option>
                <option value="1y">1 Year</option>
                <option value="2y">2 Years</option>
                <option value="5y">5 Years</option>
              </select>
            </div>
            <div>
              <label className="field-label">Risk-Free Rate</label>
              <input type="number" step="0.005" value={riskFree} onChange={e => setRiskFree(parseFloat(e.target.value) || 0)}
                     className="number-input" />
            </div>
          </div>

          <label className="field-label">Select Stocks ({symbols.length} selected)</label>
          <input type="text" placeholder="Search stocks..." value={searchTerm}
                 onChange={e => setSearchTerm(e.target.value)} className="search-input" />
          <div className="stock-picker">
            {filteredStocks.map(s => (
              <div key={s.symbol}
                   className={`stock-chip ${symbols.includes(s.symbol) ? 'selected' : ''}`}
                   onClick={() => toggleSymbol(s.symbol)}>
                {s.symbol.replace('.NS','')}
              </div>
            ))}
          </div>

          <button className="btn-primary full-width" onClick={runOptimization} disabled={loading || symbols.length < 2}>
            {loading ? '⏳ Optimizing...' : '🚀 Run Optimization'}
          </button>
          {error && <div className="error-msg">{error}</div>}
        </div>

        {/* Results Panel */}
        <div className="optimizer-results">
          {!result && !loading && (
            <div className="card empty-state">
              <div className="empty-icon">📊</div>
              <h3>Select stocks and run optimization</h3>
              <p>Choose at least 2 stocks to compute the optimal portfolio allocation</p>
            </div>
          )}

          {loading && (
            <div className="card empty-state">
              <div className="loading-spinner"></div>
              <h3>Computing efficient frontier...</h3>
              <p>Analyzing {symbols.length} assets with {strategy.replace('_',' ')} strategy</p>
            </div>
          )}

          {result && (
            <>
              {/* Metrics */}
              <div className="metrics-row">
                <div className="metric-card accent-green">
                  <div className="metric-value">{(result.optimal.expected_return * 100).toFixed(2)}%</div>
                  <div className="metric-label">Expected Return</div>
                </div>
                <div className="metric-card accent-orange">
                  <div className="metric-value">{(result.optimal.volatility * 100).toFixed(2)}%</div>
                  <div className="metric-label">Volatility</div>
                </div>
                <div className="metric-card accent-blue">
                  <div className="metric-value">{result.optimal.sharpe_ratio.toFixed(4)}</div>
                  <div className="metric-label">Sharpe Ratio</div>
                </div>
                <div className="metric-card accent-red">
                  <div className="metric-value">{(result.optimal.var_95 * 100).toFixed(2)}%</div>
                  <div className="metric-label">VaR (95%)</div>
                </div>
              </div>

              {/* Allocation Pie */}
              <div className="card">
                <h3>Optimal Allocation</h3>
                <div className="chart-container" style={{ height: 300 }}>
                  <ResponsiveContainer>
                    <PieChart>
                      <Pie data={pieData} cx="50%" cy="50%" outerRadius={100} innerRadius={50}
                           dataKey="value" label={({ name, value }) => `${name}: ${value}%`}>
                        {pieData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                      </Pie>
                      <Tooltip formatter={(v) => `${v}%`} />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
                <div className="weights-table">
                  {Object.entries(result.optimal.weights).filter(([,w]) => w > 0.001).map(([sym, w], i) => (
                    <div key={sym} className="weight-row">
                      <span className="weight-color" style={{ background: COLORS[i % COLORS.length] }}></span>
                      <span className="weight-sym">{sym}</span>
                      <div className="weight-bar-wrap">
                        <div className="weight-bar" style={{ width: `${w * 100}%`, background: COLORS[i % COLORS.length] }}></div>
                      </div>
                      <span className="weight-pct">{(w * 100).toFixed(1)}%</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Efficient Frontier */}
              {result.frontier && result.frontier.length > 0 && (
                <div className="card">
                  <h3>Efficient Frontier</h3>
                  <div className="chart-container" style={{ height: 350 }}>
                    <ResponsiveContainer>
                      <ScatterChart margin={{ top: 10, right: 30, bottom: 20, left: 10 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#333" />
                        <XAxis dataKey="x" name="Volatility" unit="%" type="number"
                               label={{ value: 'Volatility (%)', position: 'bottom', fill: '#999' }} />
                        <YAxis dataKey="y" name="Return" unit="%" type="number"
                               label={{ value: 'Return (%)', angle: -90, position: 'left', fill: '#999' }} />
                        <Tooltip cursor={{ strokeDasharray: '3 3' }}
                                 formatter={(v) => `${v.toFixed(2)}%`} />
                        <Legend />
                        {result.simulation && result.simulation.length > 0 && (
                          <Scatter name="Random Portfolios"
                            data={result.simulation.map(p => ({ x: p.volatility * 100, y: p.expected_return * 100, sharpe: p.sharpe_ratio }))}
                            fill="#334155" opacity={0.3} r={2} />
                        )}
                        <Scatter name="Efficient Frontier"
                          data={result.frontier.map(p => ({ x: p.volatility * 100, y: p.expected_return * 100 }))}
                          fill="#00c896" r={3} line={{ stroke: '#00c896', strokeWidth: 2 }} />
                        <Scatter name="Optimal Portfolio"
                          data={[{ x: result.optimal.volatility * 100, y: result.optimal.expected_return * 100 }]}
                          fill="#f7931a" r={8} shape="star" />
                      </ScatterChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              )}

              {/* Correlation Matrix */}
              {result.correlation && result.correlation.matrix && (
                <div className="card">
                  <h3>Correlation Matrix</h3>
                  <div className="corr-matrix">
                    <table>
                      <thead>
                        <tr>
                          <th></th>
                          {result.correlation.symbols.map(s => <th key={s}>{s.replace('.NS','')}</th>)}
                        </tr>
                      </thead>
                      <tbody>
                        {result.correlation.matrix.map((row, i) => (
                          <tr key={i}>
                            <td className="corr-label">{result.correlation.symbols[i].replace('.NS','')}</td>
                            {row.map((val, j) => (
                              <td key={j} className="corr-cell" style={{
                                background: val > 0 ? `rgba(0,200,150,${Math.abs(val)*0.7})` : `rgba(231,76,60,${Math.abs(val)*0.7})`,
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
            </>
          )}
        </div>
      </div>
    </div>
  );
}
