/**
 * CrackMap Executive Web App JavaScript.
 * 100% Dynamic data binding, live dataset summary, custom image batch ingestion,
 * real-time PyTorch fine-tuning polling, and interactive Leaflet GIS mapping.
 */

let currentTab = 'detect';
let mapInstance = null;
let trainPollInterval = null;

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    fetchDashboardSummary();
    loadSampleList();
});

// 1. Fetch & Bind 100% Dynamic Dashboard Summary
async function fetchDashboardSummary() {
    try {
        const res = await fetch('/api/dashboard-summary');
        const data = await res.json();

        // Bind Hero Numbers
        const elSurveyed = document.getElementById('hero-surveyed-area');
        const elVerified = document.getElementById('hero-verified-pavement');
        const elHazards = document.getElementById('hero-hazards-count');
        const elFrames = document.getElementById('hero-frames-count');

        if (elSurveyed) elSurveyed.innerHTML = `${data.surveyed_area_m2.toLocaleString()}<sup>m²</sup>`;
        if (elVerified) elVerified.innerHTML = `${data.verified_pavement_m2.toLocaleString()}<sup>m²</sup>`;
        if (elHazards) elHazards.innerHTML = `${data.total_defects}<sup>pts</sup>`;
        if (elFrames) elFrames.innerHTML = `${data.total_images}<sup>imgs</sup>`;

        // Bind Dark Card Stats & Equalizer
        const elPotholes = document.getElementById('legend-potholes-count');
        const elCracks = document.getElementById('legend-cracks-count');
        if (elPotholes) elPotholes.textContent = data.potholes_count;
        if (elCracks) elCracks.textContent = data.cracks_count;

        renderDynamicEqualizer(data.potholes_count, data.cracks_count, data.total_defects);

        // Bind Quadrant Cards
        const elAvgSev = document.getElementById('card-avg-severity');
        const elSevDesc = document.getElementById('card-severity-desc');
        const elPci = document.getElementById('card-pci');

        if (elAvgSev) elAvgSev.innerHTML = `${data.avg_severity}<span style="font-size:1.1rem;color:#64748b;"> /defect</span>`;
        if (elSevDesc) {
            if (data.avg_severity >= 2.5) {
                elSevDesc.innerHTML = '🔴 Priority Resurfacing Required';
                elSevDesc.style.color = '#ef4444';
            } else if (data.avg_severity >= 1.5) {
                elSevDesc.innerHTML = '🟡 Maintenance Recommended';
                elSevDesc.style.color = '#eab308';
            } else {
                elSevDesc.innerHTML = '🟢 Routine Maintenance Level';
                elSevDesc.style.color = '#16a34a';
            }
        }
        if (elPci) elPci.innerHTML = `${data.pci_score}<span style="font-size:1.1rem;color:#64748b;"> %</span>`;

        // Dynamic Micro-Bars in Peach Card
        renderMicroBars(data.class_distribution);

    } catch (err) {
        console.error('Failed to fetch dashboard summary:', err);
    }
}

// 2. Render Dynamic Equalizer Dot Grid based on real data
function renderDynamicEqualizer(potholes, cracks, totalDefects) {
    const grid = document.getElementById('equalizer-grid');
    if (!grid) return;
    grid.innerHTML = '';

    const cols = 20;
    const rows = 4;
    const totalSlots = cols * rows;

    const potholeSlots = Math.min(totalSlots, potholes * 3);
    const crackSlots = Math.min(totalSlots - potholeSlots, cracks * 2);

    for (let i = 0; i < totalSlots; i++) {
        const dot = document.createElement('div');
        dot.className = 'matrix-dot';

        if (i < potholeSlots) {
            dot.classList.add('active-red');
        } else if (i < (potholeSlots + crackSlots)) {
            dot.classList.add('active-teal');
        }

        grid.appendChild(dot);
    }
}

