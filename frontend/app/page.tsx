"use client";

import { useEffect, useState } from "react";
import { TopNavBar } from "@/components/TopNavBar";
import { HeroSection } from "@/components/HeroSection";
import { StepperPipeline } from "@/components/StepperPipeline";

import { SubNavRow } from "@/components/SubNavRow";
import { DetectorView } from "@/components/DetectorView";
import { GisView } from "@/components/GisView";
import { AnalyticsView } from "@/components/AnalyticsView";
import { TrainView } from "@/components/TrainView";
import { getSystemInfo } from "@/lib/api";
import { useDashboardSummary } from "@/lib/hooks/useDashboardSummary";
import type { GisDataPoint, SystemInfo, TabKey } from "@/lib/types";

export default function Home() {
  const [activeTab, setActiveTab] = useState<TabKey>("detect");
  const [systemInfo, setSystemInfo] = useState<SystemInfo | null>(null);
  const [municipalityCount, setMunicipalityCount] = useState<number | null>(null);
  const [gisDataLoaded, setGisDataLoaded] = useState(false);

  const { data: summary, lastUpdated, refetch } = useDashboardSummary();

  useEffect(() => {
    getSystemInfo()
      .then(setSystemInfo)
      .catch(() => setSystemInfo(null));
  }, []);

  function handleGisDataLoaded(points: GisDataPoint[]) {
    setMunicipalityCount(new Set(points.map((p) => p.municipality)).size);
    setGisDataLoaded(true);
  }

  return (
    <div className="dashboard-wrapper">
      <TopNavBar activeTab={activeTab} onTabChange={setActiveTab} systemInfo={systemInfo} onRefresh={refetch} />

      <HeroSection summary={summary} />

      <StepperPipeline hasSurveyData={(summary?.total_images ?? 0) > 0} gisDataLoaded={gisDataLoaded} />

      <SubNavRow activeTab={activeTab} onTabChange={setActiveTab} />


      <div className="workspace-container" style={{ display: activeTab === "detect" ? "block" : "none" }}>
        <DetectorView />
      </div>
      <div className="workspace-container" style={{ display: activeTab === "gis" ? "block" : "none" }}>
        <GisView isActive={activeTab === "gis"} onDataLoaded={handleGisDataLoaded} />
      </div>
      <div className="workspace-container" style={{ display: activeTab === "analytics" ? "block" : "none" }}>
        <AnalyticsView isActive={activeTab === "analytics"} />
      </div>
      <div className="workspace-container" style={{ display: activeTab === "train" ? "block" : "none" }}>
        <TrainView onDashboardRefetch={refetch} />
      </div>
    </div>
  );
}
