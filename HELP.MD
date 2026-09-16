# Running CrackMap

### Backend
```powershell
cd "D:\Cooking stuff\CrackMap"
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

### Frontend
```powershell
cd "D:\Cooking stuff\CrackMap\front-end"
npm run dev
```

`front-end/.env.local` points the Next.js proxy at the backend — keep `BACKEND_URL` in sync if
you move the backend off port 8000.

---

## Civic pipeline: the simulated clock

Three stages advance on their own, without anyone clicking: the portal acknowledgement, the
crew mobilising, and the repair finishing. They run on a compressed clock so a full
intake → filing → tender → repair → re-inspection → closure cycle is watchable in under a
minute.

```powershell
# One municipal working day = 12 real seconds (the default)
$env:SIM_SECONDS_PER_DAY = "12"

# Slower, for a walkthrough: one day = 1 minute
$env:SIM_SECONDS_PER_DAY = "60"

# Real time: one day = one day
$env:SIM_SECONDS_PER_DAY = "86400"
```

Set it before starting uvicorn. The UI shows the active multiplier as a `simulated clock ×N`
badge in the Civic Pipeline tab.

## Driving the pipeline

1. **Inspection Studio** — pick a sample or upload a road photo, then in *Log this finding to
   the civic pipeline* capture the location (GPS or OpenStreetMap search) and log it. The road
   name, ward and OSM road class are resolved from the real coordinate.
2. **Civic Pipeline → Intake queue** — select findings and open a case. It arrives triaged
   (P1–P4) and costed (bill of quantities).
3. **Case board** — open the case and file it. It routes by coordinate to the authority that
   owns that road and gets a grievance number in that authority's own format.
4. Wait for the acknowledgement, float the tender, award a bid, then watch the repair run.
5. When the contractor reports completion, upload an **after-photo**. The same detector
   re-scores the road: a repair passes only if at most 34% of the original defects remain,
   otherwise it goes back as rework.
6. Close the case to release the **completion certificate**. The dossier, JSON and CSV exports
   are available at every stage.

## Resetting the demo data

Findings, cases, contractors and the audit trail live in one SQLite file:

```powershell
Remove-Item "D:\Cooking stuff\CrackMap\backend\data\crackmap.db"
```

It is recreated (with the seeded contractor panel) the next time the backend starts. There are
no demo map pins — the map only ever plots findings that were actually logged.

## Tests

```powershell
# Backend
cd "D:\Cooking stuff\CrackMap"; python -m pytest backend/tests/test_backend.py -q

# Frontend unit + end-to-end
cd "D:\Cooking stuff\CrackMap\front-end"; npm test; npx playwright test
```