// 3. Render Dynamic Micro-Bars
function renderMicroBars(classDist) {
    const container = document.getElementById('micro-bar-container');
    if (!container || !classDist) return;
    container.innerHTML = '';

    const keyClasses = [
        { code: 'D00', label: 'Long.' },
        { code: 'D10', label: 'Trans.' },
        { code: 'D20', label: 'Allig.' },
        { code: 'D40', label: 'Pothole' }
    ];

    const maxVal = Math.max(1, ...keyClasses.map(k => classDist[k.code] || 0));

    keyClasses.forEach(k => {
        const val = classDist[k.code] || 0;
        const pct = Math.max(15, Math.round((val / maxVal) * 90));
        
        const col = document.createElement('div');
        col.className = 'bar-col';
        col.innerHTML = `
            <div class="bar-fill" style="height: ${pct}%; background: ${k.code === 'D40' ? '#22c55e' : (k.code === 'D20' ? '#60a5fa' : '#cbd5e1')};"></div>
            <span class="bar-tag">${val}</span>
        `;
        container.appendChild(col);
    });
}

// 4. Tab Navigation
function switchTab(tabName) {
    currentTab = tabName;
    
    // Update pill buttons
    document.querySelectorAll('.nav-pill-btn').forEach(btn => btn.classList.remove('active'));
    const activePill = document.getElementById(`pill-${tabName}`);
    if (activePill) activePill.classList.add('active');

    // Update sub-pills
    document.querySelectorAll('.sub-pill').forEach((btn, idx) => {
        btn.classList.toggle('active', (tabName === 'detect' && idx === 0) || (tabName === 'gis' && idx === 1) || (tabName === 'analytics' && idx === 2) || (tabName === 'train' && idx === 3));
    });

    // Hide all views
    document.getElementById('view-detect').style.display = 'none';
    document.getElementById('view-gis').style.display = 'none';
    document.getElementById('view-analytics').style.display = 'none';
    document.getElementById('view-train').style.display = 'none';

    // Show selected view
    const targetView = document.getElementById(`view-${tabName}`);
    if (targetView) targetView.style.display = 'block';

    if (tabName === 'gis') {
        setTimeout(initLeafletMap, 100);
    } else if (tabName === 'analytics') {
        fetchDatasetStats();
    }
}

// 5. Load Benchmark Samples List
async function loadSampleList() {
    try {
        const res = await fetch('/api/samples');
        const data = await res.json();
        const select = document.getElementById('sample-select');
        if (select && data.samples) {
            data.samples.forEach(s => {
                const opt = document.createElement('option');
                opt.value = s;
                opt.textContent = s;
                select.appendChild(opt);
            });
        }
    } catch (err) {
        console.error('Failed to load sample list:', err);
    }
}

// 6. Handle Sample Select
async function loadSampleImage(sampleName) {
    if (!sampleName) return;
    
    const formData = new FormData();
    formData.append('sample_name', sampleName);
    formData.append('conf_threshold', '0.25');

    runDetection(formData);
}

// 7. Handle Single File Upload for Inspection
function handleFileUpload(event) {
    const file = event.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);
    formData.append('conf_threshold', '0.25');

    runDetection(formData);
}

// 8. Run AI Detection & Sync Metrics
async function runDetection(formData) {
    const resultsSec = document.getElementById('results-section');
    const tableSec = document.getElementById('table-section');
    const rawPreview = document.getElementById('raw-preview');
    const annoPreview = document.getElementById('annotated-preview');
    const latencyBadge = document.getElementById('latency-badge');
    const tbody = document.getElementById('defect-table-body');
    const cardPci = document.getElementById('card-pci');

    try {
        latencyBadge.textContent = 'Analyzing...';
        resultsSec.style.display = 'grid';

        const res = await fetch('/api/detect', {
            method: 'POST',
            body: formData
        });
        const data = await res.json();

        if (data.success) {
            rawPreview.src = data.original_image;
            annoPreview.src = data.annotated_image;
            latencyBadge.textContent = `${data.inference_time_ms} ms · ${data.total_defects} defects`;
            
            if (cardPci) {
                cardPci.innerHTML = `${data.pci_score}<span style="font-size:1.1rem;color:#64748b;"> %</span>`;
            }

            // Populate Table
            tbody.innerHTML = '';
            if (data.boxes && data.boxes.length > 0) {
                tableSec.style.display = 'block';
                data.boxes.forEach(b => {
                    const row = document.createElement('tr');
                    row.innerHTML = `
                        <td><strong>${b.index}</strong></td>
                        <td><span class="defect-pill" style="background: rgba(${hexToRgb(b.color)}, 0.15); color: ${b.color}; border: 1px solid ${b.color};">${b.code}</span></td>
                        <td><strong>${b.name}</strong></td>
                        <td>${b.category}</td>
                        <td><span style="color: ${b.severity === 'Critical' ? '#ef4444' : '#f59e0b'}; font-weight:700;">${b.severity}</span></td>
                        <td>${b.confidence}%</td>
                        <td><code>[${b.box.join(', ')}]</code></td>
                        <td>${b.area.toLocaleString()}</td>
                    `;
                    tbody.appendChild(row);
                });
            } else {
                tableSec.style.display = 'none';
            }
        }
    } catch (err) {
        console.error('Detection failed:', err);
        latencyBadge.textContent = 'Error';
    }
}

