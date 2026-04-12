import { useState, useEffect, useCallback } from 'react';
import './index.css';
import Sidebar from './components/Sidebar';
import Topbar from './components/Topbar';
import Dashboard from './pages/Dashboard';
import Portfolio from './pages/Portfolio';
import Watchlist from './pages/Watchlist';
import Fundamentals from './pages/Fundamentals';
import Assistant from './pages/Assistant';
import ProfilePage from './pages/Profile';
import Optimizer from './pages/Optimizer';
import Alerts from './pages/Alerts';
import MultiAsset from './pages/MultiAsset';
import Options from './pages/Options';
import Signals from './pages/Signals';
import { ToastProvider } from './context/ToastContext';
import { getStockList, getProfile } from './api';

function App() {
  const [page, setPage]           = useState('dashboard');
  const [stockList, setStockList] = useState([]);
  const [profile, setProfile]     = useState(null);
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    getStockList().then(setStockList).catch(() => {});
    getProfile().then(setProfile).catch(() => {});
  }, []);

  // Re-fetch profile when navigating to profile tab
  useEffect(() => {
    if (page === 'profile') {
      getProfile().then(setProfile).catch(() => {});
    }
  }, [page]);

  const handleNav = (p) => {
    setPage(p);
    setRefreshKey(k => k + 1);
  };

  const renderPage = () => {
    switch (page) {
      case 'dashboard':    return <Dashboard    key={`dash-${refreshKey}`} stockList={stockList}/>;
      case 'portfolio':    return <Portfolio    key={`port-${refreshKey}`} stockList={stockList}/>;
      case 'watchlist':    return <Watchlist    key={`wl-${refreshKey}`}   stockList={stockList}/>;
      case 'fundamentals': return <Fundamentals key={`fund-${refreshKey}`} stockList={stockList}/>;
      case 'assistant':    return <Assistant    key={`ai-${refreshKey}`}/>;
      case 'profile':      return <ProfilePage  key={`prof-${refreshKey}`}/>;
      case 'optimizer':    return <Optimizer    key={`opt-${refreshKey}`}  stockList={stockList}/>;
      case 'alerts':       return <Alerts       key={`alt-${refreshKey}`}  stockList={stockList}/>;
      case 'multiasset':   return <MultiAsset   key={`ma-${refreshKey}`}/>;
      case 'options':      return <Options      key={`opt2-${refreshKey}`}/>;
      case 'signals':      return <Signals      key={`sig-${refreshKey}`}  stockList={stockList}/>;
      default:             return <Dashboard    stockList={stockList}/>;
    }
  };

  return (
    <ToastProvider>
      <div className="layout">
        <Sidebar active={page} onNav={handleNav} profile={profile}/>
        <div className="main-content">
          <Topbar page={page} onRefresh={() => setRefreshKey(k => k + 1)}/>
          <div className="page-content">
            {renderPage()}
          </div>
        </div>
      </div>
    </ToastProvider>
  );
}

export default App;
