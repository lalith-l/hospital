import { useParams } from 'react-router-dom';
import { Activity, CheckCircle, FileText, User } from 'lucide-react';

function HospitalSession() {
  const { session_id } = useParams();

  return (
    <div className="min-h-screen bg-background p-8 flex items-center justify-center">
      <div className="glass-panel w-full max-w-2xl rounded-3xl p-8 border border-white/10 relative overflow-hidden">
        <div className="absolute top-0 left-0 w-full h-2 bg-green-500" />
        
        <div className="flex justify-center mb-8">
          <div className="w-16 h-16 rounded-2xl bg-green-500/20 flex items-center justify-center border border-green-500/30">
            <CheckCircle className="text-green-400 w-8 h-8" />
          </div>
        </div>
        
        <h1 className="text-3xl font-bold text-center mb-2">QR Code Scanned Successfully</h1>
        <p className="text-textMuted text-center mb-8">Patient arrival confirmed.</p>
        
        <div className="space-y-4">
          <div className="bg-surface border border-white/5 p-4 rounded-xl flex items-center gap-4">
            <Activity className="w-6 h-6 text-primary" />
            <div>
              <p className="text-sm text-textMuted">AEGIS Session ID</p>
              <p className="font-mono">{session_id}</p>
            </div>
          </div>
          
          <div className="bg-surface border border-white/5 p-4 rounded-xl flex items-center gap-4">
            <User className="w-6 h-6 text-accent" />
            <div>
              <p className="text-sm text-textMuted">Patient Record</p>
              <p className="font-semibold">Match Found in AEGIS Database</p>
            </div>
          </div>

          <div className="bg-surface border border-white/5 p-4 rounded-xl flex items-center gap-4">
            <FileText className="w-6 h-6 text-purple-400" />
            <div>
              <p className="text-sm text-textMuted">Triage Data</p>
              <p className="font-semibold">Loaded to Reception Dashboard</p>
            </div>
          </div>
        </div>
        
        <button 
          onClick={() => window.close()}
          className="w-full mt-8 bg-white/10 hover:bg-white/20 text-white font-semibold rounded-xl py-4 transition-colors"
        >
          Close Window
        </button>
      </div>
    </div>
  );
}

export default HospitalSession;
