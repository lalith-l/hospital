import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet';
import { useState, useEffect } from 'react';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';
import LeafletHeatmapLayer from './LeafletHeatmapLayer';
import { Layers } from 'lucide-react';

// Fix leaflet default icon issue
delete (L.Icon.Default.prototype as any)._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
});

// Custom icons
const userIcon = new L.Icon({
  iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-blue.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41]
});

const hospitalIcon = new L.Icon({
  iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-red.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41]
});

interface HospitalMapProps {
  userLat: number;
  userLon: number;
  hospitalLat: number;
  hospitalLon: number;
  hospitalName: string;
}

export default function HospitalMap({ userLat, userLon, hospitalLat, hospitalLon, hospitalName }: HospitalMapProps) {
  const [showHeatmap, setShowHeatmap] = useState(false);
  const [heatmapData, setHeatmapData] = useState([]);

  useEffect(() => {
    const fetchHeatmapData = async () => {
      try {
        const apiUrl = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';
        const res = await fetch(`${apiUrl}/api/ambient-pressure/map`);
        const data = await res.json();
        setHeatmapData(data);
      } catch (e) {
        console.error("Failed to fetch heatmap data", e);
      }
    };
    fetchHeatmapData();
  }, []);

  // Calculate center between user and hospital
  const centerLat = (userLat + hospitalLat) / 2;
  const centerLon = (userLon + hospitalLon) / 2;

  const googleMapsUrl = `https://www.google.com/maps/dir/?api=1&origin=${userLat},${userLon}&destination=${hospitalLat},${hospitalLon}`;

  return (
    <div className="relative">
      {/* Toggle Button */}
      <button 
        onClick={() => setShowHeatmap(!showHeatmap)}
        className={`absolute z-10 top-4 right-4 px-4 py-2 rounded-xl text-sm font-semibold flex items-center gap-2 shadow-lg transition-colors border ${
          showHeatmap 
            ? 'bg-red-500/90 text-white border-red-400' 
            : 'bg-white/90 text-gray-800 border-gray-200 hover:bg-white'
        }`}
      >
        <Layers className="w-4 h-4" />
        {showHeatmap ? 'Hide Disease Pressure' : 'Show Disease Pressure'}
      </button>

      <div className="w-full h-64 rounded-xl overflow-hidden shadow-lg border border-white/10 relative z-0 mt-4">
      <MapContainer 
        center={[centerLat, centerLon]} 
        zoom={12} 
        scrollWheelZoom={false}
        style={{ height: '100%', width: '100%', zIndex: 0 }}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png"
        />
        <Marker position={[userLat, userLon]} icon={userIcon}>
          <Popup>You are here</Popup>
        </Marker>
        <Marker position={[hospitalLat, hospitalLon]} icon={hospitalIcon}>
          <Popup>
            <div className="text-center">
              <strong className="block mb-1">{hospitalName}</strong>
              <a 
                href={googleMapsUrl} 
                target="_blank" 
                rel="noopener noreferrer"
                className="bg-primary text-white px-3 py-1 rounded-full text-xs hover:bg-blue-600 transition-colors inline-block mt-2"
              >
                Get Directions
              </a>
            </div>
          </Popup>
        </Marker>
        {showHeatmap && heatmapData.length > 0 && (
          <LeafletHeatmapLayer data={heatmapData as any} />
        )}
      </MapContainer>
      </div>
    </div>
  );
}
