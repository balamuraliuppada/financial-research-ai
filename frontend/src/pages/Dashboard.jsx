import { useState, useEffect, useCallback } from 'react';
import { Search, Plus, Star, RefreshCw, TrendingUp, TrendingDown, AlertTriangle, ExternalLink } from 'lucide-react';
import { getStockPrice, getNews, addPortfolio, addWatchlist } from '../api';
import StockChart from '../components/StockChart';
import CompareChart from '../components/CompareChart';
import { useToast } from '../context/ToastContext';

const MARKET_TAPE_SYMBOLS = [
  'RELIANCE.NS',
  'HDFCBANK.NS',
  'INFY.NS',
  'ICICIBANK.NS',
  'SBIN.NS',
  'ITC.NS',
  'LT.NS',
];

function buildSparkline(candles = []) {
  const values = candles
    .map(c => Number(c.Close))
    .filter(v => Number.isFinite(v));

  if (values.length < 2) return '';

  const width = 92;
  const height = 28;
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;

  const points = values.map((value, index) => {
    const x = (index / (values.length - 1)) * width;
    const y = height - ((value - min) / range) * height;
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  });

  return `M ${points.join(' L ')}`;
}

function MetricCard({ label, value, sub, subType }) {
  return (
    <div className="metric-card fade-up">
      <div className="label">{label}</div>
      <div className="value">{value ?? '—'}</div>
      {sub && <div className={`sub ${subType || 'neu'}`}>{sub}</div>}
    </div>
  );
}

function SentimentBar({ score }) {
  const pct = ((score + 1) / 2) * 100;
  const color = score > 0.1 ? 'var(--accent)' : score < -0.1 ? 'var(--red)' : 'var(--accent2)';
  return (
    <div>
      <div className="flex justify-between" style={{ marginBottom: 6, fontSize: 12, fontFamily: 'var(--font-mono)' }}>
        <span style={{ color: 'var(--text-3)' }}>Sentiment Score</span>
        <span style={{ color }}>{score > 0.1 ? '📈 Positive' : score < -0.1 ? '📉 Negative' : '➡ Neutral'} ({score.toFixed(2)})</span>
      </div>
      <div className="rsi-bar-track">
        <div className="rsi-bar-fill" style={{ width: `${pct}%`, background: color }}/>
      </div>
    </div>
  );
}

