"use client";

import { Bell, Route, RefreshCw, Search } from "lucide-react";
import type { SystemInfo, TabKey } from "@/lib/types";

const TABS: { key: TabKey; label: string }[] = [
  { key: "detect", label: "AI Inspector" },
  { key: "gis", label: "GIS CrackMap" },
  { key: "analytics", label: "Analytics" },
  { key: "train", label: "Train Model" },
];

interface TopNavBarProps {
  activeTab: TabKey;
  onTabChange: (tab: TabKey) => void;
  systemInfo: SystemInfo | null;
  onRefresh: () => void;
}

export function TopNavBar({ activeTab, onTabChange, systemInfo, onRefresh }: TopNavBarProps) {
  return (
    <div className="top-nav-bar">
      <div className="brand-group">
        <button className="brand-logo" onClick={() => onTabChange("detect")} type="button">
          <Route size={26} strokeWidth={2.5} />
          Crack<span>Map</span>
        </button>
        {systemInfo && (
          <div className="brand-badges">
            <span className="brand-badge status-online">
              <span className="status-dot" />
              {systemInfo.status === "online" ? "API Online" : systemInfo.status}
            </span>
            <span className="brand-badge">PyTorch {systemInfo.torch_version}</span>
            <span className="brand-badge">
              {systemInfo.device === "cuda" ? "GPU Accelerated" : "CPU Inference"}
            </span>
          </div>
        )}
      </div>

      <div className="nav-pills">
        {TABS.map((tab) => (
          <button
            key={tab.key}
            id={`pill-${tab.key}`}
            className={`nav-pill-btn${activeTab === tab.key ? " active" : ""}`}
            onClick={() => onTabChange(tab.key)}
            type="button"
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div className="nav-actions">
        <button className="action-circle-btn" title="Refresh live data" onClick={onRefresh} type="button">
          <RefreshCw size={16} />
        </button>
        <button className="action-circle-btn" title="Search" type="button">
          <Search size={16} />
        </button>
        <button className="action-circle-btn" title="Alerts" type="button">
          <Bell size={16} />
        </button>
        <div className="user-avatar-badge" title="AI Inspection Officer">
          AI
        </div>
      </div>
    </div>
  );
}
