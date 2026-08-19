"use client";

import { useRef, useState } from "react";
import { CheckCircle2, Rocket, XCircle, Zap } from "lucide-react";
import { uploadPotholeImages } from "@/lib/api";
import { useTrainingPoll } from "@/lib/hooks/useTrainingPoll";

interface TrainViewProps {
  onDashboardRefetch: () => void;
}

const EPOCH_OPTIONS = [
  { value: 3, label: "3 Epochs (Fast)" },
  { value: 5, label: "5 Epochs (Recommended)" },
  { value: 10, label: "10 Epochs" },
  { value: 20, label: "20 Epochs" },
];
const BATCH_SIZE_OPTIONS = [2, 4, 8];
const LR_OPTIONS = [0.001, 0.005, 0.01];
const ARCH_OPTIONS = [
  { value: "fasterrcnn_mobilenet", label: "Faster R-CNN MobileNet" },
  { value: "ssdlite_mobilenet", label: "SSDLite MobileNet" },
];

export function TrainView({ onDashboardRefetch }: TrainViewProps) {
  const [epochs, setEpochs] = useState(5);
  const [batchSize, setBatchSize] = useState(4);
  const [learningRate, setLearningRate] = useState(0.005);
  const [architecture, setArchitecture] = useState("fasterrcnn_mobilenet");

  const [batchStatus, setBatchStatus] = useState<{ message: string; isError: boolean } | null>(null);
  const batchInputRef = useRef<HTMLInputElement>(null);

  const { status, isTraining, startError, start } = useTrainingPoll(onDashboardRefetch);

  async function handleBatchUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const files = e.target.files;
    if (!files || files.length === 0) return;

    setBatchStatus({ message: `Ingesting and auto-annotating ${files.length} custom road images...`, isError: false });
    try {
      const res = await uploadPotholeImages(files);
      if (res.success) {
        setBatchStatus({ message: res.message, isError: false });
        onDashboardRefetch();
      } else {
        setBatchStatus({ message: res.message || "Upload failed", isError: true });
      }
    } catch (err) {
      setBatchStatus({
        message: err instanceof Error ? err.message : "Upload failed due to network/server error",
        isError: true,
      });
    } finally {
      e.target.value = "";
    }
  }

  function handleStart() {
    void start({ epochs, batch_size: batchSize, learning_rate: learningRate, architecture });
  }

  const progressPct = status ? Math.round(status.progress * 100) : 0;
  const showProgress = status !== null;

  return (
    <div>
      <h3 className="section-headline">
        <Zap size={20} />
        Fine-Tune & Retrain AI Detector on Your Pothole Photos
      </h3>
      <p className="section-subtext">
        Upload multiple road/pothole images. The engine automatically labels defects and fine-tunes PyTorch
        neural network weights.
      </p>

      <div className="upload-dropzone" style={{ marginBottom: 20 }} onClick={() => batchInputRef.current?.click()}>
        <div className="dropzone-icon">
          <Rocket size={32} />
        </div>
        <div className="dropzone-text">Upload Custom Pothole Images (Batch)</div>
        <div className="dropzone-hint">Select one or multiple pothole photos from your computer</div>
        <input
          ref={batchInputRef}
          type="file"
          accept="image/*"
          multiple
          style={{ display: "none" }}
          onChange={handleBatchUpload}
        />
      </div>

      {batchStatus && (
        <div className={`batch-status${batchStatus.isError ? " error" : ""}`}>
          {batchStatus.isError ? <XCircle size={16} /> : <CheckCircle2 size={16} />}
          {batchStatus.message}
        </div>
      )}

      <div className="train-controls-grid">
        <div>
          <label className="field-label">Epochs</label>
          <select
            className="sample-select"
            style={{ width: "100%" }}
            value={epochs}
            onChange={(e) => setEpochs(Number(e.target.value))}
          >
            {EPOCH_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="field-label">Batch Size</label>
          <select
            className="sample-select"
            style={{ width: "100%" }}
            value={batchSize}
            onChange={(e) => setBatchSize(Number(e.target.value))}
          >
            {BATCH_SIZE_OPTIONS.map((opt) => (
              <option key={opt} value={opt}>
                {opt}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="field-label">Learning Rate</label>
          <select
            className="sample-select"
            style={{ width: "100%" }}
            value={learningRate}
            onChange={(e) => setLearningRate(Number(e.target.value))}
          >
            {LR_OPTIONS.map((opt) => (
              <option key={opt} value={opt}>
                {opt}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="field-label">Architecture</label>
          <select
            className="sample-select"
            style={{ width: "100%" }}
            value={architecture}
            onChange={(e) => setArchitecture(e.target.value)}
          >
            {ARCH_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      <button className="btn-primary" onClick={handleStart} disabled={isTraining} type="button">
        <Rocket size={16} />
        {isTraining ? "Training in Progress..." : "Start Real Model Fine-Tuning"}
      </button>

      {startError && (
        <p className="batch-status error" style={{ marginTop: 12 }}>
          {startError}
        </p>
      )}

      {showProgress && status && (
        <div className="train-progress-box">
          <div className="train-progress-row">
            <span>
              {status.status === "completed"
                ? "Fine-Tuning Complete"
                : status.status === "failed"
                  ? "Training Failed"
                  : `Epoch ${status.current_epoch}/${status.total_epochs} (${progressPct}%)`}
            </span>
            <span>
              {status.status === "failed" ? status.error || "Error occurred" : `Loss: ${status.current_loss}`}
            </span>
          </div>
          <div className="train-progress-track">
            <div
              className="train-progress-fill"
              style={{ width: `${status.status === "completed" ? 100 : progressPct}%` }}
            />
          </div>
          <div className="train-log">
            {status.losses.map((l) => (
              <div key={l.epoch}>
                Epoch {l.epoch} — Loss: <b>{l.loss}</b>
              </div>
            ))}
            {status.status === "completed" && <div>Checkpoint saved: {status.checkpoint_path}</div>}
          </div>
        </div>
      )}
    </div>
  );
}
