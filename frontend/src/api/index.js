import axios from 'axios';

const BASE = process.env.REACT_APP_API_BASE || 'http://localhost:8000/api';

const api = axios.create({ baseURL: BASE, timeout: 30000 });

// ── Market ────────────────────────────────────────────────────────────────────
export const getMarketStatus = () => api.get('/market/status').then(r => r.data);
export const getMarketOverview = () => api.get('/market/overview').then(r => r.data);

// ── Health ────────────────────────────────────────────────────────────────────
export const getHealthCheck = () => api.get('/health').then(r => r.data);

// ── Stocks ────────────────────────────────────────────────────────────────────
export const getStockList   = () => api.get('/stocks/list').then(r => r.data);
export const getSectors     = () => api.get('/stocks/sectors').then(r => r.data.sectors);
export const getStockPrice  = (symbol, period = '1mo') => api.get(`/stocks/${symbol}/price`, { params: { period } }).then(r => r.data);
export const getFundamentals = (symbol) => api.get(`/stocks/${symbol}/fundamentals`).then(r => r.data);
export const getCompare     = (symbol, compare, period) => api.get(`/stocks/${symbol}/compare`, { params: { compare, period } }).then(r => r.data);
export const getSectorComparison = (sector) => api.get(`/sector/${encodeURIComponent(sector)}/comparison`).then(r => r.data);
export const getNews        = (symbol) => api.get(`/stocks/${symbol}/news`).then(r => r.data);

// ── Portfolio ─────────────────────────────────────────────────────────────────
export const getPortfolio   = () => api.get('/portfolio').then(r => r.data);
export const addPortfolio   = (symbol) => api.post('/portfolio', { symbol });
export const removePortfolio = (symbol) => api.delete(`/portfolio/${symbol}`);

// ── Portfolio Optimization ───────────────────────────────────────────────────
export const optimizePortfolio = (data) => api.post('/portfolio/optimize', data, { timeout: 120000 }).then(r => r.data);

// ── Watchlist ─────────────────────────────────────────────────────────────────
export const getWatchlist   = () => api.get('/watchlist').then(r => r.data);
export const addWatchlist   = (item) => api.post('/watchlist', item);
export const removeWatchlist = (symbol) => api.delete(`/watchlist/${symbol}`);
export const updateNote     = (symbol, note) => api.patch(`/watchlist/${symbol}/note`, { note });

// ── Profile ───────────────────────────────────────────────────────────────────
export const getProfile     = () => api.get('/profile').then(r => r.data);
export const updateProfile  = (data) => api.put('/profile', data);
export const getProfileStats = () => api.get('/profile/stats').then(r => r.data);

// ── Agent ─────────────────────────────────────────────────────────────────────
export const sendChat = (message) => api.post('/agent/chat', { message }, { timeout: 120000 }).then(r => r.data);

// ── Alerts & Notifications ──────────────────────────────────────────────────
export const createAlert    = (data) => api.post('/alerts', data).then(r => r.data);
export const getAlerts      = (status) => api.get('/alerts', { params: status ? { status } : {} }).then(r => r.data);
export const deleteAlert    = (id) => api.delete(`/alerts/${id}`);
export const toggleAlert    = (id) => api.patch(`/alerts/${id}/toggle`).then(r => r.data);
export const getNotifications = (unreadOnly = false) => api.get('/notifications', { params: { unread_only: unreadOnly } }).then(r => r.data);
export const getUnreadCount = () => api.get('/notifications/unread-count').then(r => r.data.count);
export const markRead       = (id) => api.patch(`/notifications/${id}/read`);

// ── Multi-Asset: Fixed Income ────────────────────────────────────────────────
export const getTreasuryYields = () => api.get('/assets/fixed-income/yields').then(r => r.data);
export const getYieldCurve    = () => api.get('/assets/fixed-income/yield-curve').then(r => r.data);
export const getYieldHistory  = (maturity, period = '1y') => api.get(`/assets/fixed-income/history/${maturity}`, { params: { period } }).then(r => r.data);

// ── Multi-Asset: Commodities ─────────────────────────────────────────────────
export const getCommodities      = () => api.get('/assets/commodities').then(r => r.data);
export const getCommodityHistory = (commodity, period = '3mo') => api.get(`/assets/commodities/${commodity}/history`, { params: { period } }).then(r => r.data);

// ── Multi-Asset: Forex ───────────────────────────────────────────────────────
export const getForexRates   = () => api.get('/assets/forex').then(r => r.data);
export const getForexHistory = (pair, period = '3mo') => api.get(`/assets/forex/${pair}/history`, { params: { period } }).then(r => r.data);

// ── Multi-Asset: Cross-Asset ─────────────────────────────────────────────────
export const getCorrelation   = (period = '1y') => api.get('/assets/correlation', { params: { period } }).then(r => r.data);
export const getAssetPerformance = (period = '1y') => api.get('/assets/performance', { params: { period } }).then(r => r.data);

// ── Macro ─────────────────────────────────────────────────────────────────────
export const getMacroIndicators = () => api.get('/macro/indicators').then(r => r.data);
export const getMacroIndices = () => api.get('/macro/indices').then(r => r.data);

// ── Options ──────────────────────────────────────────────────────────────────
export const priceOption     = (data) => api.post('/options/price', data).then(r => r.data);
export const getOptionsChain = (symbol, expiry) => api.get(`/options/${symbol}/chain`, { params: expiry ? { expiry } : {} }).then(r => r.data);
export const getStrategies   = () => api.get('/options/strategies').then(r => r.data);
export const computeStrategy = (data) => api.post('/options/strategy', data).then(r => r.data);
export const computeTemplateStrategy = (data) => api.post('/options/strategy/template', data).then(r => r.data);

// ── Trading Signals ──────────────────────────────────────────────────────────
export const getSignals      = (symbol, period = '6mo') => api.get(`/signals/${symbol}`, { params: { period } }).then(r => r.data);
export const getSignalSummary = (symbol) => api.get(`/signals/${symbol}/summary`).then(r => r.data);
export const batchSignals    = (symbols) => api.post('/signals/batch', { symbols }).then(r => r.data);
