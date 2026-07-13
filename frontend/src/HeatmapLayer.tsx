import { useEffect, useRef, useState } from 'react';
import { RESOURCE_COORDINATES } from './ResourceMapDashboard';

interface HeatmapLayerProps {
  width: number;
  height: number;
}

interface HeatmapDataPoint {
  resource: string;
  intensity: number;
}

export default function HeatmapLayer({ width, height }: HeatmapLayerProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const dataRef = useRef<HeatmapDataPoint[]>([]);
  const animationRef = useRef<number>(0);
  const wsRef = useRef<WebSocket | null>(null);
  
  const [connectionState, setConnectionState] = useState<'connecting' | 'connected' | 'reconnecting'>('connecting');
  const reconnectAttempt = useRef(0);

  // WebSocket Connection Logic with Exponential Backoff
  useEffect(() => {
    let isMounted = true;
    let reconnectTimeout: ReturnType<typeof setTimeout>;

    const connect = () => {
      if (!isMounted) return;
      const token = localStorage.getItem('hospital_token');
      if (!token) return;

      const wsUrl = (import.meta.env.VITE_API_URL || 'https://hospital-tp5s.onrender.com').replace(/^http/, 'ws');
      const ws = new WebSocket(`${wsUrl}/ws/resource-map?token=${token}`);
      wsRef.current = ws;

      ws.onopen = () => {
        if (!isMounted) return;
        setConnectionState('connected');
        reconnectAttempt.current = 0;
      };

      ws.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data);
          if (payload.type === 'HEATMAP_UPDATE') {
            dataRef.current = payload.data;
          }
        } catch (e) {
          console.error("Failed to parse WS payload", e);
        }
      };

      ws.onclose = () => {
        if (!isMounted) return;
        setConnectionState('reconnecting');
        
        // Exponential backoff
        const timeout = Math.min(1000 * Math.pow(2, reconnectAttempt.current), 30000);
        reconnectAttempt.current += 1;
        
        reconnectTimeout = setTimeout(connect, timeout);
      };
      
      ws.onerror = () => {
        ws.close();
      };
    };

    connect();

    return () => {
      isMounted = false;
      clearTimeout(reconnectTimeout);
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  // High-DPI Canvas Rendering Loop
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // High-DPI Scaling
    const dpr = window.devicePixelRatio || 1;
    canvas.width = width * dpr;
    canvas.height = height * dpr;
    canvas.style.width = `${width}px`;
    canvas.style.height = `${height}px`;
    ctx.scale(dpr, dpr);

    const render = () => {
      ctx.clearRect(0, 0, width, height);

      // If reconnecting, fade out slightly (graceful degradation handled by CSS opacity, 
      // but we can also just keep rendering the last known data)

      const points = dataRef.current;
      
      points.forEach(point => {
        const coords = RESOURCE_COORDINATES[point.resource];
        if (!coords) return;
        
        // Visual Thresholds
        const intensity = point.intensity;
        if (intensity < 0.4) return; // Transparent

        const radius = 100;
        const gradient = ctx.createRadialGradient(coords.x, coords.y, 0, coords.x, coords.y, radius);
        
        // Pulse effect for high intensity
        let alpha = intensity;
        if (intensity > 0.7) {
          const pulse = (Math.sin(Date.now() / 200) + 1) / 2; // 0.0 to 1.0
          alpha = 0.7 + (pulse * 0.3); // 0.7 to 1.0
          gradient.addColorStop(0, `rgba(220, 38, 38, ${alpha})`); // Red
          gradient.addColorStop(1, 'rgba(220, 38, 38, 0)');
        } else {
          gradient.addColorStop(0, `rgba(245, 158, 11, ${alpha * 0.8})`); // Amber
          gradient.addColorStop(1, 'rgba(245, 158, 11, 0)');
        }

        ctx.fillStyle = gradient;
        ctx.beginPath();
        ctx.arc(coords.x, coords.y, radius, 0, Math.PI * 2);
        ctx.fill();
      });

      animationRef.current = requestAnimationFrame(render);
    };

    render();

    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    };
  }, [width, height]);

  return (
    <>
      {/* Graceful Degradation Overlay */}
      {connectionState === 'reconnecting' && (
        <div className="absolute inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-sm transition-opacity duration-1000">
          <div className="text-amber-400 font-mono tracking-widest text-sm flex items-center gap-2 bg-slate-800 px-4 py-2 rounded-full border border-amber-500/30">
            <span className="w-2 h-2 rounded-full bg-amber-500 animate-ping"></span>
            RECONNECTING TO TELEMETRY...
          </div>
        </div>
      )}
      
      <canvas
        ref={canvasRef}
        className={`absolute top-0 left-0 pointer-events-none z-20 transition-opacity duration-1000 ${connectionState === 'reconnecting' ? 'opacity-30' : 'opacity-100'}`}
      />
    </>
  );
}
