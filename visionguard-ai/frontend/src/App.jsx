import { useEffect, useRef, useState } from 'react';
import { analyzeImage, analyzeVideo, fetchHistory, getApiUrl, healthCheck } from './services/api';

const navItems = ['Dashboard', 'AI Analysis', 'AI Risk Replay', 'History', 'About'];

const riskStyles = {
  LOW: 'risk-badge low',
  MEDIUM: 'risk-badge medium',
  HIGH: 'risk-badge high',
};

function App() {
  const [health, setHealth] = useState({ status: 'offline' });
  const [history, setHistory] = useState([]);
  const [activeTab, setActiveTab] = useState('Dashboard');
  const [selectedFile, setSelectedFile] = useState(null);
  const [mediaType, setMediaType] = useState('image');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const [currentTime, setCurrentTime] = useState(0);
  const [demoScene, setDemoScene] = useState('Traffic');
  const [dragging, setDragging] = useState(false);
  const videoRef = useRef(null);

  useEffect(() => {
    loadHealth();
    loadHistory();
  }, []);

  const loadHealth = async () => {
    try {
      const res = await healthCheck();
      setHealth(res.data);
    } catch (err) {
      setHealth({ status: 'offline' });
    }
  };

  const loadHistory = async () => {
    try {
      const res = await fetchHistory();
      setHistory(res.data || []);
    } catch (err) {
      console.error(err);
    }
  };

  const handleFileSelect = (event) => {
    const file = event.target.files?.[0];
    if (file) setSelectedFile(file);
  };

  const setFile = (file) => {
    if (file) setSelectedFile(file);
  };

  const handleAnalyze = async () => {
    if (!selectedFile) {
      setError('Please choose an image or video to analyze.');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const response = mediaType === 'image' ? await analyzeImage(selectedFile) : await analyzeVideo(selectedFile);
      setResult(response.data);
      await loadHistory();
    } catch (err) {
      const detail = err.response?.data?.detail || 'Analysis failed. Please try again.';
      setError(detail);
    } finally {
      setLoading(false);
    }
  };

  const getMetricCards = () => {
    const stats = result?.stats || {};
    return [
      { label: 'AI MODEL', value: health.status === 'ok' ? 'ONLINE' : 'OFFLINE', accent: health.status === 'ok' ? 'emerald' : 'rose' },
      { label: 'Total detections', value: stats.total_objects ?? result?.count ?? 0 },
      { label: 'Persons', value: stats.persons ?? 0 },
      { label: 'Vehicles', value: stats.vehicles ?? 0 },
      { label: 'Avg confidence', value: `${Number(stats.avg_confidence ?? 0).toFixed(2)}%` },
      { label: 'Risk score', value: result?.risk?.risk_score ?? stats.risk_score ?? 0 },
    ];
  };

  const timeline = result?.timeline || [];
  const peakRisk = result?.peak_risk || (timeline.length ? timeline.reduce((max, entry) => (entry.risk_score > max.risk_score ? entry : max), timeline[0]) : null);

  const getOutputUrl = (path) => {
    if (!path || path.startsWith('http')) return path || '';
    const normalizedPath = path.startsWith('/') ? path : `/${path.replace(/\\/g, '/').replace(/^.*?outputs\//, 'outputs/')}`;
    return getApiUrl(normalizedPath);
  };

  const handleSeekToPeak = () => {
    if (!videoRef.current || !peakRisk?.timestamp) return;
    const [hh, mm, ss] = peakRisk.timestamp.split(':').map(Number);
    const seconds = hh * 3600 + mm * 60 + ss;
    if (Number.isFinite(seconds)) {
      videoRef.current.currentTime = seconds;
      setCurrentTime(seconds);
    }
  };

  const renderDashboard = () => (
    <div className="space-y-6">
      <section className="hero">
        <div className="hero-kicker">Vision intelligence workspace</div>
        <h2>Make every scene <span className="gradient-text">safer with AI.</span></h2>
        <p>Upload security footage or an image to identify objects, assess operational risk, and turn visual data into a clear safety decision.</p>
      </section>
      <section className="stats-grid">
        {getMetricCards().map((card) => (
          <div key={card.label} className="metric-card">
            <div className="metric-label">{card.label}</div>
            <div className={`metric-value ${card.accent === 'emerald' ? 'text-emerald-300' : card.accent === 'rose' ? 'text-rose-300' : 'text-white'}`}>
              {card.value}
            </div>
          </div>
        ))}
      </section>

      <section className="analysis-grid">
        <div className="panel upload-card">
          <div className="panel-header">
            <div className="panel-title">AI Analysis</div>
            <div className="segmented">
              <button className={mediaType === 'image' ? 'active' : ''} onClick={() => setMediaType('image')}>Image</button>
              <button className={mediaType === 'video' ? 'active' : ''} onClick={() => setMediaType('video')}>Video</button>
            </div>
          </div>

          <div
            className={`upload-dropzone ${dragging ? 'dragging' : ''}`}
            onDragOver={(event) => { event.preventDefault(); setDragging(true); }}
            onDragLeave={() => setDragging(false)}
            onDrop={(event) => { event.preventDefault(); setDragging(false); setFile(event.dataTransfer.files?.[0]); }}
          >
            <input
              type="file"
              accept=".jpg,.jpeg,.png,.mp4,.avi,.mov,image/jpeg,image/png,video/mp4,video/avi,video/quicktime"
              onChange={handleFileSelect}
              className="upload-input"
              id="file-input"
            />
            <label htmlFor="file-input" className="dropzone-label">
              <div className="file-name">{selectedFile ? selectedFile.name : 'Drag & drop or browse files'}</div>
              <div className="helper-copy">JPG, JPEG, PNG, MP4, AVI, MOV</div>
            </label>
          </div>

          <div className="demo-row">
            <span className="demo-label">Demo environments</span>
            {['Traffic', 'Crowd', 'Warehouse'].map((scene) => (
              <button key={scene} type="button" className={`demo-button ${demoScene === scene ? 'active' : ''}`} onClick={() => setDemoScene(scene)}>{scene}</button>
            ))}
          </div>

          <button onClick={handleAnalyze} disabled={loading || !selectedFile} className="primary-button">
            {loading ? 'Analyzing...' : `Analyze ${mediaType === 'image' ? 'Image' : 'Video'}`}
          </button>

          {error && <div className="reason-box">{error}</div>}
        </div>

        <div className="panel">
          <div className="panel-header">
            <div className="panel-title">Risk Assessment</div>
          </div>
          <div className="panel-body">
            {result ? (
              <div>
                <div className={`risk-card ${String(result.risk?.risk_level || 'LOW').toLowerCase()}`}>
                  <div className="risk-label">Risk level</div>
                  <div className="risk-value">{result.risk?.risk_level}</div>
                <div className="risk-score-copy">{result.risk?.risk_score}/100</div>
                </div>
                <div className="reason-box">
                  <div className="reason-title">Reason</div>
                  <p>{result.risk?.reason}</p>
                </div>
              </div>
            ) : (
              <div className="empty-state">No analysis results yet.</div>
            )}
          </div>
        </div>
      </section>

      <section className="results-grid">
        <div className="panel">
          <div className="panel-header">
            <div className="panel-title">Results</div>
          </div>
          <div className="panel-body">
            {result?.output_path ? (
              <div className="preview-box">
                {mediaType === 'video' ? (
                  <video ref={videoRef} controls onTimeUpdate={(e) => setCurrentTime(e.target.currentTime)}>
                    <source src={getOutputUrl(result.output_path)} type="video/mp4" />
                  </video>
                ) : (
                  <img src={getOutputUrl(result.output_path)} alt="Detection output" />
                )}
              </div>
            ) : (
              <div className="empty-state">Processed analysis preview will appear here.</div>
            )}
          </div>
        </div>

        <div className="panel">
          <div className="panel-header">
            <div className="panel-title">Detection Statistics</div>
          </div>
          <div className="panel-body">
            {result?.stats ? (
              <div className="stats-list">
                <div className="stat-row"><span className="stat-name">Total objects</span><span className="stat-value">{result.stats.total_objects}</span></div>
                <div className="stat-row"><span className="stat-name">Persons</span><span className="stat-value">{result.stats.persons}</span></div>
                <div className="stat-row"><span className="stat-name">Vehicles</span><span className="stat-value">{result.stats.vehicles}</span></div>
                <div className="stat-row"><span className="stat-name">Avg. confidence</span><span className="stat-value">{Number(result.stats.avg_confidence || 0).toFixed(2)}%</span></div>
                <div className="stat-row"><span className="stat-name">Density</span><span className="stat-value">{Number(result.stats.density || 0).toFixed(1)}</span></div>
                <div className="stat-row"><span className="stat-name">Activity</span><span className="stat-value">{Number(result.stats.activity_level || 0).toFixed(1)}</span></div>
              </div>
            ) : (
              <div className="empty-state">Statistics will update after upload.</div>
            )}
          </div>
        </div>
      </section>

      {timeline.length > 0 && (
        <section className="panel">
          <div className="panel-header">
            <div className="panel-title">AI Risk Replay</div>
            {peakRisk && (
              <button className="secondary-button" onClick={handleSeekToPeak}>Seek to peak risk</button>
            )}
          </div>
          <div className="panel-body">
            {peakRisk && (
              <div className="mt-0 rounded-2xl border border-amber-500/30 bg-amber-500/10 p-4">
                <div className="text-[10px] uppercase tracking-[0.24em] text-amber-200">Peak risk</div>
                <div className="mt-2 text-2xl font-bold text-white">{peakRisk.timestamp}</div>
                <div className="text-lg text-amber-200">{peakRisk.risk_score} / 100</div>
                <div className="text-sm text-amber-100">{peakRisk.risk_level}</div>
              </div>
            )}

            <div className="timeline-box">
              {timeline.map((sample) => (
                <button
                  key={`${sample.timestamp}-${sample.risk_score}`}
                  onClick={() => {
                    if (videoRef.current) {
                      const [hh, mm, ss] = sample.timestamp.split(':').map(Number);
                      const seconds = hh * 3600 + mm * 60 + ss;
                      videoRef.current.currentTime = seconds;
                      setCurrentTime(seconds);
                    }
                  }}
                  className={`timeline-item ${sample.is_peak ? 'peak' : ''}`}
                >
                  <div>
                    <div className="timeline-title">{sample.timestamp}</div>
                    <div className="timeline-meta">{sample.total_objects} objects • {sample.persons} persons • {sample.vehicles} vehicles</div>
                  </div>
                  <div className="text-right">
                    <div className="timeline-score">{sample.risk_score}/100</div>
                    <div className={riskStyles[sample.risk_level] || 'risk-badge low'}>{sample.risk_level}</div>
                  </div>
                </button>
              ))}
            </div>
          </div>
        </section>
      )}

      <section className="panel">
        <div className="panel-header">
          <div className="panel-title">History</div>
        </div>
        <div className="panel-body">
          {history.length === 0 ? (
            <div className="empty-state">No analysis history yet.</div>
          ) : (
            <div className="history-grid">
              {history.slice(0, 3).map((item) => (
                <div key={item.id} className="history-card">
                  <div className="history-name">{item.filename}</div>
                  <div className="history-score">{item.risk_score}/100</div>
                  <div className={riskStyles[item.risk_level] || 'risk-badge low'}>{item.risk_level}</div>
                </div>
              ))}
            </div>
          )}
        </div>
      </section>
    </div>
  );

  const renderHistory = () => (
    <div className="panel">
      <div className="panel-header">
        <div className="panel-title">Analysis history</div>
      </div>
      <div className="panel-body">
        {history.length === 0 ? (
          <div className="empty-state">No analysis history yet.</div>
        ) : (
          <div className="space-y-3">
            {history.map((item) => (
              <div key={item.id} className="rounded-2xl border border-slate-700 bg-slate-950/60 p-4">
                <div className="flex items-center justify-between gap-4">
                  <div>
                    <div className="font-semibold text-white">{item.filename}</div>
                    <div className="text-xs text-slate-400">{item.created_at} • {item.media_type}</div>
                  </div>
                  <span className={riskStyles[item.risk_level] || 'risk-badge low'}>{item.risk_level}</span>
                </div>
                <div className="mt-3 grid gap-2 text-sm text-slate-300 sm:grid-cols-4">
                  <div>Detections: {item.detection_count}</div>
                  <div>Risk: {item.risk_score}/100</div>
                  <div>Peak: {item.peak_timestamp || '—'}</div>
                  <div>ID: {item.id}</div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );

  const renderAbout = () => (
    <div className="panel">
      <div className="panel-header">
        <div className="panel-title">About VisionGuard AI</div>
      </div>
      <div className="panel-body about-copy">
        <p>VisionGuard AI monitors live environments with computer vision, object detection, and risk scoring to highlight activity that demands attention.</p>
        <p>Built for safety teams, operations centers, and AI demos, the system combines YOLO inference, annotated previews, and trend analysis into a single operational dashboard.</p>
        <div className="grid gap-4 md:grid-cols-2">
          <div className="rounded-2xl border border-slate-700 bg-slate-950/60 p-4">
            <div className="font-semibold text-white">Technology stack</div>
            <ul className="mt-2 space-y-1 text-slate-300">
              <li>Python + FastAPI</li>
              <li>Ultralytics YOLOv8n</li>
              <li>OpenCV</li>
              <li>SQLite</li>
              <li>React + Vite</li>
            </ul>
          </div>
          <div className="rounded-2xl border border-slate-700 bg-slate-950/60 p-4">
            <div className="font-semibold text-white">AI pipeline</div>
            <ul className="mt-2 space-y-1 text-slate-300">
              <li>Upload image or video</li>
              <li>Detect objects and confidence</li>
              <li>Estimate risk score</li>
              <li>Highlight peak-risk moments</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );

  const renderContent = () => {
    if (activeTab === 'Dashboard') return renderDashboard();
    if (activeTab === 'AI Analysis') return renderDashboard();
    if (activeTab === 'Video Analysis') return renderDashboard();
    if (activeTab === 'AI Risk Replay') return renderDashboard();
    if (activeTab === 'History') return renderHistory();
    if (activeTab === 'About') return renderAbout();
    return renderDashboard();
  };

  return (
    <div className="app-shell">
      <div className="dashboard-shell">
        <aside className="sidebar">
          <div className="brand-box">
            <div className="brand-mark">V</div>
            <div>
              <div className="brand-title">VisionGuard AI</div>
              <div className="brand-subtitle">Safety Monitor</div>
            </div>
          </div>

          <nav className="nav-panel">
            {navItems.map((item, index) => (
              <button
                key={item}
                onClick={() => {
                  setActiveTab(item);
                  if (item === 'AI Analysis') {
                    setMediaType('image');
                  }
                }}
                className={`nav-button ${activeTab === item ? 'active' : ''}`}
              >
                <span>{item}</span>
                <span className="nav-index">{String(index + 1).padStart(2, '0')}</span>
              </button>
            ))}
          </nav>
        </aside>

        <main className="main-panel">
          <header className="topbar">
            <div>
              <div className="eyebrow">Intelligent Real-Time Safety Monitoring</div>
              <h1 className="header-title">See the Risk. Detect the Threat. Act Faster.</h1>
            </div>
            <div className="status-pill">
              <span className="status-dot" />
              <span className="status-text">{health.status === 'ok' ? 'AI MODEL ONLINE • YOLOv8n' : 'AI MODEL OFFLINE'}</span>
            </div>
          </header>

          <div className="content-wrap">{renderContent()}</div>
        </main>
      </div>
    </div>
  );
}

export default App;
