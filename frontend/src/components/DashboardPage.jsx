import React from 'react';
import { useNavigate } from 'react-router-dom';
import '../styles/DashboardPage.css';

const DashboardPage = () => { 
  const navigate = useNavigate();

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
      <div class="stat-card">
          <div class="stat-icon">📊</div>
          <div class="stat-value">--</div>
          <div class="stat-label">Documents Processed</div>
          <div class="stat-subtext">Will update after uploads</div>
      </div>
      <div class="stat-card">
          <div class="stat-icon">🛡️</div>
          <div class="stat-value">--</div>
          <div class="stat-label">Security Score</div>
          <div class="stat-subtext">System health rating</div>
      </div>
      <div class="stat-card">
          <div class="stat-icon">⚠️</div>
          <div class="stat-value">--</div>
          <div class="stat-label">PII Items Protected</div>
          <div class="stat-subtext">Sensitive data secured</div>
      </div>
      <div class="stat-card">
          <div class="stat-icon">⏳</div>
          <div class="stat-value">--</div>
          <div class="stat-label">Pending Reviews</div>
          <div class="stat-subtext">Awaiting approval</div>
      </div>
    </section>

    <section className='getting-started-grid'>
      <h2 class="section-title">Get Started in 3 Simple Steps</h2>
      <div className="getting-started">
          <div class="step-card">
              <div class="step-number">1</div>
              <h3 class="step-title">Upload Document</h3>
              <p class="step-description">Upload any .txt, .csv, .json, or .docx file. Our system supports various document formats for maximum flexibility.</p>
              <a href="#" class="step-button">Choose Files</a>
          </div>
          <div class="step-card">
              <div class="step-number">2</div>
              <h3 class="step-title">Review Security Scan</h3>
              <p class="step-description">View detected PII, risk assessment, and recommended sanitization options before AI processing.</p>
              <a href="#" class="step-button">Learn More</a>
          </div>
          <div class="step-card">
              <div class="step-number">3</div>
              <h3 class="step-title">Process with AI</h3>
              <p class="step-description">Securely send sanitized data to AI services for analysis while maintaining complete audit trails.</p>
              <a href="#" class="step-button">View Demo</a>
          </div>
      </div>
    </section>

    <section className='features'>
      <h2 class="section-title">Key Features</h2>
      <div class="features-grid">
          <div class="feature-card">
              <div class="feature-icon">🔍</div>
              <h3 class="feature-title">PII Detection</h3>
              <p class="feature-description">Automatically identify names, emails, phone numbers, SSNs, and other sensitive data across all document types.</p>
          </div>
          <div class="feature-card">
              <div class="feature-icon">⚡</div>
              <h3 class="feature-title">Risk Assessment</h3>
              <p class="feature-description">Get instant risk scores (0-100) based on detected sensitive information and document context.</p>
          </div>
          <div class="feature-card">
              <div class="feature-icon">🛡️</div>
              <h3 class="feature-title">Smart Sanitization</h3>
              <p class="feature-description">Multiple sanitization options including masking, tokenization, and synthetic replacement.</p>
          </div>
          <div class="feature-card">
              <div class="feature-icon">🤖</div>
              <h3 class="feature-title">AI Integration</h3>
              <p class="feature-description">Secure proxy to OpenAI and other AI services with complete data governance.</p>
          </div>
          <div class="feature-card">
              <div class="feature-icon">📋</div>
              <h3 class="feature-title">Audit Trails</h3>
              <p class="feature-description">Complete logging of all processing activities for compliance and accountability.</p>
          </div>
      </div>
    </section>
    </div>  
  );
}

export default DashboardPage;