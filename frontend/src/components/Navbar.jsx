import React from 'react';

export default function Navbar({ activePage, setActivePage }) {
  return (
    <header className="navbar">
      <div className="nav-brand" role="banner">
        <div className="nav-logo-icon">P</div>
        <span>PULSE // SEO AGENT</span>
        <span className="nav-tag">v2.0</span>
      </div>

      <nav className="nav-center-tabs" aria-label="Main Navigation">
        <button
          className={`nav-tab-btn ${activePage === 'landing' ? 'active' : ''}`}
          onClick={() => setActivePage('landing')}
          type="button"
        >
          Overview
        </button>
        <button
          className={`nav-tab-btn ${activePage === 'console' ? 'active' : ''}`}
          onClick={() => setActivePage('console')}
          type="button"
        >
          Audit Console
        </button>
      </nav>

      <div className="nav-right-actions">
        {/* LangChain Single LLM Status Badge */}
        <div className="llm-selector-wrapper" title="Powered by LangChain (Groq / Gemini)">
          <span className="llm-status-dot" aria-hidden="true"></span>
          <span className="llm-selector-label">Engine:</span>
          <span style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-primary)', padding: '2px 6px' }}>
            LangChain LLM
          </span>
        </div>
      </div>
    </header>
  );
}
