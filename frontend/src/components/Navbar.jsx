import React from 'react';

export default function Navbar({ activePage, setActivePage, selectedModel, setSelectedModel }) {
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
        {/* LLM Model Switching Dropdown in Navbar */}
        <div className="llm-selector-wrapper" title="Switch AI Provider / Execution Engine">
          <span className="llm-status-dot" aria-hidden="true"></span>
          <span className="llm-selector-label">LLM:</span>
          <select
            className="llm-dropdown"
            value={selectedModel}
            onChange={(e) => setSelectedModel(e.target.value)}
            aria-label="Select AI Model"
          >
            <option value="auto">Auto (Smart Detect)</option>
            <option value="gemini">Gemini 1.5 Flash</option>
            <option value="groq">Groq Llama 3.3 70B</option>
            <option value="openai">OpenAI GPT-4o-mini</option>
            <option value="none">Deterministic (No AI)</option>
          </select>
        </div>
      </div>
    </header>
  );
}
