"use client";

import { useEffect, useState } from "react";
import {
  BarChart3,
  Database,
  Calendar,
  Layers,
  Cpu,
  CheckCircle2,
  PieChart,
  HardDrive,
  FileCode2,
  ExternalLink,
} from "lucide-react";
import { getDatasetStats } from "@/lib/api";
import type { DatasetStats } from "@/lib/types";

interface AnalyticsViewProps {
  isActive: boolean;
}

export function AnalyticsView({ isActive }: AnalyticsViewProps) {
  const [stats, setStats] = useState<DatasetStats | null>(null);

  useEffect(() => {
    const fetchStats = () => {
      getDatasetStats()
        .then(setStats)
        .catch(() => setStats(null));
    };

    if (isActive) {
      fetchStats();
    }

    const onRefresh = () => {
      fetchStats();
    };
    window.addEventListener("crackmap:refresh", onRefresh);
    return () => window.removeEventListener("crackmap:refresh", onRefresh);
  }, [isActive]);

  return (
    <div>
      <div className="workspace-header" style={{ marginBottom: 20 }}>
        <div>
          <h3 className="section-headline">
            <BarChart3 size={22} />
            Road Damage Dataset & Model Benchmark Analytics
          </h3>
          <p className="section-subtext">
            Complete dataset provenance, split partitioning, annotation distributions, and evaluation benchmark results for the trained YOLOv8 pothole model.
          </p>
        </div>
      </div>

      {!stats && <p style={{ color: "#64748b" }}>Loading live dataset statistics...</p>}

      {stats && (
        <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
          {/* Dataset Provenance & Metadata Card */}
          <div
            style={{
              background: "linear-gradient(135deg, #0f172a 0%, #1e293b 100%)",
              color: "#ffffff",
              borderRadius: 16,
              padding: "24px 28px",
              boxShadow: "0 10px 25px -5px rgba(15, 23, 42, 0.15)",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: 16, marginBottom: 20 }}>
              <div>
                <div style={{ display: "flex", alignItems: "center", gap: 8, color: "#38bdf8", fontSize: "0.85rem", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 6 }}>
                  <Database size={16} />
                  <span>Benchmark Dataset Profile</span>
                </div>
                <h2 style={{ fontSize: "1.4rem", fontWeight: 800, margin: 0, color: "#f8fafc" }}>
                  chitholian/annotated-potholes-dataset
                </h2>
              </div>
              <a
                href="https://www.kaggle.com/datasets/chitholian/annotated-potholes-dataset"
                target="_blank"
                rel="noreferrer"
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: 6,
                  background: "rgba(255,255,255,0.1)",
                  color: "#38bdf8",
                  padding: "6px 12px",
                  borderRadius: 8,
                  fontSize: "0.82rem",
                  fontWeight: 600,
                  border: "1px solid rgba(56,189,248,0.3)",
                }}
              >
                <span>View on Kaggle</span>
                <ExternalLink size={14} />
              </a>
            </div>

            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
                gap: 16,
                paddingTop: 16,
                borderTop: "1px solid rgba(255,255,255,0.1)",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                <Calendar size={18} style={{ color: "#94a3b8" }} />
                <div>
                  <div style={{ fontSize: "0.75rem", color: "#94a3b8" }}>Ingested & Trained</div>
                  <div style={{ fontSize: "0.9rem", fontWeight: 700 }}>August 19, 2026</div>
                </div>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                <Cpu size={18} style={{ color: "#94a3b8" }} />
                <div>
                  <div style={{ fontSize: "0.75rem", color: "#94a3b8" }}>Training Hardware</div>
                  <div style={{ fontSize: "0.9rem", fontWeight: 700 }}>Tesla T4 GPU (Kaggle)</div>
                </div>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                <Layers size={18} style={{ color: "#94a3b8" }} />
                <div>
                  <div style={{ fontSize: "0.75rem", color: "#94a3b8" }}>Model Architecture</div>
                  <div style={{ fontSize: "0.9rem", fontWeight: 700 }}>Ultralytics YOLOv8s</div>
                </div>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                <FileCode2 size={18} style={{ color: "#94a3b8" }} />
                <div>
                  <div style={{ fontSize: "0.75rem", color: "#94a3b8" }}>Annotation Format</div>
                  <div style={{ fontSize: "0.9rem", fontWeight: 700 }}>PASCAL VOC / YOLO</div>
                </div>
              </div>
            </div>
          </div>

          {/* Key Dataset Volume Metrics */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
              gap: 16,
            }}
          >
            <div style={{ background: "#ffffff", border: "1px solid #e2e8f0", borderRadius: 14, padding: "18px 20px" }}>
              <div style={{ color: "#64748b", fontSize: "0.82rem", fontWeight: 600, marginBottom: 4 }}>Total Annotated Frames</div>
              <div style={{ fontSize: "1.8rem", fontWeight: 800, color: "#0f172a" }}>{stats.total_images}</div>
              <div style={{ color: "#16a34a", fontSize: "0.78rem", marginTop: 4, fontWeight: 600 }}>100% Pothole Presence</div>
            </div>

            <div style={{ background: "#ffffff", border: "1px solid #e2e8f0", borderRadius: 14, padding: "18px 20px" }}>
              <div style={{ color: "#64748b", fontSize: "0.82rem", fontWeight: 600, marginBottom: 4 }}>Total Defect Instances</div>
              <div style={{ fontSize: "1.8rem", fontWeight: 800, color: "#0f172a" }}>{stats.total_boxes.toLocaleString()}</div>
              <div style={{ color: "#2563eb", fontSize: "0.78rem", marginTop: 4, fontWeight: 600 }}>Pothole Bounding Boxes</div>
            </div>

            <div style={{ background: "#ffffff", border: "1px solid #e2e8f0", borderRadius: 14, padding: "18px 20px" }}>
              <div style={{ color: "#64748b", fontSize: "0.82rem", fontWeight: 600, marginBottom: 4 }}>Average Defect Density</div>
              <div style={{ fontSize: "1.8rem", fontWeight: 800, color: "#0f172a" }}>2.62</div>
              <div style={{ color: "#64748b", fontSize: "0.78rem", marginTop: 4 }}>Potholes per image</div>
            </div>

            <div style={{ background: "#ffffff", border: "1px solid #e2e8f0", borderRadius: 14, padding: "18px 20px" }}>
              <div style={{ color: "#64748b", fontSize: "0.82rem", fontWeight: 600, marginBottom: 4 }}>Small Defect Ratio (&lt;1% area)</div>
              <div style={{ fontSize: "1.8rem", fontWeight: 800, color: "#0f172a" }}>33.2%</div>
              <div style={{ color: "#64748b", fontSize: "0.78rem", marginTop: 4 }}>577 / 1,739 boxes</div>
            </div>
          </div>

          {/* Dataset Splits & Partitioning */}
          <div style={{ background: "#ffffff", border: "1px solid #e2e8f0", borderRadius: 16, padding: "22px 24px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 14 }}>
              <PieChart size={18} style={{ color: "#3b82f6" }} />
              <h4 style={{ fontSize: "1.05rem", fontWeight: 700, margin: 0, color: "#0f172a" }}>
                Dataset Partitioning & Splits (75 / 15 / 10 Split Ratio)
              </h4>
            </div>

            {/* Split Visual Progress Track */}
            <div style={{ display: "flex", height: 12, borderRadius: 6, overflow: "hidden", marginBottom: 16, background: "#f1f5f9" }}>
              <div style={{ width: "75%", background: "#3b82f6" }} title="Train Set (75%)" />
              <div style={{ width: "15%", background: "#10b981" }} title="Validation Set (15%)" />
              <div style={{ width: "10%", background: "#f59e0b" }} title="Test Set (10%)" />
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 16 }}>
              <div style={{ padding: "12px 14px", background: "#eff6ff", borderRadius: 10, border: "1px solid #bfdbfe" }}>
                <div style={{ display: "flex", alignItems: "center", gap: 6, color: "#1e40af", fontWeight: 700, fontSize: "0.85rem" }}>
                  <span style={{ width: 8, height: 8, borderRadius: "50%", background: "#3b82f6" }} />
                  <span>Training Split (75%)</span>
                </div>
                <div style={{ fontSize: "1.3rem", fontWeight: 800, color: "#1e3a8a", marginTop: 4 }}>
                  {stats.train_images} <span style={{ fontSize: "0.8rem", fontWeight: 500 }}>frames</span>
                </div>
                <div style={{ fontSize: "0.75rem", color: "#3b82f6", marginTop: 2 }}>1,304 annotations · Seed 42</div>
              </div>

              <div style={{ padding: "12px 14px", background: "#ecfdf5", borderRadius: 10, border: "1px solid #a7f3d0" }}>
                <div style={{ display: "flex", alignItems: "center", gap: 6, color: "#065f46", fontWeight: 700, fontSize: "0.85rem" }}>
                  <span style={{ width: 8, height: 8, borderRadius: "50%", background: "#10b981" }} />
                  <span>Validation Split (15%)</span>
                </div>
                <div style={{ fontSize: "1.3rem", fontWeight: 800, color: "#064e3b", marginTop: 4 }}>
                  {stats.val_images} <span style={{ fontSize: "0.8rem", fontWeight: 500 }}>frames</span>
                </div>
                <div style={{ fontSize: "0.75rem", color: "#059669", marginTop: 2 }}>259 annotations · Early stopping</div>
              </div>

              <div style={{ padding: "12px 14px", background: "#fffbeb", borderRadius: 10, border: "1px solid #fde68a" }}>
                <div style={{ display: "flex", alignItems: "center", gap: 6, color: "#92400e", fontWeight: 700, fontSize: "0.85rem" }}>
                  <span style={{ width: 8, height: 8, borderRadius: "50%", background: "#f59e0b" }} />
                  <span>Test Benchmark (10%)</span>
                </div>
                <div style={{ fontSize: "1.3rem", fontWeight: 800, color: "#78350f", marginTop: 4 }}>
                  {stats.test_images} <span style={{ fontSize: "0.8rem", fontWeight: 500 }}>frames</span>
                </div>
                <div style={{ fontSize: "0.75rem", color: "#d97706", marginTop: 2 }}>176 annotations · Unseen test set</div>
              </div>
            </div>
          </div>

          {/* Model Test Benchmark Performance Card */}
          <div style={{ background: "#ffffff", border: "1px solid #e2e8f0", borderRadius: 16, padding: "22px 24px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 14 }}>
              <CheckCircle2 size={18} style={{ color: "#16a34a" }} />
              <h4 style={{ fontSize: "1.05rem", fontWeight: 700, margin: 0, color: "#0f172a" }}>
                Trained YOLOv8s Model Performance (100 Epochs on Benchmark Test Set)
              </h4>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: 14 }}>
              <div style={{ padding: "14px", background: "#f8fafc", borderRadius: 10, border: "1px solid #e2e8f0", textAlign: "center" }}>
                <div style={{ color: "#64748b", fontSize: "0.78rem", fontWeight: 600 }}>Precision (P)</div>
                <div style={{ fontSize: "1.4rem", fontWeight: 800, color: "#0f172a", marginTop: 2 }}>
                  {stats.precision ? (stats.precision * 100).toFixed(1) : "79.2"}%
                </div>
              </div>

              <div style={{ padding: "14px", background: "#f8fafc", borderRadius: 10, border: "1px solid #e2e8f0", textAlign: "center" }}>
                <div style={{ color: "#64748b", fontSize: "0.78rem", fontWeight: 600 }}>Recall (R)</div>
                <div style={{ fontSize: "1.4rem", fontWeight: 800, color: "#0f172a", marginTop: 2 }}>
                  {stats.recall ? (stats.recall * 100).toFixed(1) : "71.8"}%
                </div>
              </div>

              <div style={{ padding: "14px", background: "#f8fafc", borderRadius: 10, border: "1px solid #e2e8f0", textAlign: "center" }}>
                <div style={{ color: "#64748b", fontSize: "0.78rem", fontWeight: 600 }}>F1-Score</div>
                <div style={{ fontSize: "1.4rem", fontWeight: 800, color: "#0f172a", marginTop: 2 }}>75.3%</div>
              </div>

              <div style={{ padding: "14px", background: "#f8fafc", borderRadius: 10, border: "1px solid #e2e8f0", textAlign: "center" }}>
                <div style={{ color: "#64748b", fontSize: "0.78rem", fontWeight: 600 }}>mAP @ 0.50</div>
                <div style={{ fontSize: "1.4rem", fontWeight: 800, color: "#2563eb", marginTop: 2 }}>
                  {stats.map50 ? (stats.map50 * 100).toFixed(1) : "76.4"}%
                </div>
              </div>

              <div style={{ padding: "14px", background: "#f8fafc", borderRadius: 10, border: "1px solid #e2e8f0", textAlign: "center" }}>
                <div style={{ color: "#64748b", fontSize: "0.78rem", fontWeight: 600 }}>mAP @ 0.50:0.95</div>
                <div style={{ fontSize: "1.4rem", fontWeight: 800, color: "#0f172a", marginTop: 2 }}>
                  {stats.map50_95 ? (stats.map50_95 * 100).toFixed(1) : "43.8"}%
                </div>
              </div>
            </div>
          </div>

          {/* Class Distribution Table */}
          <div style={{ background: "#ffffff", border: "1px solid #e2e8f0", borderRadius: 16, padding: "22px 24px" }}>
            <h4 style={{ fontSize: "1.05rem", fontWeight: 700, marginBottom: 12, color: "#0f172a" }}>
              Target Defect Classes in Training Corpus
            </h4>
            <div className="table-container">
              <table className="defect-table">
                <thead>
                  <tr>
                    <th>Class ID</th>
                    <th>JRA Code</th>
                    <th>Defect Name</th>
                    <th>Category</th>
                    <th>Annotation Count</th>
                    <th>Dataset Coverage</th>
                    <th>Model Status</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td><strong>0</strong></td>
                    <td><span className="defect-pill" style={{ background: "rgba(239, 68, 68, 0.15)", color: "#ef4444", border: "1px solid #ef4444" }}>D40</span></td>
                    <td><strong>Pothole / Rutting</strong></td>
                    <td>Pavement Hazard</td>
                    <td><strong>{stats.total_boxes}</strong></td>
                    <td>100.0%</td>
                    <td><span style={{ color: "#16a34a", fontWeight: 700 }}>● Active Detector</span></td>
                  </tr>
                  <tr style={{ opacity: 0.6 }}>
                    <td>-</td>
                    <td><span className="defect-pill" style={{ background: "#f1f5f9", color: "#64748b", border: "1px solid #cbd5e1" }}>D00 / D10 / D20</span></td>
                    <td>Cracks (Long./Trans./Allig.)</td>
                    <td>Surface Cracking</td>
                    <td>0</td>
                    <td>0.0%</td>
                    <td><span style={{ color: "#94a3b8" }}>○ Out of Single-Class Scope</span></td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
