# Reviewing the auto-generated pothole labels

The detector has pre-drawn boxes for all 199 images. They are **deliberately
over-proposed** (run at confidence 0.12), because deleting a wrong box is much
faster than hunting for and drawing a missed one.

Your job is a cleanup pass, not a labelling-from-scratch pass.

## What you have

```
data/real_potholes/JPEGImages/   199 images
data/real_potholes/labels/       199 .txt files  (704 boxes total)
```

Format is standard YOLO, one line per box:
`class x_center y_center width height` — all normalised 0-1, class is always `0` (pothole).

## Recommended tool: makesense.ai (browser, no install, nothing uploaded)

1. Open <https://www.makesense.ai> → **Get Started**
2. Drop in every image from `data/real_potholes/JPEGImages/`
3. Choose **Object Detection**
4. Create a single label named exactly `pothole`
5. **Actions → Import Annotations → YOLO**, select all files from
   `data/real_potholes/labels/` (and the label file if it asks — one line: `pothole`)
6. Fix the boxes (see rules below)
7. **Actions → Export Annotations → YOLO**, and unzip the result back over
   `data/real_potholes/labels/`, replacing the old files

Alternatives: [LabelImg](https://github.com/HumanSignal/labelImg) (desktop),
[CVAT](https://www.cvat.ai), or Roboflow — any of them read/write YOLO format.

## Rules for a good pass

**Delete a box when it is:**
- on a vehicle, person, tree, building, sign or sky
- on a shadow, wet sheen or a dark tar repair seam with no actual cavity
- a duplicate sitting on top of another box for the same pothole

**Add a box when:**
- an obvious pothole was missed — these images have many, and missed potholes
  are exactly what the current model is bad at, so this is the highest-value edit

**Tighten a box when:**
- it is far larger than the pothole (loose boxes teach loose predictions)

**Leave the file empty when:**
- the road genuinely has no potholes. Do **not** delete the empty `.txt`.
  Empty files are kept on purpose as negative examples — they are what teach
  the model to stop firing on clean tarmac.

Aim for consistency over perfection. One box per distinct pothole; if several
merge into one broken patch, one box around the patch is fine.

## Then train

```bash
python train_potholes.py train            # ~60 epochs, uses your GPU
```

Weights are written to `models_saved/pothole_yolov8_finetuned.pt`. The detector
prefers that file over the stock models automatically — restart the backend
(`python backend_server.py`) and the app uses your model.

To sanity-check afterwards:

```bash
python train_potholes.py compare
```
