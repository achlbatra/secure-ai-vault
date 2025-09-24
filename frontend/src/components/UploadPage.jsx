import React, { useEffect, useState } from 'react';
import upload from '../assets/upload.svg';
import '../styles/Upload.css';
import axios from 'axios';

const UploadPage = () => {
  const [uploading, setUploading] = useState(false);
  const [uploadSuccess, setUploadSuccess] = useState(false);
  const [uploadedFileName, setUploadedFileName] = useState('');
  const [error, setError] = useState(null);
  const [uploads, setUploads] = useState([]);

    useEffect(() => {
    axios
      .get("http://localhost:8000/files/list-recent-uploads", {
        headers: {
          Authorization: `Bearer ${localStorage.getItem("token")}`,
        },
      })
      .then((res) => setUploads(res.data))
      .catch((err) => console.error(err));
  }, []);

  const handleFileChange = (e) => {
    const files = e.target.files;
    if (!files.length) return;

    const formData = new FormData();
    formData.append("file", files[0]);

    setUploading(true);
    setError(null);

    fetch("http://localhost:8000/files/upload", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${localStorage.getItem("token")}`,
      },
      body: formData,
    })
      .then((response) => {
        if (!response.ok) throw new Error("Upload failed");
        return response.json();
      })
      .then((data) => {
        setUploading(false);
        setUploadSuccess(true);
        setUploadedFileName(data.filename);

        // ✅ Refetch recent uploads from backend (so DB stays in sync)
        axios
          .get("http://localhost:8000/files/recent", {
            headers: {
              Authorization: `Bearer ${localStorage.getItem("token")}`,
            },
          })
          .then((res) => setUploads(res.data));

        setTimeout(() => setUploadSuccess(false), 5000);
      })
      .catch((error) => {
        setUploading(false);
        setError(error.message);
        console.error("Error:", error);
      });
    }

  const handleSubmit = (e) => {
    e.preventDefault();
    document.getElementById("fileInput").click();
  };

  return (
    <div className="upload-page">
      <div className="upload-header">
        <h2>Upload Documents</h2>
        <p>
          Securely upload your documents for AI-powered analysis with automatic
          PII detection and compliance protection.
        </p>
      </div>

      <div className="upload-container">
        <form className="upload-form" onSubmit={(e) => e.preventDefault()}>
          <div className="upload-image">
            <img src={upload} alt="Upload" />
          </div>
          <div className="upload-instructions">
            <h2>Drag and drop files here</h2>
            <p>or click to select files</p>
          </div>
          <div className="separator">
            <input
              type="file"
              id="fileInput"
              className="hidden-file-input"
              onChange={handleFileChange}
            />

            <label htmlFor="fileInput" className="custom-upload-btn">
              Choose File
            </label>
            <small>Max size: 25 MB</small>
            {uploading && (
              <div className="uploading-status">
                ⏳ Uploading... Please wait.
              </div>

            )}
            {uploadSuccess && (
              <div className="upload-success">✅ {uploadedFileName} uploaded successfully!</div>
            )}
            {/* <button type="submit" className="upload-button">
              Upload
            </button> */}
          </div>
        </form>

      
        {error && <div className="error-message">❌ {error}</div>}

        <div className="supported-formats">
          <div className="format-card">
              <div className="format-icon">📄</div>
              <div className="format-name">Text Files (.txt)</div>
              <div className="format-description">Plain text documents, notes, reports</div>
          </div>
          <div className="format-card">
              <div className="format-icon">📊</div>
              <div className="format-name">CSV Files (.csv)</div>
              <div className="format-description">Spreadsheet data, customer lists</div>
          </div>
          <div className="format-card">
              <div className="format-icon">🔗</div>
              <div className="format-name">JSON Files (.json)</div>
              <div className="format-description">API data, structured information</div>
          </div>
          <div className="format-card">
              <div className="format-icon">📝</div>
              <div className="format-name">Word Docs (.docx)</div>
              <div className="format-description">Documents, resumes, reports</div>
          </div>
        </div>
        </div>
      <div className="guidelines-section">
            <h3 className="guidelines-title">
                🛡️ Security Guidelines
            </h3>
            <ul className="guidelines-list">
                <div className="guideline-item">
                    <div className="guideline-icon">✓</div>
                    <div>All files are scanned for PII (Personal Identifiable Information) automatically</div>
                </div>
                <div className="guideline-item">
                    <div className="guideline-icon">✓</div>
                    <div>Risk scores are calculated based on detected sensitive data</div>
                </div>
                <div className="guideline-item">
                    <div className="guideline-icon">✓</div>
                    <div>High-risk documents require manual approval before AI processing</div>
                </div>
                <div className="guideline-item">
                    <div className="guideline-icon">✓</div>
                    <div>All activities are logged for compliance and audit purposes</div>
                </div>
                <div className="guideline-item">
                    <div className="guideline-icon">✓</div>
                    <div>Data is sanitized before being sent to AI services</div>
                </div>
            </ul>
        </div>
        <div className="recent-uploads">
          <h3 className="section-title">Recent Uploads</h3>
          {uploads.length === 0 ? (
            <div className="empty-state">
              <div className="empty-icon">📂</div>
              <h4 className="empty-title">No files uploaded yet</h4>
              <p className="empty-description">
                Your uploaded files will appear here.
              </p>
            </div>
          ) : (
            <ul className="uploaded-list">
              {uploads.map((file) => (
                <li key={file.id}>
                  <strong>{file.file_name}</strong> <br />
                  <small>
                    Uploaded at:{" "}
                    {new Date(file.created_at).toLocaleString()}
                  </small>
                </li>
              ))}
            </ul>
          )}          
         </div>
      </div>
  );
};

export default UploadPage;
