import { useEffect } from 'react';
import { useMap } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet.heat';

interface HeatmapData {
  lat: number;
  lon: number;
  intensity: number;
}

interface HeatmapLayerProps {
  data: HeatmapData[];
}

export default function HeatmapLayer({ data }: HeatmapLayerProps) {
  const map = useMap();

  useEffect(() => {
    if (!data || data.length === 0) return;

    // Convert data to format required by leaflet.heat: [lat, lon, intensity]
    const heatData = data.map(point => [point.lat, point.lon, point.intensity]);

    // Create the heat layer
    // Adjust radius, blur, and gradient as needed
    // @ts-ignore - leaflet.heat adds L.heatLayer
    const heatLayer = L.heatLayer(heatData, {
      radius: 30,
      blur: 20,
      maxZoom: 14,
      gradient: { 0.2: 'green', 0.5: 'orange', 1.0: 'red' }
    });

    // Add to map
    heatLayer.addTo(map);

    // Cleanup when component unmounts or data changes
    return () => {
      map.removeLayer(heatLayer);
    };
  }, [map, data]);

  return null;
}
