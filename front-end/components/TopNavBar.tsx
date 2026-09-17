"use client";

import { useState } from "react";
import Link from "next/link";
import { Route, RefreshCw, Check, Megaphone, SlidersHorizontal, Settings2 } from "lucide-react";
import type { SystemInfo, TabKey } from "@/lib/types";
import { FilterControlsPopover } from "./FilterControlsPopover";
import { SettingsModal } from "./SettingsModal";

const TABS: { key: TabKey; label: string }[] = [
  { key: "detect", label: "AI Inspector" },
  { key: "analytics", label: "Dataset Analytics" },
  { key: "civic", label: "Civic Pipeline" },
];

interface TopNavBarProps {
  activeTab: TabKey;
  onTabChange: (tab: TabKey) => void;
  systemInfo: SystemInfo | null;
  onRefresh: () => void;
}

export function TopNavBar({ activeTab, onTabChange, systemInfo, onRefresh }: TopNavBarProps) {
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [justRefreshed, setJustRefreshed] = useState(false);
  const [isFilterOpen, setIsFilterOpen] = useState(false);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);

  const handleRefresh = async () => {
    if (isRefreshing) return;
    setIsRefreshing(true);
    try {
      onRefresh();
      if (typeof window !== "undefined") {
        window.dispatchEvent(new CustomEvent("crackmap:refresh"));
      }
      setJustRefreshed(true);
      setTimeout(() => setJustRefreshed(false), 2000);
    } finally {
      setTimeout(() => setIsRefreshing(false), 600);
    }
  };

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
            <span className="brand-badge" title={systemInfo.models_loaded.join(", ")}>
              {systemInfo.fine_tuned ? "Fine-Tuned Model" : "Pretrained Model"}
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
        <Link className="report-pothole-link" href="/report" title="Public reporting page for citizens">
          <Megaphone size={14} />
          Report a Pothole
        </Link>
        <button
          className={`action-circle-btn${isFilterOpen ? " is-active" : ""}`}
          title="Inspection & filter controls"
          onClick={() => setIsFilterOpen(!isFilterOpen)}
          type="button"
          aria-label="Inspection and filter controls"
        >
          <SlidersHorizontal size={16} />
        </button>
        <button
          className={`action-circle-btn${isSettingsOpen ? " is-active" : ""}`}
          title="System preferences & settings"
          onClick={() => setIsSettingsOpen(true)}
          type="button"
          aria-label="System settings"
        >
          <Settings2 size={16} />
        </button>
        <button
          className={`action-circle-btn refresh-btn${isRefreshing ? " is-refreshing" : ""}${justRefreshed ? " just-refreshed" : ""}`}
          title={justRefreshed ? "Telemetry & metrics refreshed!" : "Refresh all live data"}
          onClick={handleRefresh}
          disabled={isRefreshing}
          type="button"
          aria-label="Refresh live data"
        >
          {justRefreshed ? (
            <Check size={16} className="text-green-500" style={{ color: "#16a34a" }} />
          ) : (
            <RefreshCw size={16} className={isRefreshing ? "spin-animation" : ""} />
          )}
        </button>
      </div>

      <FilterControlsPopover isOpen={isFilterOpen} onClose={() => setIsFilterOpen(false)} />
      <SettingsModal isOpen={isSettingsOpen} onClose={() => setIsSettingsOpen(false)} />
    </div>
  );
}
