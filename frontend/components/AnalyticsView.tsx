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
        Road Damage Dataset & Analytics Explorer
      </h3>
      <p className="section-subtext">
        PASCAL VOC annotation distribution, damage frequencies, and format converters.
      </p>

      {!stats && <p>Loading live dataset statistics...</p>}

      {stats && (
        <>
          <div className="analytics-chips">
            <div className="analytics-chip">
              <strong>Total Images:</strong> {stats.total_images}
            </div>
            <div className="analytics-chip peach">
              <strong>Damaged Frames:</strong> {stats.damaged_images}
            </div>
            <div className="analytics-chip sky">
              <strong>Total Defects:</strong> {stats.total_boxes}
            </div>
          </div>

          <h4 className="analytics-heading">Damage Class Distribution (VOC Dataset)</h4>
          <div className="class-dist-grid">
            {Object.entries(stats.class_distribution || {}).map(([cls, count]) => (
              <div className="class-dist-card" key={cls}>
                <span className="class-dist-code">{cls}</span>
                <div className="class-dist-count">{count}</div>
                <span className="class-dist-label">Defect Instances</span>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
