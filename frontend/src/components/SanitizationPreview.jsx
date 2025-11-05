import React, { useState, useEffect } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import axios from "axios";
import { requireLogin } from "../utils/auth";
import "../styles/SanitizationPreview.css";

/**
 * PII options used in the UI. Adjust labels/descriptions/icons as you wish.
 * NOTE: We will bucket backend keys to these UI labels via PII_KEY_MAP below.
 */
const PII_OPTIONS = [
  { value: "EMAIL", label: "Email", description: "Email addresses (e.g. name@example.com)", icon: "📧" },
  { value: "PHONE", label: "Phone", description: "Phone numbers (local / international)", icon: "📱" },
  { value: "NAME", label: "Name", description: "Person names", icon: "🧑" },
  { value: "ADDRESS", label: "Address", description: "Postal addresses", icon: "🏠" },
  { value: "CREDIT_CARD", label: "Card", description: "Credit / Debit card numbers", icon: "💳" },
  { value: "DOB", label: "DOB", description: "Date of birth", icon: "🎂" },
  { value: "ID", label: "IDs", description: "Government IDs (SSN / PAN / etc.)", icon: "🆔" },
  { value: "OTHER", label: "Other", description: "Other sensitive tokens", icon: "🔒" }
];

/**
 * Map backend keys to UI buckets.
 * E.g., PERSON/ORG → "Name", SSN/PASSPORT/DRIVERS_LICENSE/BANK_ACC → "IDs", etc.
 */
const PII_KEY_MAP = {
  EMAIL: "Email",
  PHONE: "Phone",
  PERSON: "Name",
  ORG: "Name",
  GPE: "Address",
  ADDRESS: "Address",
  CREDIT_CARD: "Card",
  DOB: "DOB",
  SSN: "IDs",
  PASSPORT: "IDs",
  DRIVERS_LICENSE: "IDs",
  BANK_ACC: "IDs",
  IP_ADDRESS: "Other",
  URL: "Other",
  MAC_ADDRESS: "Other"
};

// reduce `{TYPE:[...]}` into counts per UI bucket (Email/Phone/Name/Address/Card/DOB/IDs/Other)
const normalizeCounts = (piiFound = {}) => {
  const counts = {};
  Object.entries(piiFound).forEach(([rawKey, arr]) => {
    const key = String(rawKey).toUpperCase();
    const ui = PII_KEY_MAP[key] || key; // fall back to raw key if unmapped
    const n = Array.isArray(arr) ? arr.length : Number(arr) || 0;
    counts[ui] = (counts[ui] || 0) + n;
  });
  return counts;
};

const sumCounts = (counts = {}) =>
  Object.values(counts).reduce((s, n) => s + (Number(n) || 0), 0);

// sample values for a UI bucket (up to 3 examples)
const sampleValues = (piiFound = {}, uiKey, limit = 3) => {
  const wantedBackKeys = Object.entries(PII_KEY_MAP)
    .filter(([bk, ui]) => ui === uiKey)
    .map(([bk]) => bk);
  const values = [];
  for (const bk of wantedBackKeys) {
    const arr = piiFound[bk] || piiFound[bk.toUpperCase()];
    if (Array.isArray(arr)) values.push(...arr);
  }
  return [...new Set(values)].slice(0, limit);
};

const METHOD_INFO = {
  mask: { title: "Masking Preview", description: "Partially hides detected data but preserves context.", color: "#0ea5a4" },
  tokenize: { title: "Tokenization Preview", description: "Replaces values with reversible tokens.", color: "#7c3aed" },
  synthetic: { title: "Synthetic Replacement Preview", description: "Replaces values with realistic fake data.", color: "#06b6d4" },
  approve: { title: "Approve (No Change)", description: "Save the file unchanged.", color: "#64748b" }
};

