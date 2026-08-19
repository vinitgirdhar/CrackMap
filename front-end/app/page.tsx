"use client";

import { useEffect, useState } from "react";
import { TopNavBar } from "@/components/TopNavBar";
import { HeroSection } from "@/components/HeroSection";
import { StepperPipeline } from "@/components/StepperPipeline";
import { SubNavRow } from "@/components/SubNavRow";
import { DetectorView } from "@/components/DetectorView";
import { AnalyticsView } from "@/components/AnalyticsView";
import { getSystemInfo } from "@/lib/api";
import { useDashboardSummary } from "@/lib/hooks/useDashboardSummary";
import type { SystemInfo, TabKey } from "@/lib/types";

export default function Home() {
  const [activeTab, setActiveTab] = useState<TabKey>("detect");
  const [systemInfo, setSystemInfo] = useState<SystemInfo | null>(null);

  const { data: summary, refetch } = useDashboardSummary();

  useEffect(() => {
    getSystemInfo()
      .then(setSystemInfo)
      .catch(() => setSystemInfo(null));
  }, []);

  return (
    <div className="dashboard-wrapper">
      <TopNavBar activeTab={activeTab} onTabChange={setActiveTab} systemInfo={systemInfo} onRefresh={refetch} />

      <HeroSection summary={summary} />

      <StepperPipeline hasSurveyData={(summary?.total_images ?? 0) > 0} />

      <SubNavRow activeTab={activeTab} onTabChange={setActiveTab} />

      <div className="workspace-container" style={{ display: activeTab === "detect" ? "block" : "none" }}>
        <DetectorView />
      </div>
      <div className="workspace-container" style={{ display: activeTab === "analytics" ? "block" : "none" }}>
        <AnalyticsView isActive={activeTab === "analytics"} />
      </div>
    </div>
  );
}
