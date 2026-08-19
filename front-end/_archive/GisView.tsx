"use client";

import dynamic from "next/dynamic";
import { MapPin } from "lucide-react";
import type { GisDataPoint } from "@/lib/types";

const GisMap = dynamic(() => import("./GisMap"), { ssr: false });

interface GisViewProps {
  isActive: boolean;
  onDataLoaded?: (points: GisDataPoint[]) => void;
}

export function GisView({ isActive, onDataLoaded }: GisViewProps) {
  return (
    <div>
      <h3 className="section-headline">
        <MapPin size={20} />
        Municipal CrackMap & Geotagged Damage Heatmap
      </h3>
      <p className="section-subtext">Crowdsensed pavement anomalies mapped across municipal highway networks.</p>
      <div className="gis-map-container">
        <GisMap isActive={isActive} onDataLoaded={onDataLoaded} />
      </div>
    </div>
  );
}
