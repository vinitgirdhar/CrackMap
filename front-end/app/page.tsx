"use client";

import { useEffect, useState } from "react";
import { TopNavBar } from "@/components/TopNavBar";
import { HeroSection } from "@/components/HeroSection";
import { StepperPipeline } from "@/components/StepperPipeline";
import { SubNavRow } from "@/components/SubNavRow";
import { DetectorView } from "@/components/DetectorView";
import { AnalyticsView } from "@/components/AnalyticsView";
import { CivicPipelineView } from "@/components/CivicPipelineView";
import { getSystemInfo } from "@/lib/api";
import { useDashboardSummary } from "@/lib/hooks/useDashboardSummary";
import type { SystemInfo, TabKey } from "@/lib/types";

export default function Home() {
  const [activeTab, setActiveTab] = useState<TabKey>("detect");
  const [systemInfo, setSystemInfo] = useState<SystemInfo | null>(null);
  const [civicMounted, setCivicMounted] = useState(false);
  const [prevTab, setPrevTab] = useState(activeTab);
  if (activeTab !== prevTab) {
    setPrevTab(activeTab);
    if (activeTab === "civic") setCivicMounted(true);
  }

  const { data: summary, refetch } = useDashboardSummary();

  const fetchSystemData = () => {
    getSystemInfo()
      .then(setSystemInfo)
      .catch(() => setSystemInfo(null));
  };

  useEffect(() => {
    fetchSystemData();
  }, []);

  const handleGlobalRefresh = () => {
    refetch();
    fetchSystemData();
    if (typeof window !== "undefined") {
      window.dispatchEvent(new CustomEvent("crackmap:refresh"));
    }
  };

  return (
    <div className="dashboard-wrapper">
      <TopNavBar activeTab={activeTab} onTabChange={setActiveTab} systemInfo={systemInfo} onRefresh={handleGlobalRefresh} />

      <HeroSection summary={summary} />

      <StepperPipeline />

      <SubNavRow activeTab={activeTab} onTabChange={setActiveTab} />

      <div className="workspace-container" style={{ display: activeTab === "detect" ? "block" : "none" }}>
        <DetectorView />
      </div>
      <div className="workspace-container" style={{ display: activeTab === "analytics" ? "block" : "none" }}>
        <AnalyticsView isActive={activeTab === "analytics"} />
      </div>
      {/* Mounted only after first activation: Leaflet corrupts its internal size if it
          ever initializes inside a display:none container, and invalidateSize() can't
          repair that later — so the map must never be born hidden. */}
      {civicMounted && (
        <div className="workspace-container" style={{ display: activeTab === "civic" ? "block" : "none" }}>
          <CivicPipelineView isActive={activeTab === "civic"} />
        </div>
      )}
    </div>
  );
}
