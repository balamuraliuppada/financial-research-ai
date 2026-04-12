import { useState, useEffect } from 'react';
import { getSignals, batchSignals } from '../api';

const SIGNAL_COLORS = {
  'BUY': '#00c896',
  'STRONG BUY': '#00e5a0',
  'SELL': '#e74c3c',
  'STRONG SELL': '#c0392b',
  'HOLD': '#f7931a',
};

export default function Signals({ stockList }) {
  const [symbol, setSymbol] = useState('');
  const [result, setResult] = useState(null);
  const [batchResults, setBatchResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [batchLoading, setBatchLoading] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const stocks = stockList || [];

  const filteredStocks = stocks.filter(s =>
    s.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    s.symbol.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const analyzeStock = async (sym) => {
    setSymbol(sym);
    setLoading(true);
    try {
      const data = await getSignals(sym);
      setResult(data);
    } catch (e) {
      alert('Error: ' + (e.response?.data?.detail || e.message));
    } finally {
      setLoading(false);
    }
  };

  const runBatchScan = async () => {
    const syms = stocks.slice(0, 15).map(s => s.symbol);
    setBatchLoading(true);
    try {
      const data = await batchSignals(syms);
      setBatchResults(data.filter(d => !d.error));
    } catch (e) {
      console.error(e);
    } finally {
      setBatchLoading(false);
    }
  };

  const signalIcon = (signal) => {
    if (signal.includes('BUY')) return '🟢';
    if (signal.includes('SELL')) return '🔴';
    return '🟡';
  };

  const confidenceMeter = (confidence, signal) => {
    const color = SIGNAL_COLORS[signal] || '#999';
    return (
      <div className="confidence-meter">
        <svg viewBox="0 0 120 60" className="gauge-svg">
          <path d="M 10 55 A 50 50 0 0 1 110 55" fill="none" stroke="#333" strokeWidth="8" strokeLinecap="round" />
          <path d="M 10 55 A 50 50 0 0 1 110 55" fill="none" stroke={color} strokeWidth="8" strokeLinecap="round"
                strokeDasharray={`${confidence * 1.57} 157`} />
          <text x="60" y="45" textAnchor="middle" fill="#fff" fontSize="16" fontWeight="bold">{confidence}%</text>
          <text x="60" y="58" textAnchor="middle" fill={color} fontSize="10">{signal}</text>
        </svg>
      </div>
    );
  };

  return (
    <div className="signals-page">
      <h2>🎯 Trading Signals</h2>
      <p className="page-subtitle">Multi-indicator analysis with composite scoring</p>

      <div className="signals-grid">
        {/* Stock Selector */}
        <div className="card signal-selector">
          <h3>Select Stock</h3>
          <input type="text" placeholder="Search..." value={searchTerm}
                 onChange={e => setSearchTerm(e.target.value)} className="search-input" />
          <div className="stock-list-scroll">
            {filteredStocks.map(s => (
              <div key={s.symbol}
                   className={`stock-list-item ${symbol === s.symbol ? 'active' : ''}`}
                   onClick={() => analyzeStock(s.symbol)}>
                <span className="stock-sym">{s.symbol.replace('.NS','')}</span>
                <span className="stock-name">{s.name}</span>
              </div>
            ))}
          </div>
          <button className="btn-secondary full-width" onClick={runBatchScan} disabled={batchLoading}>
            {batchLoading ? '⏳ Scanning...' : '🔍 Scan All Stocks'}
          </button>
        </div>

        {/* Results */}
        <div className="signal-results">
          {!result && !loading && batchResults.length === 0 && (
            <div className="card empty-state">
              <div className="empty-icon">🎯</div>
              <h3>Select a stock to analyze</h3>
              <p>Or scan all stocks for a quick overview of buy/sell signals</p>
            </div>
          )}

          {loading && (
            <div className="card empty-state">
              <div className="loading-spinner"></div>
              <h3>Analyzing {symbol}...</h3>
              <p>Computing 9 technical indicators</p>
            </div>
          )}

          {result && !loading && (
            <>
              {/* Hero */}
              <div className="card signal-hero">
                <div className="signal-hero-left">
                  <h3>{result.symbol}</h3>
                  <div className="signal-price">₹{result.current_price}</div>
                  <div className={`signal-change ${result.price_change >= 0 ? 'up' : 'down'}`}>
                    {result.price_change >= 0 ? '▲' : '▼'} ₹{Math.abs(result.price_change)} ({result.price_change_pct}%)
                  </div>
                </div>
                <div className="signal-hero-right">
                  {confidenceMeter(result.composite.confidence, result.composite.signal)}
                </div>
              </div>

              {/* Composite Summary */}
              <div className="metrics-row">
                <div className="metric-card accent-green">
                  <div className="metric-value">{result.composite.buy_signals}</div>
                  <div className="metric-label">Buy Signals</div>
                </div>
                <div className="metric-card accent-red">
                  <div className="metric-value">{result.composite.sell_signals}</div>
                  <div className="metric-label">Sell Signals</div>
                </div>
                <div className="metric-card accent-orange">
                  <div className="metric-value">{result.composite.hold_signals}</div>
                  <div className="metric-label">Hold Signals</div>
                </div>
                <div className="metric-card accent-blue">
                  <div className="metric-value">{result.composite.score.toFixed(3)}</div>
                  <div className="metric-label">Composite Score</div>
                </div>
              </div>

              {/* Individual Signals */}
              <div className="card">
                <h3>Signal Breakdown</h3>
                <div className="signal-breakdown">
                  {result.signals.map((sig, i) => (
                    <div key={i} className={`signal-row ${sig.signal.toLowerCase()}`}>
                      <span className="signal-name-col">
                        {signalIcon(sig.signal)} {sig.name}
                      </span>
                      <span className={`signal-badge ${sig.signal.toLowerCase()}`}>
                        {sig.signal}
                      </span>
                      <div className="signal-strength-bar">
                        <div className="strength-fill" style={{
                          width: `${(sig.strength || 0) * 100}%`,
                          background: SIGNAL_COLORS[sig.signal] || '#999',
                        }}></div>
                      </div>
                      <span className="signal-reason">{sig.reason}</span>
                    </div>
                  ))}
                </div>
              </div>
            </>
          )}

          {/* Batch Results */}
          {batchResults.length > 0 && !result && (
            <div className="card">
              <h3>Stock Scanner Results</h3>
              <div className="batch-grid">
                {batchResults.sort((a, b) => (b.score || 0) - (a.score || 0)).map((r, i) => (
                  <div key={i} className={`batch-card ${r.signal?.includes('BUY') ? 'buy' : r.signal?.includes('SELL') ? 'sell' : 'hold'}`}
                       onClick={() => analyzeStock(r.symbol)}>
                    <div className="batch-symbol">{r.symbol?.replace('.NS','')}</div>
                    <div className="batch-signal">{signalIcon(r.signal || 'HOLD')} {r.signal}</div>
                    <div className="batch-confidence">{r.confidence}%</div>
                    <div className="batch-price">₹{r.price}</div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
