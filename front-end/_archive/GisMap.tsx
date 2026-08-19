"use client";

import { useEffect, useState } from "react";
import { MapContainer, TileLayer, CircleMarker, Popup, useMap } from "react-leaflet";
import { getGisData } from "@/lib/api";
import type { GisDataPoint } from "@/lib/types";

const TOKYO_CENTER: [number, number] = [35.6762, 139.6503];

function InvalidateOnActivate({ isActive }: { isActive: boolean }) {
  const map = useMap();
  useEffect(() => {
    if (isActive) {
      map.invalidateSize();
    }
  }, [isActive, map]);
  return null;
}

interface GisMapProps {
  isActive: boolean;
  onDataLoaded?: (points: GisDataPoint[]) => void;
}

export default function GisMap({ isActive, onDataLoaded }: GisMapProps) {
  const [points, setPoints] = useState<GisDataPoint[]>([]);

  useEffect(() => {
    getGisData()
      .then((data) => {
        setPoints(data);
        onDataLoaded?.(data);
      })
      .catch(() => setPoints([]));
    // onDataLoaded intentionally excluded: fetch once on mount, like the original.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <MapContainer center={TOKYO_CENTER} zoom={12} style={{ height: "100%", width: "100%" }}>
      <InvalidateOnActivate isActive={isActive} />
      <TileLayer
        attribution="&copy; OpenStreetMap contributors &amp; CartoDB"
        url="https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png"
        maxZoom={19}
      />
      {points.map((pt) => (
        <CircleMarker
          key={pt.id}
          center={[pt.lat, pt.lon]}
          radius={pt.severity_score * 4 + 4}
          pathOptions={{
            fillColor: pt.color_hex || "#ef4444",
            color: "#ffffff",
            weight: 1.5,
            opacity: 1,
            fillOpacity: 0.85,
          }}
        >
          <Popup>
            <div style={{ fontFamily: "'Plus Jakarta Sans', sans-serif", padding: 4 }}>
              <b style={{ color: "#0f172a", fontSize: "1.1em" }}>
                {pt.damage_code}: {pt.damage_type}
              </b>
              <br />
              <b>Severity:</b> <span style={{ color: "#ef4444" }}>{pt.severity}</span> (Score:{" "}
              {pt.severity_score}/5)
              <br />
              <b>Confidence:</b> {(pt.confidence * 100).toFixed(0)}%
              <br />
              <b>Municipality:</b> {pt.municipality}
            </div>
          </Popup>
        </CircleMarker>
      ))}
    </MapContainer>
  );
}
