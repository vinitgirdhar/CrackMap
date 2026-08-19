import { Check } from "lucide-react";

interface StepperPipelineProps {
  hasSurveyData: boolean;
}

interface StepNode {
  label: string;
  state: "done" | "active" | "pending";
}

/**
 * Each node reflects a real backend capability:
 * - Input road imagery ingestion
 * - YOLOv8 pothole defect localization
 * - Frame-coverage severity and damage rating
 */
export function StepperPipeline({ hasSurveyData }: StepperPipelineProps) {
  const nodes: StepNode[] = [
    { label: "Input Road Imagery", state: hasSurveyData ? "done" : "active" },
    { label: "AI Pothole Localization", state: "done" },
    { label: "Severity & Damage Assessment", state: "done" },
  ];

  const doneCount = nodes.filter((n) => n.state === "done").length;

  const nodeCount = nodes.length;
  const edgePct = 50 / nodeCount;
  const trackWidthPct = 100 - 100 / nodeCount;
  const filledSegments = Math.max(0, doneCount - 1);
  const fillPct = nodeCount > 1 ? (filledSegments / (nodeCount - 1)) * trackWidthPct : 0;

  return (
    <div className="stepper-pipeline">
      <div className="stepper-track" style={{ left: `${edgePct}%`, width: `${trackWidthPct}%` }} />
      <div className="stepper-track-fill" style={{ left: `${edgePct}%`, width: `${fillPct}%` }} />
      {nodes.map((node, i) => (
        <div className="stepper-node" key={node.label}>
          <div className={`node-circle${node.state === "done" ? " done" : ""}${node.state === "active" ? " active" : ""}`}>
            {node.state === "done" ? <Check size={14} /> : i + 1}
          </div>
          <div className="node-label">{node.label}</div>
        </div>
      ))}
    </div>
  );
}
