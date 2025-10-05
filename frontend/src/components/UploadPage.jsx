import React, { useEffect, useState } from 'react';
import upload from '../assets/upload.svg';
import '../styles/Upload.css';
import axios from 'axios';
import FileAnalytics from './FileAnalytics';

const UploadPage = () => {
  const [uploading, setUploading] = useState(false);
  const [uploadSuccess, setUploadSuccess] = useState(false);
  const [uploadedFileName, setUploadedFileName] = useState('');
  const [error, setError] = useState(null);
  const [uploads, setUploads] = useState([]);
  const [latestFile, setLatestFile] = useState(null);
  const [dragActive, setDragActive] = useState(false);
  const [processingProgress, setProcessingProgress] = useState(0);

  const fetchUploads = async () => {
    try {
      const res = await axios.get("http://localhost:8000/files/analytics", {
        headers: { Authorization: `Bearer ${localStorage.getItem("token")}` },
      });

      const normalized = res.data
        .map(d => ({
          ...d,
          detected_pii: typeof d.detected_pii === "string" ? JSON.parse(d.detected_pii || "[]") : d.detected_pii,
          recommendations: d.recommendations || []
        }))
        .sort((a, b) => new Date(b.uploaded_at || b.created_at) - new Date(a.uploaded_at || a.created_at));

      const recent = normalized.slice(0, 5);
      setUploads(recent);
      return recent;
    } catch (err) {
      console.error(err);
      return [];
    }
  };

  useEffect(() => {
    fetchUploads().then(recent => {
      if (recent.length) setLatestFile(recent[0]);
    });
  }, []);

  const handleFileChange = async (e) => {
    const files = e.target.files;
    if (!files.length) return;

    await uploadFile(files[0]);
  };

  const uploadFile = async (file) => {
    const formData = new FormData();
    formData.append("file", file);

    setUploading(true);
    setError(null);
    setProcessingProgress(10);

    try {
      setTimeout(() => setProcessingProgress(30), 500);
      
      const res = await fetch("http://localhost:8000/files/upload", {
        method: "POST",
        headers: { Authorization: `Bearer ${localStorage.getItem("token")}` },
        body: formData,
      });

      setProcessingProgress(70);

      if (!res.ok) throw new Error("Upload failed");
      const data = await res.json();

      setProcessingProgress(90);
      setUploading(false);
      setUploadSuccess(true);
      setUploadedFileName(data.filename);

      const recent = await fetchUploads();
      const uploaded = recent.find(f => f.filename === data.filename);
      if (uploaded) setLatestFile(uploaded);
      setUploads(recent);
      setProcessingProgress(100);
      setTimeout(() => {
        setUploadSuccess(false);
        setProcessingProgress(0);
      }, 5000);
    } catch (err) {
      setUploading(false);
      setError(err.message);
      setProcessingProgress(0);
      console.error(err);
    }
  };

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      uploadFile(e.dataTransfer.files[0]);
    }
  };

  const handleSanitize = async (filename, method) => {
    try {
      await axios.post("http://localhost:8000/files/sanitize", { filename, method }, {
        headers: { Authorization: `Bearer ${localStorage.getItem("token")}` },
      });
      const recent = await fetchUploads();
      const updated = recent.find(f => f.filename === filename);
      if (updated) setLatestFile(updated);
    } catch (err) {
      console.error(err);
    }
  };

  const handleProceedToAI = (filename, mode = 'normal') => {
    window.location.href = `/ai-processing?file=${filename}&mode=${mode}`;
  };

  const getRiskBadgeClass = (score) => {
    if (score <= 30) return 'risk-low';
    if (score <= 60) return 'risk-medium';
    return 'risk-high';
  };

  const getStatusBadgeClass = (status) => {
    const statusMap = {
      'processed': 'status-processed',
      'pending': 'status-pending',
      'rejected': 'status-rejected',
      'approved': 'status-approved'
    };
    return statusMap[status?.toLowerCase()] || 'status-default';
  };

  return (
    <div className="upload-page">
      <div className="upload-header">
        <h2>Upload Documents</h2>
        <p>Upload your files for secure AI analysis with automatic PII detection and compliance protection.</p>
      </div>

      <div className="upload-container">
        <form 
          className={`upload-form ${dragActive ? 'drag-active' : ''}`}
          onSubmit={e => e.preventDefault()}
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
        >
          <div className="upload-image">
            <img src={upload} alt="Upload" />
          </div>
          <div className="upload-instructions">
            <h2>Drag and drop files here</h2>
            <p>or click to select files</p>
          </div>
          <input 
            type="file" 
            id="fileInput" 
            className="hidden-file-input" 
            onChange={handleFileChange}
            accept=".txt,.csv,.json,.docx"
          />
          <label htmlFor="fileInput" className="custom-upload-btn">
            Choose File
          </label>
          <div className="file-format-info">
            <small>Supported formats: TXT, CSV, JSON, DOCX • Max size: 25 MB</small>
          </div>

          {uploading && (
            <div className="processing-status">
              <div className="processing-text">⏳ Processing...</div>
              <div className="progress-bar">
                <div className="progress-fill" style={{ width: `${processingProgress}%` }}></div>
              </div>
              <div className="progress-steps">
                <span className={processingProgress >= 10 ? 'active' : ''}>Uploading</span>
                <span className={processingProgress >= 30 ? 'active' : ''}>Extracting</span>
                <span className={processingProgress >= 70 ? 'active' : ''}>Scanning PII</span>
                <span className={processingProgress >= 90 ? 'active' : ''}>Analyzing Risk</span>
              </div>
            </div>
          )}

          {uploadSuccess && (
            <div className="upload-success">
              <span className="success-icon">✅</span>
              <span className="success-text">{uploadedFileName} uploaded successfully!</span>
            </div>
          )}

          {error && (
            <div className="error-message">
              <span className="error-icon">❌</span>
              <span className="error-text">{error}</span>
            </div>
          )}
        </form>

        <div className="supported-formats">
          <div className="format-card">
            <div className="format-icon">📄</div>
            <div className="format-name">Text Files</div>
            <div className="format-description">.txt</div>
          </div>
          <div className="format-card">
            <div className="format-icon">📊</div>
            <div className="format-name">CSV Files</div>
            <div className="format-description">.csv</div>
          </div>
          <div className="format-card">
            <div className="format-icon">🔗</div>
            <div className="format-name">JSON Files</div>
            <div className="format-description">.json</div>
          </div>
          <div className="format-card">
            <div className="format-icon">📝</div>
            <div className="format-name">Word Docs</div>
            <div className="format-description">.docx</div>
          </div>
        </div>
      </div>

      <div className="guidelines-section">
        <h3 className="guidelines-title">
          🛡️ Security Guidelines
        </h3>
        <ul className="guidelines-list">
          <li className="guideline-item">
            <div className="guideline-icon">✓</div>
            <div>All files are scanned for PII (Personal Identifiable Information) automatically</div>
          </li>
          <li className="guideline-item">
            <div className="guideline-icon">✓</div>
            <div>Risk scores are calculated based on detected sensitive data</div>
          </li>
          <li className="guideline-item">
            <div className="guideline-icon">✓</div>
            <div>High-risk documents require manual approval before AI processing</div>
          </li>
          <li className="guideline-item">
            <div className="guideline-icon">✓</div>
            <div>All activities are logged for compliance and audit purposes</div>
          </li>
        </ul>
      </div>

      {latestFile && (
        <div className="latest-file-analytics">
          <FileAnalytics
            file={latestFile}
            onSanitize={handleSanitize}
            onProceedToAI={handleProceedToAI}
          />
        </div>
      )}

      <div className="recent-uploads">
        <h3>Recent Uploads</h3>
        {uploads.length === 0 ? (
          <div className="empty-state">
            <div className="empty-icon">📂</div>
            <h4 className="empty-title">No files uploaded yet</h4>
            <p className="empty-description">Your uploaded files will appear here</p>
          </div>
        ) : (
          <div className="table-container">
            <table className="uploads-table">
              <thead>
                <tr>
                  <th>Filename</th>
                  <th>File Type</th>
                  <th>Uploaded At</th>
                  <th>Risk Score</th>
                  <th>Status</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {uploads.map(file => (
                  <tr key={file.filename} className="table-row">
                    <td className="filename-cell">
                      <span className="file-icon">📄</span>
                      {file.filename}
                    </td>
                    <td>
                      <span className="file-type-badge">{file.file_type?.toUpperCase() || 'N/A'}</span>
                    </td>
                    <td className="date-cell">
                      {new Date(file.uploaded_at || file.created_at).toLocaleDateString()} <br/>
                      <small>{new Date(file.uploaded_at || file.created_at).toLocaleTimeString()}</small>
                    </td>
                    <td>
                      <span className={`risk-badge ${getRiskBadgeClass(file.risk_score)}`}>
                        {file.risk_score != null ? `${file.risk_score}%` : "-"}
                      </span>
                    </td>
                    <td>
                      <span className={`status-badge ${getStatusBadgeClass(file.status)}`}>
                        {file.status || 'Unknown'}
                      </span>
                    </td>
                    <td>
                      <button 
                        className="view-btn" 
                        onClick={() => setLatestFile(file)}
                      >
                        View Analysis
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};

export default UploadPage;