// 9. Batch Pothole Images Ingestion
async function handleBatchUpload(event) {
    const files = event.target.files;
    if (!files || files.length === 0) return;

    const statusDiv = document.getElementById('batch-upload-status');
    statusDiv.style.display = 'block';
    statusDiv.innerHTML = `⏳ Ingesting and auto-annotating ${files.length} custom road images...`;

    const formData = new FormData();
    for (let i = 0; i < files.length; i++) {
        formData.append('files', files[i]);
    }

    try {
        const res = await fetch('/api/upload-pothole-images', {
            method: 'POST',
            body: formData
        });
        const data = await res.json();

        if (data.success) {
            statusDiv.innerHTML = `✅ ${data.message}`;
            // Refresh dynamic summary
            fetchDashboardSummary();
        } else {
            statusDiv.innerHTML = `❌ Error: ${data.message || 'Upload failed'}`;
        }
    } catch (err) {
        console.error('Batch upload error:', err);
        statusDiv.innerHTML = '❌ Upload failed due to network/server error';
    }
}

// 10. Trigger Model Fine-Tuning Run & Live Polling
async function triggerTrainingRun() {
    const epochs = document.getElementById('train-epochs').value;
    const bs = document.getElementById('train-bs').value;
    const lr = document.getElementById('train-lr').value;
    const arch = document.getElementById('train-arch').value;

    const btn = document.getElementById('btn-start-train');
    const progressBox = document.getElementById('train-progress-box');
    const statusText = document.getElementById('train-status-text');
    const lossText = document.getElementById('train-loss-text');
    const progressBar = document.getElementById('train-progress-bar');
    const logBox = document.getElementById('train-log-messages');

    btn.disabled = true;
    btn.textContent = 'Training in Progress...';
    progressBox.style.display = 'block';
    logBox.innerHTML = '<div>Initiating PyTorch neural network training...</div>';

    const formData = new FormData();
    formData.append('epochs', epochs);
    formData.append('batch_size', bs);
    formData.append('learning_rate', lr);
    formData.append('architecture', arch);

    try {
        const res = await fetch('/api/train-model', {
            method: 'POST',
            body: formData
        });
        const data = await res.json();

        if (data.success) {
            // Start Polling Training Status
            if (trainPollInterval) clearInterval(trainPollInterval);
            trainPollInterval = setInterval(async () => {
                const sRes = await fetch('/api/train-status');
                const sData = await sRes.json();

                if (sData.status === 'training') {
                    const pct = Math.round(sData.progress * 100);
                    progressBar.style.width = `${pct}%`;
                    statusText.textContent = `Epoch ${sData.current_epoch}/${sData.total_epochs} (${pct}%)`;
                    lossText.textContent = `Loss: ${sData.current_loss}`;
                    
                    if (sData.losses && sData.losses.length > 0) {
                        const last = sData.losses[sData.losses.length - 1];
                        logBox.innerHTML = sData.losses.map(l => `<div>• Epoch ${l.epoch} — Loss: <b>${l.loss}</b></div>`).join('');
                        logBox.scrollTop = logBox.scrollHeight;
                    }
                } else if (sData.status === 'completed') {
                    clearInterval(trainPollInterval);
                    progressBar.style.width = '100%';
                    statusText.textContent = '✅ Fine-Tuning Complete!';
                    btn.disabled = false;
                    btn.textContent = '🚀 Start Real Model Fine-Tuning';
                    logBox.innerHTML += `<div><strong>🎉 Checkpoint saved: ${sData.checkpoint_path}</strong></div>`;
                    fetchDashboardSummary();
                } else if (sData.status === 'failed') {
                    clearInterval(trainPollInterval);
                    statusText.textContent = '❌ Training Failed';
                    lossText.textContent = sData.error || 'Error occurred';
                    btn.disabled = false;
                    btn.textContent = '🚀 Start Real Model Fine-Tuning';
                }
            }, 800);
        } else {
            alert(data.message || 'Could not start training');
            btn.disabled = false;
            btn.textContent = '🚀 Start Real Model Fine-Tuning';
        }
    } catch (err) {
        console.error('Failed to trigger training:', err);
        btn.disabled = false;
        btn.textContent = '🚀 Start Real Model Fine-Tuning';
    }
}

