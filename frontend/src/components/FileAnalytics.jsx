import React, { useState } from 'react';
import '../styles/FileAnalytics.css';
import SanitizationPreview from './SanitizationPreview';
import { useNavigate } from 'react-router-dom';

const FileAnalytics = ({ file, onSanitize, onProceedToAI }) => {
  const [selectedMethod, setSelectedMethod] = useState(null);
  const [showPreview, setShowPreview] = useState(false);

  if (!file) return null;

  // Determine risk level category
  const getRiskLevel = (score) => {
    if (score <= 30) return { level: 'Low', color: '#10b981', badge: 'low-risk' };
    if (score <= 60) return { level: 'Medium', color: '#f59e0b', badge: 'medium-risk' };
    return { level: 'High', color: '#ef4444', badge: 'high-risk' };
  };

  const riskInfo = getRiskLevel(file.risk_score);

  // Get appropriate sanitization options based on risk level
  const getSanitizationOptions = () => {
    const baseOptions = [
      {
        id: 'mask',
        label: "Masking",
        description: "Partially obscure PII (e.g., John Doe → J*** D***)",
        icon: "🎭",
        action: () => handleSanitize("mask")
      },
      {
        id: 'tokenize',
        label: "Tokenization",
        description: "Replace with reversible tokens (e.g., John Doe → TOKEN_A1B2)",
        icon: "🔑",
        action: () => handleSanitize("tokenize")
      },
      {
        id: 'synthetic',
        label: "Synthetic Replacement",
        description: "Replace with fake but realistic data (e.g., John Doe → Jane Smith)",
        icon: "🔄",
        action: () => handleSanitize("synthetic")
      }
    ];

    // Low risk: Auto-approve option
    if (file.risk_score <= 30) {
      return [
        {
          id: 'auto',
          label: "Auto-Approve & Process",
          description: "Low risk detected. Proceed with minimal sanitization.",
          icon: "✅",
          action: () => onProceedToAI(file.filename, 'auto')
        },
        ...baseOptions
      ];
    }

    // Medium risk: User choice required
    if (file.risk_score <= 60) {
      return baseOptions;
    }

    // High risk: Admin approval required
    return [
      {
        id: 'admin',
        label: "Request Admin Approval",
        description: "High risk file requires compliance team review before processing.",
        icon: "🚨",
        action: () => handleAdminApproval()
      },
      ...baseOptions.map(opt => ({ ...opt, disabled: true }))
    ];
  };

  const navigate = useNavigate();
  const handleSanitize = (method) => {
    setSelectedMethod(method);
    setShowPreview(true);
    navigate('/sanitize/preview', { state: { file, method } });
  };

  const handleAdminApproval = () => {
    onSanitize(file.filename, "admin_approval");
  };

  const handleConfirmSanitization = () => {
    onSanitize(file.filename, selectedMethod);
    setShowPreview(false);
  };

  const options = getSanitizationOptions();

const groupPIIByType = () => {
  if (!file.detected_pii || file.detected_pii.length === 0) return {};

  const grouped = {};

  file.detected_pii.forEach(item => {
    // If item is a string like "GPE", "ORG", "PERSON"
    if (typeof item === "string") {
      const type = item; 
      if (!grouped[type]) grouped[type] = [];
      grouped[type].push({ value: item });
    }
    // If item is an object like { type: "Email", value: "xyz" }
    else {
      const type = item.type || "Other";
      if (!grouped[type]) grouped[type] = [];
      grouped[type].push(item);
    }
  });

  console.log("Grouped:", grouped);
  return grouped;
};

  const piiByType = groupPIIByType();

  return (
    <div className="file-analytics-container">
      {/* Header Section */}
      <div className="analytics-header">
        <div className="file-info">
          <h2>📄 {file.filename}</h2>
          <span className="file-type-badge">{file.file_type?.toUpperCase()}</span>
        </div>
        <div className={`risk-badge ${riskInfo.badge}`}>
          Risk: {riskInfo.level} ({file.risk_score}%)
        </div>
      </div>

      {/* Risk Visualization */}
      <div className="risk-meter-section">
        <div className="risk-meter">
          <div className="risk-bar">
            <div 
              className="risk-fill" 
              style={{ 
                width: `${file.risk_score}%`, 
                backgroundColor: riskInfo.color 
              }}
            ></div>
          </div>
          <div className="risk-labels">
            <span>0</span>
            <span className="risk-label-center">Risk Score</span>
            <span>100</span>
          </div>
        </div>
      </div>

      {/* PII Detection Results */}
      <div className="pii-detection-section">
        <h3>🔍 Detected PII</h3>
        {Object.keys(piiByType).length > 0 ? (
          <div className="pii-categories">
            {Object.entries(piiByType).map(([type, items]) => (
              <div key={type} className="pii-category">
                <div className="pii-category-header">
                  <span className="pii-type">{type}</span>
                  <span className="pii-count">{items.length} found</span>
                </div>
                <div className="pii-items">
                  {items.slice(0, 3).map((item, idx) => (
                    <span key={idx} className="pii-item">
                      {item.text || item.value}
                    </span>
                  ))}
                  {items.length > 3 && (
                    <span className="pii-more">+{items.length - 3} more</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="no-pii">
            <span className="no-pii-icon">✅</span>
            <p>No sensitive information detected</p>
          </div>
        )}
      </div>

      {/* Recommendations Section */}
      {file.recommendations && file.recommendations.length > 0 && (
        <div className="recommendations-section">
          <h3>💡 Recommendations</h3>
          <ul className="recommendations-list">
            {file.recommendations.map((rec, idx) => (
              <li key={idx}>
                <span className="rec-icon">→</span>
                {rec}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Workflow Decision Section */}
      <div className="workflow-section">
        <h3>⚙️ Next Steps</h3>
        <div className="workflow-description">
          {file.risk_score <= 30 && (
            <p className="workflow-info low">
              ✅ <strong>Low Risk:</strong> This file can be auto-approved for processing. 
              Light sanitization recommended but optional.
            </p>
          )}
          {file.risk_score > 30 && file.risk_score <= 60 && (
            <p className="workflow-info medium">
              ⚠️ <strong>Medium Risk:</strong> Review required. Choose a sanitization method 
              before proceeding to AI processing.
            </p>
          )}
          {file.risk_score > 60 && (
            <p className="workflow-info high">
              🚨 <strong>High Risk:</strong> Admin approval mandatory. This file contains 
              sensitive information that requires compliance team review.
            </p>
          )}
        </div>

        {/* Sanitization Options */}
        <div className="sanitization-options">
          {options.map((option) => (
            <div 
              key={option.id} 
              className={`option-card ${option.disabled ? 'disabled' : ''} ${selectedMethod === option.id ? 'selected' : ''}`}
            >
              <div className="option-icon">{option.icon}</div>
              <div className="option-content">
                <h4>{option.label}</h4>
                <p>{option.description}</p>
              </div>
              <button 
                className="option-button"
                onClick={option.action}
                disabled={option.disabled}
              >
                {option.id === 'auto' ? 'Process Now' : 'Select'}
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* Preview Modal */}
      {showPreview && (
        <div className="preview-modal">
          <div className="modal-content">
            <h3>Preview Sanitization</h3>
            <div className="preview-comparison">
              <div className="preview-column">
                <h4>Original</h4>
                <div className="preview-text">
                  {/* Show original content preview */}
                  <p className="preview-sample">
                    John Doe<br />
                    john.doe@email.com<br />
                    555-1234
                  </p>
                </div>
              </div>
              <div className="preview-arrow">→</div>
              <div className="preview-column">
                <h4>Sanitized ({selectedMethod})</h4>
                <div className="preview-text">
                  {selectedMethod === 'mask' && (
                    <p className="preview-sample">
                      J*** D***<br />
                      j***.d***@email.com<br />
                      555-****
                    </p>
                  )}
                  {selectedMethod === 'tokenize' && (
                    <p className="preview-sample">
                      TOKEN_A1B2<br />
                      TOKEN_C3D4<br />
                      TOKEN_E5F6
                    </p>
                  )}
                  {selectedMethod === 'synthetic' && (
                    <p className="preview-sample">
                      Jane Smith<br />
                      jane.smith@example.com<br />
                      555-9876
                    </p>
                  )}
                </div>
              </div>
            </div>
            <div className="modal-actions">
              <button className="btn-cancel" onClick={() => setShowPreview(false)}>
                Cancel
              </button>
              <button className="btn-confirm" onClick={handleConfirmSanitization}>
                Confirm & Proceed to AI
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default FileAnalytics;