export default function Dashboard({ stockList }) {
  const toast = useToast();
  const [search, setSearch]         = useState('');
  const [selected, setSelected]     = useState(null);
  const [period, setPeriod]         = useState('1mo');
  const [stockData, setStockData]   = useState(null);
  const [news, setNews]             = useState(null);
  const [loadChart, setLoadChart]   = useState(false);
  const [loadNews, setLoadNews]     = useState(false);
  const [showCompare, setShowCompare] = useState(false);
  const [compareWith, setCompareWith] = useState(null);
  const [marketTape, setMarketTape] = useState([]);
  const [tapeLoading, setTapeLoading] = useState(false);

  const filtered = stockList.filter(s =>
    s.name.toLowerCase().includes(search.toLowerCase()) ||
    s.symbol.toLowerCase().includes(search.toLowerCase())
  );

  const load = useCallback(async (sym, per) => {
    if (!sym) return;
    setLoadChart(true);
    try {
      const d = await getStockPrice(sym, per);
      setStockData(d);
    } catch (e) {
      toast('Failed to load stock data', 'error');
    } finally {
      setLoadChart(false);
    }
  }, [toast]);

  const loadNewsData = useCallback(async (sym) => {
    setLoadNews(true);
    try {
      const d = await getNews(sym);
      setNews(d);
    } catch {}
    finally { setLoadNews(false); }
  }, []);

  useEffect(() => {
    if (!stockList.length || selected) return;
    const defaultStock = stockList.find(s => s.symbol === 'RELIANCE.NS') || stockList[0];
    if (defaultStock) selectStock(defaultStock);
  }, [stockList, selected]);

  useEffect(() => {
    if (!stockList.length) return;

    const loadTape = async () => {
      setTapeLoading(true);
      try {
        const preferred = MARKET_TAPE_SYMBOLS
          .map(sym => stockList.find(s => s.symbol === sym))
          .filter(Boolean);
        const fallback = stockList.filter(
          s => !MARKET_TAPE_SYMBOLS.includes(s.symbol)
        );

        const picks = [];
        const seen = new Set();

        [...preferred, ...fallback].forEach((stock) => {
          if (!stock || seen.has(stock.symbol) || picks.length >= 8) return;
          seen.add(stock.symbol);
          picks.push(stock);
        });

        const data = await Promise.all(
          picks.map(async (stock) => {
            try {
              const quote = await getStockPrice(stock.symbol, '5d');
              return {
                ...stock,
                current_price: quote.current_price,
                change: quote.change,
                change_pct: quote.change_pct,
                sparkline: buildSparkline(quote.candles),
              };
            } catch {
              return {
                ...stock,
                current_price: null,
                change: null,
                change_pct: null,
                sparkline: '',
              };
            }
          })
        );
        setMarketTape(data);
      } finally {
        setTapeLoading(false);
      }
    };

    loadTape();
  }, [stockList]);

  const topMovers = [...marketTape]
    .filter(s => typeof s.change_pct === 'number')
    .sort((a, b) => Math.abs(b.change_pct) - Math.abs(a.change_pct))
    .slice(0, 4);

  const selectStock = (stock) => {
    setSelected(stock);
    setSearch('');
    setStockData(null);
    setNews(null);
    setShowCompare(false);
    load(stock.symbol, period);
    loadNewsData(stock.symbol);
  };

  const handlePeriod = (p) => {
    setPeriod(p);
    if (selected) load(selected.symbol, p);
  };

  const handleAddPortfolio = async () => {
    if (!selected) return;
    await addPortfolio(selected.symbol);
    toast(`${selected.symbol} added to portfolio`);
  };

  const handleAddWatchlist = async () => {
    if (!selected) return;
    await addWatchlist({ symbol: selected.symbol, name: selected.name, sector: selected.sector });
    toast(`${selected.symbol} added to watchlist`);
  };

  const rsiColor = (v) => {
    if (!v) return 'neu';
    if (v > 70) return 'neg';
    if (v < 30) return 'pos';
    return 'neu';
  };

  return (
    <div>
      {/* Market tape */}
      <div className="market-tape-wrap mb-20 fade-up">
        <div className="market-tape-header">
          <div className="market-tape-status">{tapeLoading ? 'Refreshing quotes...' : 'Live tape'}</div>
        </div>
        <div className="market-tape-scroller">
          {marketTape.map((s) => (
            <button
              key={s.symbol}
              className={`tape-pill ${selected?.symbol === s.symbol ? 'active' : ''}`}
              onClick={() => selectStock(s)}
            >
              <div className="tape-pill-top">
                <span className="sym">{s.symbol.replace('.NS', '')}</span>
                <span className={typeof s.change_pct === 'number' ? (s.change_pct >= 0 ? 'chg up' : 'chg dn') : 'chg'}>
                  {typeof s.change_pct === 'number' ? `${s.change_pct >= 0 ? '+' : ''}${s.change_pct}%` : '--'}
                </span>
              </div>
              <div className="tape-pill-bottom">
                <span className="pr">{typeof s.current_price === 'number' ? `₹${s.current_price.toLocaleString('en-IN')}` : '—'}</span>
                <svg className="tape-spark" viewBox="0 0 92 28" preserveAspectRatio="none" aria-hidden="true">
                  <path d={s.sparkline || 'M 0 14 L 92 14'} />
                </svg>
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Search + Stock selector */}
      <div className="card mb-20 fade-up">
        <div className="flex items-center gap-12 flex-wrap">
          <div className="search-wrapper" style={{ maxWidth: 400, flex: 1 }}>
            <Search size={15}/>
            <input
              className="input"
              placeholder="Search stocks by name or symbol…"
              value={search}
              onChange={e => setSearch(e.target.value)}
            />
          </div>
        </div>

        {/* Dropdown results */}
        {search && (
          <div style={{
            marginTop: 8, background: 'var(--bg-2)', borderRadius: 'var(--radius)',
            border: '1px solid var(--border)', maxHeight: 280, overflowY: 'auto'
          }}>
            {filtered.slice(0, 12).map(s => (
              <div key={s.symbol}
                onClick={() => selectStock(s)}
                style={{ padding: '11px 16px', cursor: 'pointer', borderBottom: '1px solid rgba(255,255,255,0.03)', transition: 'background 0.15s' }}
                onMouseEnter={e => e.currentTarget.style.background = 'var(--bg-3)'}
                onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
              >
                <div className="flex justify-between items-center">
                  <div>
                    <span style={{ fontWeight: 600, color: 'var(--text-1)' }}>{s.name}</span>
                    <span style={{ marginLeft: 8, fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--text-3)' }}>{s.symbol}</span>
                  </div>
                  <span className="tag tag-sector">{s.sector}</span>
                </div>
              </div>
            ))}
            {filtered.length === 0 && <div style={{ padding: '16px', color: 'var(--text-3)', fontSize: 13 }}>No stocks found</div>}
          </div>
        )}
      </div>

      {!!topMovers.length && (
        <div className="movers-grid mb-20 fade-up">
          {topMovers.map((m) => (
            <button key={m.symbol} className="mover-card" onClick={() => selectStock(m)}>
              <div className="flex justify-between items-center">
                <span className="name">{m.name}</span>
                <span className={`delta ${m.change_pct >= 0 ? 'up' : 'dn'}`}>
                  {m.change_pct >= 0 ? <TrendingUp size={12}/> : <TrendingDown size={12}/>} {m.change_pct >= 0 ? '+' : ''}{m.change_pct}%
                </span>
              </div>
              <div className="flex justify-between items-center mt-8">
                <span className="sym">{m.symbol}</span>
                <span className="pr">₹{m.current_price?.toLocaleString('en-IN')}</span>
              </div>
            </button>
          ))}
        </div>
      )}

      {!selected && (
        <div className="empty-state fade-up">
          <TrendingUp size={56} style={{ margin: '0 auto 16px', display: 'block' }}/>
          <p style={{ fontSize: 16, fontWeight: 600, color: 'var(--text-2)', marginBottom: 6 }}>Select a stock to begin</p>
          <p>Search above for any NSE-listed stock</p>
        </div>
      )}

      {selected && (
        <>
          {/* Header */}
          <div className="flex justify-between items-center mb-20 fade-up">
            <div>
              <div className="flex items-center gap-10 flex-wrap">
                <h2 style={{ fontFamily: 'var(--font-display)', fontSize: 22, fontWeight: 800, color: 'var(--text-1)' }}>
                  {stockData?.name || selected.name}
                </h2>
                <div className="flex gap-8 flex-wrap">
                  <button className="btn btn-ghost btn-sm" onClick={handleAddPortfolio}><Plus size={14}/> Portfolio</button>
                  <button className="btn btn-ghost btn-sm" onClick={handleAddWatchlist}><Star size={14}/> Watchlist</button>
                  <button className="btn btn-ghost btn-sm" onClick={() => load(selected.symbol, period)}><RefreshCw size={14}/> Refresh</button>
                  <button className="btn btn-ghost btn-sm" onClick={() => setShowCompare(v => !v)}>
                    {showCompare ? 'Hide Compare' : 'Compare'}
                  </button>
                </div>
              </div>
              <div className="flex gap-8 mt-4 items-center flex-wrap">
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: 12, color: 'var(--text-3)' }}>{selected.symbol}</span>
                <span className="tag tag-sector">{selected.sector}</span>
              </div>
            </div>
            {stockData && (
              <div style={{ textAlign: 'right' }}>
                <div style={{ fontFamily: 'var(--font-mono)', fontSize: 32, fontWeight: 700, color: 'var(--text-1)' }}>
                  ₹{stockData.current_price.toLocaleString('en-IN')}
                </div>
                <div className={`flex gap-6 items-center justify-end mt-4 ${stockData.change >= 0 ? 'price-pos' : 'price-neg'}`}>
                  {stockData.change >= 0 ? <TrendingUp size={14}/> : <TrendingDown size={14}/>}
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: 14 }}>
                    {stockData.change >= 0 ? '+' : ''}{stockData.change} ({stockData.change_pct >= 0 ? '+' : ''}{stockData.change_pct}%)
                  </span>
                </div>
              </div>
            )}
          </div>

          {/* Metrics */}
          {stockData && (
            <div className="metric-grid mb-20">
              <MetricCard label="Period High"  value={`₹${stockData.period_high}`}/>
              <MetricCard label="Period Low"   value={`₹${stockData.period_low}`}/>
              <MetricCard label="Market Cap"   value={stockData.market_cap}/>
              <MetricCard label="Volume"       value={stockData.volume?.toLocaleString('en-IN')}/>
              <MetricCard label="RSI (14-day)" value={stockData.rsi}
                sub={stockData.rsi > 70 ? 'Overbought ⚠' : stockData.rsi < 30 ? 'Oversold 💡' : 'Neutral'}
                subType={rsiColor(stockData.rsi)}/>
              <MetricCard label="MA (20-day)"  value={stockData.ma20 ? `₹${stockData.ma20}` : '—'}/>
            </div>
          )}

          {/* RSI warning */}
          {stockData?.rsi > 70 && (
            <div className="flex gap-8 items-center mb-16 fade-up" style={{ background:'var(--red-dim)', border:'1px solid rgba(255,77,109,0.2)', borderRadius:'var(--radius)', padding:'12px 16px' }}>
              <AlertTriangle size={16} color="var(--red)"/>
              <span style={{ fontSize:13, color:'var(--red)' }}>RSI above 70 — stock may be <strong>overbought</strong></span>
            </div>
          )}
          {stockData?.rsi < 30 && (
            <div className="flex gap-8 items-center mb-16 fade-up" style={{ background:'var(--accent-dim)', border:'1px solid rgba(0,210,150,0.2)', borderRadius:'var(--radius)', padding:'12px 16px' }}>
              <TrendingUp size={16} color="var(--accent)"/>
              <span style={{ fontSize:13, color:'var(--accent)' }}>RSI below 30 — stock may be <strong>oversold</strong></span>
            </div>
          )}

          {/* Main chart */}
          <div className="mb-20">
            <StockChart data={stockData} period={period} onPeriodChange={handlePeriod} loading={loadChart}/>
          </div>

          {/* Compare */}
          {showCompare && (
            <div className="card mb-20 fade-up">
              <div className="card-title">Compare With</div>
              <div className="flex gap-12 items-center mb-16 flex-wrap">
                <select className="input" style={{ width: 260 }} onChange={e => setCompareWith(e.target.value)} value={compareWith || ''}>
                  <option value="">Select a stock…</option>
                  {stockList.filter(s => s.symbol !== selected.symbol).map(s => (
                    <option key={s.symbol} value={s.symbol}>{s.name}</option>
                  ))}
                </select>
              </div>
              {compareWith && (
                <CompareChart symbol1={selected.symbol} symbol2={compareWith} period={period}
                  name1={stockData?.name || selected.name}
                  name2={stockList.find(s => s.symbol === compareWith)?.name || compareWith}/>
              )}
            </div>
          )}

          {/* News */}
          <div className="card fade-up">
            <div className="card-title">News & Sentiment</div>
            {loadNews ? (
              <div className="flex gap-8 items-center" style={{ padding: '16px 0' }}>
                <div className="spinner"/>
                <span className="text-muted text-sm">Loading news…</span>
              </div>
            ) : news ? (
              <>
                <SentimentBar score={news.sentiment}/>
                <div className="flex-col gap-8 mt-16" style={{ display: 'flex' }}>
                  {news.articles.map((art, i) => (
                    <a key={i} href={art.url} target="_blank" rel="noreferrer" className="news-card">
                      <div className="flex justify-between items-center">
                        <span className="tag tag-neu">{art.source}</span>
                        <div className="flex gap-4 items-center">
                          <span className={`tag ${art.sentiment > 0.1 ? 'tag-pos' : art.sentiment < -0.1 ? 'tag-neg' : 'tag-neu'}`}>
                            {art.sentiment > 0.1 ? '▲' : art.sentiment < -0.1 ? '▼' : '●'} {art.sentiment.toFixed(2)}
                          </span>
                          <ExternalLink size={11} color="var(--text-3)"/>
                        </div>
                      </div>
                      <div className="headline">{art.title}</div>
                      <div className="meta">
                        <span>{new Date(art.publishedAt).toLocaleDateString('en-IN')}</span>
                      </div>
                    </a>
                  ))}
                </div>
              </>
            ) : (
              <div className="text-muted text-sm">News unavailable</div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