const SanitizationPreview = () => {
  const { state } = useLocation();
  const navigate = useNavigate();
  const { file, method } = state || {};

  const [originalSnippet, setOriginalSnippet] = useState("");
  const [sanitizedSnippet, setSanitizedSnippet] = useState("");
  const [selectedPII, setSelectedPII] = useState([]);
  const [piiFound, setPiiFound] = useState({});     // raw map from backend {TYPE:[...]}
  const [piiCounts, setPiiCounts] = useState({});   // counts per UI bucket
  const [totalFound, setTotalFound] = useState(0);  // total sum across buckets
  const [loading, setLoading] = useState(true);
  const [processing, setProcessing] = useState(false);
  const [error, setError] = useState(null);
  const [previewInfo, setPreviewInfo] = useState(null);
  const token = localStorage.getItem("token");

  const pickSanitizeName = (file) =>
    (file?.stored_as || file?.filename || file?.name || "").split("\\").pop().split("/").pop();

  const nameToUse = pickSanitizeName(file);

  const handleCheckbox = (value) => {
    setSelectedPII(prev =>
      prev.includes(value) ? prev.filter(p => p !== value) : [...prev, value]
    );
  };

  const selectAll = () => setSelectedPII(PII_OPTIONS.map(opt => opt.value));
  const deselectAll = () => setSelectedPII([]);

  // common handler to ingest preview response and update state
  const ingestPreviewResponse = (res, isCSV, forInit = false) => {
    const data = res.data || {};
    const backendFound = data.pii_found || {};
    setPiiFound(backendFound);
    const counts = normalizeCounts(backendFound);
    setPiiCounts(counts);
    setTotalFound(sumCounts(counts));

    if (isCSV) {
      if (forInit) setOriginalSnippet(data.preview_rows || []);
      else setSanitizedSnippet(data.sanitized_rows || []);
      setPreviewInfo({
        previewLength: (forInit ? data.preview_rows : data.sanitized_rows)?.length || 0,
        totalLength: data.total_rows || 0
      });
    } else {
      if (forInit) setOriginalSnippet(data.original_snippet || "");
      else setSanitizedSnippet(data.sanitized_snippet || "");
      const previewLen = data.preview_length ||
        ((forInit ? data.original_snippet : data.sanitized_snippet) || "").length;
      const totalLen = data.total_length || (data.original_snippet || "").length;
      setPreviewInfo({ previewLength: previewLen, totalLength: totalLen });
    }

    // On init, pre-select types that actually have detections.
    if (forInit) {
      const foundTypes = Object.keys(backendFound).filter(
        (k) => Array.isArray(backendFound[k]) ? backendFound[k].length > 0 : Number(backendFound[k]) > 0
      );
      // Map backend found types to your UI option values if needed
      // We include raw keys too, since router accepts them.
      setSelectedPII(Array.from(new Set(foundTypes.map(k => String(k).toUpperCase()))));
    }
  };

  // Called to generate preview (user picks PII)
  const handleProcess = async () => {
    if (selectedPII.length === 0 && method !== "approve") {
      alert("Please select at least one PII type to sanitize");
      return;
    }
    setProcessing(true);
    setError(null);

    try {
      const res = await axios.post("http://localhost:8000/sanitize/preview", {
        file: nameToUse, method, pii: selectedPII, partial_mask: true, preserve_structure: true
      }, { headers: { Authorization: `Bearer ${token}` } });

      const isCSV = file.filename.toLowerCase().endsWith(".csv");
      ingestPreviewResponse(res, isCSV, false);
    } catch (err) {
      console.error("Preview error:", err);
      setError(err?.response?.data?.detail || "Failed to generate preview");
    } finally {
      setProcessing(false);
    }
  };

  // Confirm & save sanitized file
  const handleConfirm = async () => {
    if (!sanitizedSnippet && method !== "approve") {
      alert("Please process the preview first");
      return;
    }
    setProcessing(true);
    setError(null);

    try {
      const response = await axios.post("http://localhost:8000/sanitize/save", {
        file: nameToUse, method, pii: selectedPII, partial_mask: true, preserve_structure: true
      }, { headers: { Authorization: `Bearer ${token}` } });

      const stats = response.data || {};
      alert(
        `✅ File sanitized successfully!\n\n` +
        `Method: ${stats.method || method}\n` +
        `PII Redacted: ${stats.total_pii_redacted || 0}\n` +
        `Saved as: ${stats.sanitized_filename || 'n/a'}`
      );
      navigate("/analytics");
    } catch (err) {
      console.error("Save error:", err);
      setError(err?.response?.data?.detail || "Failed to save sanitized file");
    } finally {
      setProcessing(false);
    }
  };

  // Load a preview on mount (show detected PII and original snippet)
  useEffect(() => {
    const init = async () => {
      const userId = await requireLogin(navigate);
      if (!userId || !file) {
        navigate("/upload");
        return;
      }
      setLoading(true);
      setError(null);

      try {
        const res = await axios.post("http://localhost:8000/sanitize/preview", {
          file: nameToUse, method, pii: selectedPII, partial_mask: true, preserve_structure: true
        }, { headers: { Authorization: `Bearer ${token}` } });

        const isCSV = file.filename.toLowerCase().endsWith(".csv");
        ingestPreviewResponse(res, isCSV, true);
      } catch (err) {
        console.error("Initialization error:", err);
        setError(err?.response?.data?.detail || "Failed to load preview");
      } finally {
        setLoading(false);
      }
    };

    init();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [file, method, navigate]);

  const renderCSVPreview = (rows) => {
    if (!rows || rows.length === 0) return <div className="no-data">No data available</div>;
    const headers = Object.keys(rows[0] || {});
    return (
      <div className="csv-preview">
        <table>
          <thead>
            <tr>{headers.map(h => <th key={h}>{h}</th>)}</tr>
          </thead>
        </table>
        <div className="csv-body-scroll">
          <table>
            <tbody>
              {rows.map((row, i) => (
                <tr key={i}>
                  {headers.map(h => <td key={h}>{String(row[h] ?? "")}</td>)}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    );
  };

  if (!file) {
    return (
      <div className="sanitization-preview-page">
        <div className="error-message">
          <h3>❌ No file selected</h3>
          <button onClick={() => navigate("/upload")} className="btn-back">Go to Upload</button>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="sanitization-preview-page">
        <div className="loading-spinner">
          <div className="spinner" />
          <p>Loading preview...</p>
        </div>
      </div>
    );
  }

  const methodInfo = METHOD_INFO[method] || METHOD_INFO.approve;
  const isCSV = file.filename.toLowerCase().endsWith(".csv");

  const summaryStrip = (
    totalFound > 0 && (
      <div style={{display:"flex",flexWrap:"wrap",gap:8,margin:"12px 0"}}>
        <span style={{padding:"6px 10px",borderRadius:999,fontWeight:600,background:"#E6FFEA",border:"1px solid #B7F0C0"}}>
          Found {totalFound} PII instance{totalFound>1?"s":""} in preview
        </span>
        {Object.entries(piiCounts).map(([k, v]) => (
          v > 0 && (
            <span key={k} style={{padding:"6px 10px",borderRadius:999,background:"#F1F5FF",border:"1px solid #D6E4FF",fontSize:14}}>
              {k}: {v}
            </span>
          )
        ))}
      </div>
    )
  );

  return (
    <div className="sanitization-preview-page">
      <div className="preview-header">
        <h2 style={{ color: methodInfo.color }}>{methodInfo.title}</h2>
        <p className="method-description">{methodInfo.description}</p>
        <div className="file-info">
          <span className="file-name">📄 {file.filename}</span>
          {previewInfo && (
            <span className="file-stats">
              {isCSV ? (
                <>Preview: {previewInfo.previewLength} rows | Total: {previewInfo.totalLength} rows</>
              ) : (
                <>Preview: {previewInfo.previewLength} chars | Total: {previewInfo.totalLength} chars</>
              )}
            </span>
          )}
        </div>
        {summaryStrip}
      </div>

      {error && <div className="error-banner"><strong>⚠️ Error:</strong> {error}</div>}

      {method !== "approve" && (
        <div className="pii-selection-section">
          <div className="section-header">
            <h3>🎯 Select PII to Sanitize</h3>
            <div className="selection-actions">
              <button onClick={selectAll} className="btn-select-action">Select All</button>
              <button onClick={deselectAll} className="btn-select-action">Clear All</button>
            </div>
          </div>

          <div className="pii-grid">
            {PII_OPTIONS.map(option => {
              const isSelected = selectedPII.includes(option.value);
              // use counts bucketed by UI label
              const foundCount = piiCounts[option.label] || 0;
              return (
                <label key={option.value} className={`pii-card ${isSelected ? 'selected' : ''}`}>
                  <input
                    type="checkbox"
                    value={option.value}
                    checked={isSelected}
                    onChange={() => handleCheckbox(option.value)}
                  />
                  <div className="pii-content">
                    <span className="pii-icon">{option.icon}</span>
                    <span className="pii-label">{option.label}</span>
                    <span className="pii-description">{option.description}</span>
                    {foundCount > 0 && <span className="pii-badge">{foundCount} found</span>}
                  </div>
                </label>
              );
            })}
          </div>

          <div className="process-section">
            <button
              onClick={handleProcess}
              className="btn-process"
              disabled={processing || (selectedPII.length === 0 && method !== "approve")}
            >
              {processing ? "Processing..." : "🔄 Generate Preview"}
            </button>
          </div>
        </div>
      )}

      <div className="preview-container">
        <div className="preview-box original-box">
          <h3>📄 Original Content</h3>
          {isCSV ? renderCSVPreview(originalSnippet) : <pre className="preview-text">{originalSnippet}</pre>}
        </div>

        <div className="preview-arrow"><span>→</span></div>

        <div className="preview-box sanitized-box">
          <h3 style={{ color: methodInfo.color }}>{methodInfo.title.split(' ')[0]} Sanitized Content</h3>
          {isCSV ? (
            (sanitizedSnippet && sanitizedSnippet.length > 0)
              ? renderCSVPreview(sanitizedSnippet)
              : <div className="preview-text sanitized">Click 'Generate Preview' to see results</div>
          ) : (
            <pre className="preview-text sanitized">{sanitizedSnippet || "Click 'Generate Preview' to see results"}</pre>
          )}
        </div>
      </div>

      {totalFound > 0 && (
        <div className="pii-statistics">
          <h4>📊 PII Detection Summary</h4>
          <div className="stats-grid">
            {Object.entries(piiCounts)
              .filter(([,count]) => Number(count) > 0)
              .map(([uiKey, count]) => (
                <div key={uiKey} className="stat-card">
                  <div className="stat-header">
                    <span className="stat-label">{uiKey}</span>
                    <span className="stat-count">{count}</span>
                  </div>
                  {/* samples (up to 3) */}
                  <div className="stat-samples">
                    {sampleValues(piiFound, uiKey, 3).map(val => (
                      <span key={uiKey + val} className="stat-chip" title={val}>{val}</span>
                    ))}
                  </div>
                </div>
            ))}
          </div>
        </div>
      )}

      <div className="action-buttons">
        <button className="btn-back" onClick={() => navigate(-1)} disabled={processing}>← Back</button>
        <button
          className="btn-confirm"
          onClick={handleConfirm}
          disabled={processing || (!sanitizedSnippet && method !== "approve")}
          style={{ backgroundColor: methodInfo.color }}
        >
          {processing ? "Saving..." : "✓ Confirm & Save"}
        </button>
      </div>

      <div className="help-section">
        <h4>ℹ️ How it works:</h4>
        <ul>
          {method === "mask" && (
            <>
              <li>Sensitive data is partially hidden (e.g., j***@example.com)</li>
              <li>Last 4 digits shown for numbers (e.g., ***-1234)</li>
              <li>Useful for internal reviews where context is needed</li>
            </>
          )}
          {method === "tokenize" && (
            <>
              <li>PII is replaced with unique tokens (e.g., [EMAIL_TOKEN_a1b2c3d4])</li>
              <li>Original data can be restored using the token mapping</li>
              <li>Ideal for data processing where re-identification may be needed</li>
            </>
          )}
          {method === "synthetic" && (
            <>
              <li>Real PII is replaced with realistic fake data</li>
              <li>Cannot be reversed - provides complete anonymization</li>
              <li>Best for sharing data externally or testing purposes</li>
            </>
          )}
          {method === "approve" && (
            <>
              <li>Document will be saved without any modifications</li>
              <li>Use only when no PII sanitization is required</li>
            </>
          )}
        </ul>
      </div>
    </div>
  );
};

export default SanitizationPreview;
