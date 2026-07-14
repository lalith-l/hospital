import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Activity, Clock, MapPin, CheckCircle, AlertTriangle, TrendingUp, Users } from 'lucide-react';
import { AuroraBackground } from './components/ui/aurora-background';

interface Alert {
  id: string;
  session_id: string;
  predicted_condition: string;
  urgency_level: number;
  patient_city: string;
  patient_pincode: string;
  image_evidence_url: string | null;
  pdf_url: string | null;
  status: string;
  created_at: string;
}

function HospitalDashboard() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [authHeader, setAuthHeader] = useState('');
  const [hospitalId, setHospitalId] = useState('h1');
  const [loadStatus, setLoadStatus] = useState<any>(null);

  const navigate = useNavigate();

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const apiUrl = 'https://hospital-tp5s.onrender.com';
      const res = await fetch(`${apiUrl}/api/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password })
      });
      if (res.ok) {
        const data = await res.json();
        
        // Save for websocket/routing
        localStorage.setItem('hospital_token', data.token);
        
        if (data.role === 'doctor') {
            navigate('/hospital/map');
            return;
        }
        
        setAuthHeader(`Bearer ${data.token}`);
        if (data.hospital_id) {
            setHospitalId(data.hospital_id);
        }
        setIsAuthenticated(true);
      } else {
        alert("Invalid credentials");
      }
    } catch (e) {
      console.error(e);
      alert("Login failed");
    }
  };

  const fetchAlerts = async () => {
    if (!authHeader) return;
    try {
      const apiUrl = 'https://hospital-tp5s.onrender.com';
      const response = await fetch(`${apiUrl}/api/alerts`, {
        headers: {
          'Authorization': authHeader
        }
      });
      if (response.ok) {
        const data = await response.json();
        setAlerts(data);
      }
    } catch (e) {
      console.error("Failed to fetch alerts", e);
    }
  };

  const fetchLoad = async () => {
    if (!authHeader) return;
    try {
      // Use the dynamically set hospitalId from login
      const apiUrl = 'https://hospital-tp5s.onrender.com';
      const response = await fetch(`${apiUrl}/api/hospital/load?hospital_id=${hospitalId}`, {
        headers: {
          'Authorization': authHeader
        }
      });
      if (response.ok) {
        const data = await response.json();
        setLoadStatus(data);
      }
    } catch (e) {
      console.error("Failed to fetch load status", e);
    }
  };

  useEffect(() => {
    if (isAuthenticated) {
      fetchAlerts();
      fetchLoad();
      const interval = setInterval(() => {
        fetchAlerts();
        fetchLoad();
      }, 10000); // Poll every 10s
      return () => clearInterval(interval);
    }
  }, [isAuthenticated, authHeader]);

  const handleAcknowledge = async (alertId: string) => {
    try {
      const apiUrl = 'https://hospital-tp5s.onrender.com';
      await fetch(`${apiUrl}/api/alerts/${alertId}/acknowledge`, {
        method: 'POST',
        headers: {
          'Authorization': authHeader
        }
      });
      // Refresh feed immediately
      fetchAlerts();
    } catch (e) {
      console.error("Failed to acknowledge alert", e);
    }
  };

  if (!isAuthenticated) {
    return (
      <AuroraBackground showRadialGradient={true}>
        <div className="flex h-screen items-center justify-center p-4 relative z-10 w-full text-white">
          <div className="glass-panel p-8 rounded-3xl w-full max-w-md bg-slate-900/50 backdrop-blur-md border border-white/10">
            <div className="flex justify-center mb-6">
              <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-blue-500 to-indigo-500 flex items-center justify-center shadow-lg">
                <Activity className="text-white w-7 h-7" />
              </div>
            </div>
            <h2 className="text-2xl font-bold text-center mb-8">Hospital Portal Login</h2>
            <form onSubmit={handleLogin} className="space-y-4">
              <div>
                <p className="text-xs text-slate-400 mb-1 text-left">Username: manipal_reception</p>
                <input
                  type="text"
                  placeholder="Username (manipal_reception)"
                  value={username}
                  onChange={e => setUsername(e.target.value)}
                  className="w-full bg-slate-800/50 border border-white/10 rounded-xl p-3 text-white outline-none focus:border-blue-500"
                />
              </div>
              <div>
                <p className="text-xs text-slate-400 mb-1 text-left">Password: aegis2024 (Reception) / doctor123 (Doctor)</p>
                <input
                  type="password"
                  placeholder="Password (aegis2024)"
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  className="w-full bg-slate-800/50 border border-white/10 rounded-xl p-3 text-white outline-none focus:border-blue-500"
                />
              </div>
              <button type="submit" className="w-full bg-blue-600 hover:bg-blue-500 text-white font-semibold rounded-xl py-3 mt-4 transition-colors">
                Access Dashboard
              </button>
            </form>
          </div>
        </div>
      </AuroraBackground>
    );
  }

  return (
    <AuroraBackground showRadialGradient={true}>
      <div className="min-h-screen p-8 relative z-10 w-full text-white">
        <div className="max-w-5xl mx-auto">
          <header className="flex items-center justify-between mb-8 bg-slate-900/40 p-4 rounded-2xl border border-white/10 backdrop-blur-md">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-blue-500 to-indigo-500 flex items-center justify-center shadow-lg">
                <Activity className="text-white w-7 h-7" />
              </div>
              <div>
                <h1 className="text-2xl font-bold">Manipal Hospital</h1>
                <p className="text-slate-400">AEGIS Incoming Alerts Dashboard</p>
              </div>
            </div>
            <div className="flex items-center gap-2 text-sm text-green-400 bg-green-500/10 px-4 py-2 rounded-full border border-green-500/20">
              <span className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
              Live Feed Active
            </div>
          </header>

          {/* Current Load Status Widget */}
          {loadStatus && (
            <div className="mb-8 glass-panel rounded-2xl p-6 border border-white/10 flex flex-col md:flex-row items-center justify-between gap-6 bg-slate-900/40 backdrop-blur-md">
              <div>
                <h2 className="text-sm font-bold text-slate-400 uppercase tracking-wider mb-1">Current Capacity Load</h2>
                <div className="flex items-center gap-3">
                  <span className={`text-3xl font-black ${
                    loadStatus.load === 'High' ? 'text-red-400' : loadStatus.load === 'Medium' ? 'text-orange-400' : 'text-green-400'
                  }`}>
                    {loadStatus.load}
                  </span>
                  {loadStatus.method === 'baseline_comparison' && (
                    <span className="text-sm bg-white/10 px-3 py-1 rounded-full border border-white/5">
                      {loadStatus.z_score}σ vs Baseline
                    </span>
                  )}
                  {loadStatus.method === 'heuristic' && (
                    <span className="text-sm bg-white/10 px-3 py-1 rounded-full border border-white/5 text-orange-400">
                      Baseline building...
                    </span>
                  )}
                </div>
              </div>
              
              <div className="flex gap-8">
                <div className="flex flex-col items-center">
                  <div className="flex items-center gap-2 text-slate-400 mb-1">
                    <Users className="w-4 h-4" />
                    <span className="text-xs uppercase font-semibold">Pending</span>
                  </div>
                  <span className="text-xl font-bold">{loadStatus?.pending_alerts ?? '0'}</span>
                </div>
                <div className="flex flex-col items-center">
                  <div className="flex items-center gap-2 text-slate-400 mb-1">
                    <TrendingUp className="w-4 h-4" />
                    <span className="text-xs uppercase font-semibold">Avg Wait</span>
                  </div>
                  <span className="text-xl font-bold">
                    {loadStatus?.avg_wait_seconds ? `${Math.round(loadStatus.avg_wait_seconds / 60)}m` : '--'}
                  </span>
                </div>
              </div>
            </div>
          )}

          <div className="space-y-4">
            {alerts.length === 0 ? (
              <div className="glass-panel p-12 text-center rounded-3xl border border-white/5 bg-slate-900/40 backdrop-blur-md">
                <p className="text-slate-400 text-lg">No pending alerts. You're all caught up.</p>
              </div>
            ) : (
              alerts.map(alert => (
                <div key={alert.id} className="glass-panel p-6 rounded-2xl flex items-center justify-between border border-white/5 hover:border-white/10 transition-colors bg-slate-900/40 backdrop-blur-md">
                  <div className="flex items-center gap-6">
                    {/* Urgency Badge */}
                    <div className={`w-16 h-16 rounded-xl flex flex-col items-center justify-center ${
                      alert.urgency_level === 1 ? 'bg-red-500/20 text-red-400 border border-red-500/30' : 'bg-orange-500/20 text-orange-400 border border-orange-500/30'
                    }`}>
                      <AlertTriangle className="w-6 h-6 mb-1" />
                      <span className="font-bold text-sm">LVL {alert.urgency_level}</span>
                    </div>

                    <div>
                      <h3 className="text-xl font-bold">{alert.predicted_condition}</h3>
                      <div className="flex items-center gap-4 text-sm text-slate-400 mt-2">
                        <span className="flex items-center gap-1"><MapPin className="w-4 h-4" /> {alert.patient_city} ({alert.patient_pincode})</span>
                        <span className="flex items-center gap-1"><Clock className="w-4 h-4" /> {new Date(alert.created_at).toLocaleTimeString()}</span>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-4">
                    <a href={`/hospital/session/${alert.session_id}`} target="_blank" rel="noreferrer" className="text-blue-400 hover:text-blue-300 text-sm font-semibold transition-colors">
                      View Session
                    </a>
                    <button 
                      onClick={() => handleAcknowledge(alert.id)}
                      className="flex items-center gap-2 bg-green-500/20 hover:bg-green-500/30 text-green-400 border border-green-500/30 px-6 py-3 rounded-xl font-semibold transition-colors"
                    >
                      <CheckCircle className="w-5 h-5" />
                      Acknowledge
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </AuroraBackground>
  );
}

export default HospitalDashboard;
