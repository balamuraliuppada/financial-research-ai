import { useState, useEffect, useCallback } from 'react';
import { User, Save, RefreshCw, Briefcase, Star, Search, TrendingUp } from 'lucide-react';
import { getProfile, updateProfile, getProfileStats } from '../api';
import { useToast } from '../context/ToastContext';

const COLORS = ['#00d296','#f7a035','#4b91f7','#a78bfa','#f472b6','#34d399','#fb923c','#e879f9','#22d3ee'];
const RISKS  = ['Conservative','Moderate','Aggressive','Very Aggressive'];
const GOALS  = ['Wealth Creation','Retirement Planning','Short-term Gains','Passive Income','Capital Preservation'];
const LEVELS = ['Beginner','Intermediate','Advanced','Expert'];
const SECTORS= [
  'Information Technology','Banking & Finance','Energy & Conglomerates','Automobile',
  'Pharmaceuticals','FMCG','Metals & Mining','Infrastructure','Telecom',
];

export default function ProfilePage() {
  const toast = useToast();
  const [profile, setProfile] = useState({ name:'', email:'', phone:'', risk_profile:'Moderate', investment_goal:'Wealth Creation', experience:'Intermediate', preferred_sectors:[], avatar_color:'#00d296' });
  const [stats, setStats]     = useState(null);
  const [saving, setSaving]   = useState(false);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [p, s] = await Promise.all([getProfile(), getProfileStats()]);
      setProfile(p);
      setStats(s);
    } catch { toast('Failed to load profile', 'error'); }
    finally { setLoading(false); }
  }, [toast]);

  useEffect(() => { load(); }, [load]);

  const save = async () => {
    setSaving(true);
    try {
      await updateProfile(profile);
      toast('Profile saved successfully');
    } catch { toast('Failed to save profile', 'error'); }
    finally { setSaving(false); }
  };

  const toggleSector = (s) => {
    const cur = profile.preferred_sectors || [];
    const next = cur.includes(s) ? cur.filter(x=>x!==s) : [...cur, s];
    setProfile(p => ({ ...p, preferred_sectors: next }));
  };

  const initials = (profile.name||'IN').split(' ').map(w=>w[0]).join('').slice(0,2).toUpperCase();

  if (loading) return (
    <div style={{ display:'flex', alignItems:'center', justifyContent:'center', padding:60 }}>
      <div className="spinner spinner-lg"/>
    </div>
  );

  return (
    <div>
      {/* Profile Header */}
      <div className="card mb-20 fade-up">
        <div className="flex gap-20 items-center flex-wrap">
          <div className="avatar" style={{ background: profile.avatar_color || '#00d296' }}>{initials}</div>
          <div style={{ flex:1 }}>
            <div style={{ fontFamily:'var(--font-display)', fontSize:22, fontWeight:800, color:'var(--text-1)' }}>
              {profile.name || 'Your Name'}
            </div>
            <div style={{ color:'var(--text-2)', marginTop:4, fontSize:13 }}>{profile.email || 'your@email.com'}</div>
            <div className="flex gap-8 mt-8 flex-wrap">
              <span className="tag tag-sector">{profile.risk_profile}</span>
              <span className="tag tag-neu">{profile.investment_goal}</span>
              <span className="tag tag-neu">{profile.experience}</span>
            </div>
          </div>
          <button className="btn btn-primary" onClick={save} disabled={saving}>
            {saving ? <><div className="spinner" style={{width:14,height:14,borderWidth:2}}/> Saving…</> : <><Save size={15}/> Save Profile</>}
          </button>
        </div>
      </div>

      {/* Stats */}
      {stats && (
        <div className="grid-3 mb-20 fade-up fade-up-1">
          <div className="stat-block">
            <Briefcase size={22} color="var(--accent)" style={{ margin:'0 auto 10px' }}/>
            <div className="stat-num">{stats.portfolio_count}</div>
            <div className="stat-lbl">Portfolio Holdings</div>
          </div>
          <div className="stat-block">
            <Star size={22} color="var(--accent2)" style={{ margin:'0 auto 10px' }}/>
            <div className="stat-num">{stats.watchlist_count}</div>
            <div className="stat-lbl">Watchlist Stocks</div>
          </div>
          <div className="stat-block">
            <Search size={22} color="var(--blue)" style={{ margin:'0 auto 10px' }}/>
            <div className="stat-num">{stats.total_searches}</div>
            <div className="stat-lbl">Total Searches</div>
          </div>
        </div>
      )}

      <div className="profile-grid fade-up fade-up-2">
        {/* Personal Info */}
        <div className="card">
          <div className="card-title">Personal Information</div>
          <div className="flex-col gap-16" style={{ display:'flex' }}>
            <div className="input-group">
              <label className="input-label">Full Name</label>
              <input className="input" value={profile.name||''} onChange={e=>setProfile(p=>({...p,name:e.target.value}))} placeholder="Your full name"/>
            </div>
            <div className="input-group">
              <label className="input-label">Email Address</label>
              <input className="input" type="email" value={profile.email||''} onChange={e=>setProfile(p=>({...p,email:e.target.value}))} placeholder="your@email.com"/>
            </div>
            <div className="input-group">
              <label className="input-label">Phone Number</label>
              <input className="input" type="tel" value={profile.phone||''} onChange={e=>setProfile(p=>({...p,phone:e.target.value}))} placeholder="+91 XXXXX XXXXX"/>
            </div>

            {/* Avatar Color */}
            <div>
              <div className="input-label" style={{ marginBottom:10 }}>Avatar Color</div>
              <div className="flex gap-8 flex-wrap">
                {COLORS.map(c => (
                  <div key={c} onClick={() => setProfile(p=>({...p,avatar_color:c}))}
                    style={{
                      width:32, height:32, borderRadius:'50%', background:c, cursor:'pointer',
                      border: profile.avatar_color===c ? '3px solid white' : '3px solid transparent',
                      boxShadow: profile.avatar_color===c ? `0 0 0 2px ${c}` : 'none',
                      transition:'all 0.15s',
                    }}
                  />
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Investment Preferences */}
        <div className="card">
          <div className="card-title">Investment Preferences</div>
          <div className="flex-col gap-16" style={{ display:'flex' }}>
            <div className="input-group">
              <label className="input-label">Risk Profile</label>
              <select className="input" value={profile.risk_profile||'Moderate'} onChange={e=>setProfile(p=>({...p,risk_profile:e.target.value}))}>
                {RISKS.map(r=><option key={r} value={r}>{r}</option>)}
              </select>
            </div>
            <div className="input-group">
              <label className="input-label">Investment Goal</label>
              <select className="input" value={profile.investment_goal||''} onChange={e=>setProfile(p=>({...p,investment_goal:e.target.value}))}>
                {GOALS.map(g=><option key={g} value={g}>{g}</option>)}
              </select>
            </div>
            <div className="input-group">
              <label className="input-label">Experience Level</label>
              <select className="input" value={profile.experience||''} onChange={e=>setProfile(p=>({...p,experience:e.target.value}))}>
                {LEVELS.map(l=><option key={l} value={l}>{l}</option>)}
              </select>
            </div>
          </div>
        </div>
      </div>

      {/* Preferred Sectors */}
      <div className="card mt-20 fade-up fade-up-3">
        <div className="card-title">Preferred Sectors</div>
        <div style={{ fontSize:12, color:'var(--text-3)', marginBottom:12 }}>Select the sectors you're most interested in</div>
        <div className="sector-chips">
          {SECTORS.map(s => (
            <div key={s} className={`sector-chip ${(profile.preferred_sectors||[]).includes(s)?'selected':''}`} onClick={()=>toggleSector(s)}>
              {s}
            </div>
          ))}
        </div>
      </div>

      {/* Activity */}
      <div className="card mt-20 fade-up">
        <div className="card-title">Account Activity</div>
        <div style={{ display:'grid', gridTemplateColumns:'repeat(auto-fill, minmax(200px,1fr))', gap:14 }}>
          <div className="metric-card">
            <div className="label">Member Since</div>
            <div style={{ fontFamily:'var(--font-mono)', fontSize:14, color:'var(--text-1)' }}>
              {profile.created_at ? new Date(profile.created_at).toLocaleDateString('en-IN',{day:'2-digit',month:'short',year:'numeric'}) : '—'}
            </div>
          </div>
          <div className="metric-card">
            <div className="label">Risk Level</div>
            <div style={{ fontFamily:'var(--font-mono)', fontSize:14, color:'var(--accent)' }}>{profile.risk_profile || 'Moderate'}</div>
          </div>
          <div className="metric-card">
            <div className="label">Preferred Sectors</div>
            <div style={{ fontFamily:'var(--font-mono)', fontSize:14, color:'var(--text-1)' }}>
              {(profile.preferred_sectors||[]).length || 0} selected
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