// 11. Initialize Leaflet GIS CrackMap
async function initLeafletMap() {
    if (mapInstance) {
        mapInstance.invalidateSize();
        return;
    }

    const mapContainer = document.getElementById('leaflet-map');
    if (!mapContainer) return;

    mapInstance = L.map('leaflet-map').setView([35.6762, 139.6503], 12);

    L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png', {
        attribution: '&copy; OpenStreetMap contributors & CartoDB',
        maxZoom: 19
    }).addTo(mapInstance);

    try {
        const res = await fetch('/api/gis-data');
        const points = await res.json();

        points.forEach(pt => {
            const marker = L.circleMarker([pt.lat, pt.lon], {
                radius: pt.severity_score * 4 + 4,
                fillColor: pt.color_hex || '#ef4444',
                color: '#ffffff',
                weight: 1.5,
                opacity: 1,
                fillOpacity: 0.85
            }).addTo(mapInstance);

            marker.bindPopup(`
                <div style="font-family:'Plus Jakarta Sans',sans-serif; padding:4px;">
                    <b style="color:#0f172a; font-size:1.1em;">${pt.damage_code}: ${pt.damage_type}</b><br/>
                    <b>Severity:</b> <span style="color:#ef4444;">${pt.severity}</span> (Score: ${pt.severity_score}/5)<br/>
                    <b>Confidence:</b> ${(pt.confidence * 100).toFixed(0)}%<br/>
                    <b>Municipality:</b> ${pt.municipality}
                </div>
            `);
        });
    } catch (err) {
        console.error('Failed to load GIS data:', err);
    }
}

// 12. Dataset Statistics Explorer
async function fetchDatasetStats() {
    try {
        const res = await fetch('/api/dataset-stats');
        const stats = await res.json();
        const container = document.getElementById('analytics-content');
        if (container && stats) {
            let distHtml = '<div style="display:grid; grid-template-columns: repeat(4, 1fr); gap:16px; margin-top:16px;">';
            for (const [cls, count] of Object.entries(stats.class_distribution || {})) {
                distHtml += `
                    <div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:16px; padding:16px; text-align:center;">
                        <span style="font-weight:800; font-size:1.2rem; color:#0f172a;">${cls}</span>
                        <div style="font-size:1.8rem; font-weight:900; color:#3b82f6; margin:4px 0;">${count}</div>
                        <span style="font-size:0.78rem; color:#64748b; font-weight:600;">Defect Instances</span>
                    </div>
                `;
            }
            distHtml += '</div>';

            container.innerHTML = `
                <div style="display:flex; gap:24px; margin-bottom:20px; flex-wrap:wrap;">
                    <div style="background:#ebf6ee; padding:16px 24px; border-radius:16px;"><strong>Total Images:</strong> ${stats.total_images}</div>
                    <div style="background:#faebe0; padding:16px 24px; border-radius:16px;"><strong>Damaged Frames:</strong> ${stats.damaged_images}</div>
                    <div style="background:#eaf2fc; padding:16px 24px; border-radius:16px;"><strong>Total Defects:</strong> ${stats.total_boxes}</div>
                </div>
                <h4>Damage Class Distribution (VOC Dataset)</h4>
                ${distHtml}
            `;
        }
    } catch (err) {
        console.error('Failed to load dataset stats:', err);
    }
}

// Helper: Hex to RGB
function hexToRgb(hex) {
    if (!hex) return '239, 68, 68';
    hex = hex.replace('#', '');
    if (hex.length === 3) {
        hex = hex.split('').map(c => c + c).join('');
    }
    const num = parseInt(hex, 16);
    return `${(num >> 16) & 255}, ${(num >> 8) & 255}, ${num & 255}`;
}
