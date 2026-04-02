import axios from 'axios';

const BASE = 'http://localhost:8000/api';

const api = axios.create({ baseURL: BASE, timeout: 30000 });

// ── Market ────────────────────────────────────────────────────────────────────
export const getMarketStatus = () => api.get('/market/status').then(r => r.data);

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
export const sendChat = (message) => api.post('/agent/chat', { message }).then(r => r.data);
