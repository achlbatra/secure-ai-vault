import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useState, useEffect } from 'react';
import axios from 'axios';
import '../styles/DashboardPage.css';

const DashboardPage = () => { 
  const navigate = useNavigate();

   const [stats, setStats] = useState({
    documentsProcessed: 0,
    securityScore: 0,
    piiItemsProtected: 0,
    pendingReviews: 0,
  });

  const fetchDashboardStats = async () => {
    try {
      const token = localStorage.getItem("token");
      const response = await axios.get("http://localhost:8000/dashboard/stats", {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      setStats(response.data);
    } catch (error) {
      console.error("Error fetching dashboard data:", error);
    }
  };

  useEffect(() => {
    fetchDashboardStats();
    const interval = setInterval(fetchDashboardStats, 5000);
    return () => clearInterval(interval);
  }, []);

  const handlClickUpload = () => {
    // Logic to navigate to the upload page or open upload modal
    navigate('/upload');
    console.log("Navigate to upload page");
  };

  return (
    <div className='dashboard-page'>
    <div className="dashboard-intro">
      <h2>Welcome to SecureVault!</h2>
      {/* <p>Your secure AI processing platform is here. Start by uploading your first document to experience AI-powered analysis with complete privacy protection.</p>
      <button onClick={handlClickUpload}>Upload Document</button> */}
    </div>
    <div className="dashboard-about">
      <h3>About the platform</h3>
      <p>SecureAI Vault is an intelligent security platform that sits between your sensitive documents and AI services. It automatically detects personal identifiable information (PII), assigns risk scores, sanitizes data, and maintains complete audit trails—enabling organizations to leverage AI analytics while staying compliant with GDPR, HIPAA, and other regulations.
      </p>
      <p><b><i>Start by uploading your first document to experience AI-powered analysis with complete privacy protection.</i></b></p>
      <button className='get-started' onClick={handlClickUpload}>Get Started</button>
    </div>
    
    <section className="quick-stats">
  <div className="stat-card">
    <div className="stat-icon">📊</div>
    <div className="stat-value">{stats.documentsProcessed}</div>
    <div className="stat-label">Documents Processed</div>
    <div className="stat-subtext">
      {stats.documentsProcessed > 0
        ? "Documents successfully processed"
        : "Will update after uploads"}
    </div>
  </div>

  <div className="stat-card">
    <div className="stat-icon">🛡️</div>
    <div className="stat-value">{stats.securityScore}</div>
    <div className="stat-label">Security Score</div>
    <div className="stat-subtext">
      {stats.securityScore > 0
        ? "System health rating"
        : "Awaiting initial scan"}
    </div>
  </div>

  <div className="stat-card">
    <div className="stat-icon">⚠️</div>
    <div className="stat-value">{stats.piiItemsProtected}</div>
    <div className="stat-label">PII Items Protected</div>
    <div className="stat-subtext">
      {stats.piiItemsProtected > 0
        ? "Sensitive data secured"
        : "No PII detected yet"}
    </div>
  </div>

  <div className="stat-card">
    <div className="stat-icon">⏳</div>
    <div className="stat-value">{stats.pendingReviews}</div>
    <div className="stat-label">Pending Reviews</div>
    <div className="stat-subtext">
      {stats.pendingReviews > 0
        ? "Awaiting review actions"
        : "All clear for now"}
    </div>
  </div>
</section>

    <section className='getting-started-grid'>
      <h2 className="section-title">Get Started in 3 Simple Steps</h2>
      <div className="getting-started">
          <div className="step-card">
              <div className="step-number">1</div>
              <h3 className="step-title">Upload Document</h3>
              <p className="step-description">Upload any .txt, .csv, .json, or .docx file. Our system supports various document formats for maximum flexibility.</p>
              <a href="#" className="step-button">Choose Files</a>
          </div>
          <div className="step-card">
              <div className="step-number">2</div>
              <h3 className="step-title">Review Security Scan</h3>
              <p className="step-description">View detected PII, risk assessment, and recommended sanitization options before AI processing.</p>
              <a href="#" className="step-button">Learn More</a>
          </div>
          <div className="step-card">
              <div className="step-number">3</div>
              <h3 className="step-title">Process with AI</h3>
              <p className="step-description">Securely send sanitized data to AI services for analysis while maintaining complete audit trails.</p>
              <a href="#" className="step-button">View Demo</a>
          </div>
      </div>
    </section>

    <section className='features'>
      <h2 className="section-title">Key Features</h2>
      <div className="features-grid">
          <div className="feature-card">
              <div className="feature-icon">🔍</div>
              <h3 className="feature-title">PII Detection</h3>
              <p className="feature-description">Automatically identify names, emails, phone numbers, SSNs, and other sensitive data across all document types.</p>
          </div>
          <div className="feature-card">
              <div className="feature-icon">⚡</div>
              <h3 className="feature-title">Risk Assessment</h3>
              <p className="feature-description">Get instant risk scores (0-100) based on detected sensitive information and document context.</p>
          </div>
          <div className="feature-card">
              <div className="feature-icon">🛡️</div>
              <h3 className="feature-title">Smart Sanitization</h3>
              <p className="feature-description">Multiple sanitization options including masking, tokenization, and synthetic replacement.</p>
          </div>
          <div className="feature-card">
              <div className="feature-icon">🤖</div>
              <h3 className="feature-title">AI Integration</h3>
              <p className="feature-description">Secure proxy to OpenAI and other AI services with complete data governance.</p>
          </div>
          <div className="feature-card">
              <div className="feature-icon">📋</div>
              <h3 className="feature-title">Audit Trails</h3>
              <p className="feature-description">Complete logging of all processing activities for compliance and accountability.</p>
          </div>
      </div>
    </section>
    </div>  
  );
}

export default DashboardPage;