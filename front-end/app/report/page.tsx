import type { Metadata } from "next";
import { Suspense } from "react";
import { CitizenReportPage } from "@/components/citizen/CitizenReportPage";

export const metadata: Metadata = {
  title: "Report a Pothole — CrackMap",
  description: "Report a road defect with a photo and a location, then track its repair.",
};

// useSearchParams (used to make a tracking link bookmarkable) forces the
// component tree under it to client-render; wrapping it in Suspense keeps
// that scoped to this page instead of deopting the whole route.
export default function ReportPage() {
  return (
    <Suspense fallback={null}>
      <CitizenReportPage />
    </Suspense>
  );
}
