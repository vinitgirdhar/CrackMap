"use client";

import { useEffect, useState } from "react";
import { BarChart3 } from "lucide-react";
import { getDatasetStats } from "@/lib/api";
import type { DatasetStats } from "@/lib/types";

interface AnalyticsViewProps {
  isActive: boolean;
}

export function AnalyticsView({ isActive }: AnalyticsViewProps) {
  const [stats, setStats] = useState<DatasetStats | null>(null);

  useEffect(() => {
    if (!isActive) return;
    getDatasetStats()
      .then(setStats)
      .catch(() => setStats(null));
  }, [isActive]);

  return (
    <div>
      <h3 className="section-headline">
        <BarChart3 size={20} />
        Road Damage Dataset & Model Benchmark Analytics
      </h3>
      <p className="section-subtext">
        Ground-truth training annotations and benchmark metrics for the single-class YOLOv8 pothole model from Kaggle: <code>chitholian/annotated-potholes-dataset</code>.
      </p>

      {!stats && <p>Loading live dataset statistics...</p>}

      {stats && (
        <>
          <div className="analytics-chips">
            <div className="analytics-chip">
              <strong>Annotated Frames:</strong> {stats.total_images}
            </div>
            <div className="analytics-chip peach">
              <strong>Damaged Frames:</strong> {stats.damaged_images}
            </div>
            <div className="analytics-chip sky">
              <strong>Total Pothole Instances:</strong> {stats.total_boxes}
            </div>
          </div>

          <h4 className="analytics-heading">Model Class Distribution (Training Corpus)</h4>
          <div className="class-dist-grid">
            {Object.entries(stats.class_distribution || {}).map(([cls, count]) => (
              <div className="class-dist-card" key={cls}>
                <span className="class-dist-code">{cls.toUpperCase()}</span>
                <div className="class-dist-count">{count}</div>
                <span className="class-dist-label">Annotated Instances</span>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
