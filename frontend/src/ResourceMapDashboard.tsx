// React import removed for React 17+ JSX transform
import HeatmapLayer from './HeatmapLayer';

export const RESOURCE_COORDINATES: Record<string, { x: number, y: number }> = {
  "Waiting_Room": { x: 400, y: 50 },
  "Triage_Desk": { x: 400, y: 150 },
  "Cath_Lab": { x: 200, y: 300 },
  "Ultrasound_Bay": { x: 600, y: 300 },
  "X_Ray": { x: 200, y: 500 },
  "Respiratory_Isolation": { x: 600, y: 500 }
};

export default function ResourceMapDashboard() {
  return (
    <div className="min-h-screen bg-slate-900 flex flex-col items-center justify-center p-8">
      <div className="flex flex-col items-center gap-6 w-full max-w-4xl">
        <h1 className="text-3xl font-bold text-white tracking-tight">Predictive Resource Bottleneck Map</h1>
        <p className="text-slate-400 max-w-2xl text-center">
          Real-time spatial visualization of active triage resource demand. Glowing zones indicate 
          imminent clinical bottlenecks based on live NLP diagnostics.
        </p>
        
        {/* Parent container must be relative and fixed size to align heatmap exactly */}
        <div className="relative w-[800px] h-[600px] bg-slate-800 border-2 border-slate-700 rounded-lg shadow-2xl overflow-hidden mt-4 shrink-0">
          
          {/* Base Map Layers */}
          <div className="absolute top-0 left-0 w-full h-[100px] border-b-2 border-slate-700 flex items-center justify-center">
            <span className="text-slate-400 font-mono tracking-widest text-lg">WAITING ROOM (ENTRANCE)</span>
          </div>
          
          <div className="absolute top-[100px] left-[300px] w-[200px] h-[100px] border-b-2 border-x-2 border-slate-700 flex items-center justify-center bg-slate-800 z-10">
            <span className="text-slate-400 font-mono tracking-widest text-center text-sm">TRIAGE<br/>DESK</span>
          </div>

          <div className="absolute top-[200px] left-0 w-[400px] h-[200px] border-b-2 border-r-2 border-slate-700 flex items-center justify-center">
            <span className="text-slate-400 font-mono tracking-widest">CATH LAB</span>
          </div>

          <div className="absolute top-[200px] left-[400px] w-[400px] h-[200px] border-b-2 border-slate-700 flex items-center justify-center">
            <span className="text-slate-400 font-mono tracking-widest">ULTRASOUND BAY</span>
          </div>

          <div className="absolute top-[400px] left-0 w-[400px] h-[200px] border-r-2 border-slate-700 flex items-center justify-center">
            <span className="text-slate-400 font-mono tracking-widest">X-RAY</span>
          </div>

          <div className="absolute top-[400px] left-[400px] w-[400px] h-[200px] flex items-center justify-center">
            <span className="text-slate-400 font-mono tracking-widest text-center">RESPIRATORY<br/>ISOLATION</span>
          </div>

          {/* Absolute positioned Heatmap Overlay */}
          <HeatmapLayer width={800} height={600} />
          
        </div>
      </div>
    </div>
  );
}
