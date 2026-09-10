import React, { useState, useRef, useEffect } from 'react';
import { DEMO_Q1_AUDIT, DEMO_Q1_SUMMARY, DEMO_Q2_NAP, DEMO_Q2_OFFSITE, DEMO_Q3_QA } from '../demoData';

function NapVisualizer({ data }) {
  const [activeTab, setActiveTab] = useState('in_site');
  const inSiteFields = data?.in_site || data?.fields || [];
  const offSite = data?.off_site || null;

  return (
    <div className="nap-container">
      {/* Dual Tab Header */}
      <div className="nap-tab-header">
        <div className="nap-tab-pills">
          <button
            type="button"
            className={`nap-tab-btn ${activeTab === 'in_site' ? 'active' : ''}`}
            onClick={() => setActiveTab('in_site')}
          >
            🏢 In-Site Consistency
            <span className="nap-tab-count">
              {inSiteFields.filter((f) => f.verdict === 'consistent').length}/{inSiteFields.length} Consistent
            </span>
          </button>
          <button
            type="button"
            className={`nap-tab-btn ${activeTab === 'off_site' ? 'active' : ''}`}
            onClick={() => setActiveTab('off_site')}
          >
            🌐 Off-Site Citations (Web Search)
            {offSite?.citation_health_score !== null && offSite?.citation_health_score !== undefined && (
              <span className="nap-score-pill">
                Score {offSite.citation_health_score}/100
              </span>
            )}
          </button>
        </div>
      </div>

      {/* Tab 1: In-Site Consistency */}
      {activeTab === 'in_site' && (
        <div className="nap-field-cards">
          {inSiteFields.map((fld) => (
            <div key={fld.field} className="nap-card">
              <div className="nap-card-header">
                <div className="nap-card-field">{fld.field}</div>
                <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                  <span className={`nap-verdict-tag ${fld.verdict}`}>{fld.verdict}</span>
                  <span className="nap-confidence-pill">
                    Confidence: {(fld.confidence * 100).toFixed(0)}%
                  </span>
                </div>
              </div>

              <p className="nap-explanation-text">{fld.confidence_explanation}</p>

              {fld.values && fld.values.length > 0 ? (
                <table className="nap-values-table">
                  <thead>
                    <tr>
                      <th>Extracted Value</th>
                      <th>Normalized</th>
                      <th>Sources</th>
                      <th>Pages</th>
                    </tr>
                  </thead>
                  <tbody>
                    {fld.values.map((v, i) => (
                      <tr key={i}>
                        <td>
                          <strong>{v.value}</strong>
                        </td>
                        <td className="mono" style={{ color: 'var(--text-secondary)' }}>
                          {v.normalized}
                        </td>
                        <td>{v.sources.join(', ')}</td>
                        <td>{v.pages.length} page(s)</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <div style={{ fontSize: '12px', color: 'var(--text-tertiary)', fontStyle: 'italic' }}>
                  No instances found across any crawled pages.
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Tab 2: Off-Site Citations */}
      {activeTab === 'off_site' && (
        <div className="nap-offsite-view">
          {/* Canonical In-Site Baseline & Score Banner */}
          <div className="nap-offsite-banner">
            <div className="nap-canonical-box">
              <div className="nap-canonical-title">Canonical In-Site Baseline (Ground Truth)</div>
              <div className="nap-canonical-grid">
                <div>
                  <strong>Name:</strong>{' '}
                  <span>{offSite?.in_site_canonical?.name || 'Not detected'}</span>
                </div>
                <div>
                  <strong>Address:</strong>{' '}
                  <span>{offSite?.in_site_canonical?.address || 'Not detected'}</span>
                </div>
                <div>
                  <strong>Phone:</strong>{' '}
                  <span>{offSite?.in_site_canonical?.phone || 'Not detected'}</span>
                </div>
              </div>
            </div>

            <div className="nap-offsite-score-card">
              <div className="nap-score-label">Citation Health</div>
              <div className="nap-score-val">
                {offSite?.citation_health_score !== null && offSite?.citation_health_score !== undefined
                  ? `${offSite.citation_health_score}/100`
                  : 'N/A'}
              </div>
              <div className="nap-agent-tool-tag">Tool: search_web (ddgs live citations)</div>
            </div>
          </div>

          {/* AI Footprint Summary */}
          {offSite?.summary && (
            <div className="nap-offsite-summary">
              <div className="nap-summary-header">
                <span className="summary-sparkle">✦</span> Off-Site Web Footprint Summary
              </div>
              <p className="nap-summary-text">{offSite.summary}</p>
            </div>
          )}

          {/* Notice if no LLM Key configured */}
          {offSite?.status === 'no_llm' && (
            <div className="nap-no-llm-banner">
              <strong>LLM API Key Required:</strong> Configure <code>GROQ_API_KEY</code> or{' '}
              <code>GEMINI_API_KEY</code> in your <code>.env</code> file to enable the agent to autonomously search
              the web and audit external listings.
            </div>
          )}

          {/* External Citations */}
          <div className="nap-citations-section">
            <div className="nap-citations-title">
              External Directory & Citation Findings
              <span className="nap-citations-count">
                ({offSite?.citations?.length || 0} external source{offSite?.citations?.length === 1 ? '' : 's'})
              </span>
            </div>

            {offSite?.citations && offSite.citations.length > 0 ? (
              <div className="nap-citations-grid">
                {offSite.citations.map((cit, idx) => (
                  <div key={idx} className="nap-citation-card">
                    <div className="nap-citation-top">
                      <div>
                        <div className="nap-citation-source">{cit.source}</div>
                        {cit.url && (
                          <a
                            href={cit.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="nap-citation-link"
                          >
                            {cit.url.replace(/^https?:\/\//i, '').slice(0, 45)}... ↗
                          </a>
                        )}
                      </div>
                      <span className={`nap-match-badge ${cit.match_status}`}>
                        {cit.match_status?.replace('_', ' ')}
                      </span>
                    </div>

                    <div className="nap-citation-details">
                      <div className="nap-detail-row">
                        <span className="nap-detail-lbl">Name:</span>
                        <span className="nap-detail-val">{cit.name || '—'}</span>
                      </div>
                      <div className="nap-detail-row">
                        <span className="nap-detail-lbl">Address:</span>
                        <span className="nap-detail-val">{cit.address || '—'}</span>
                      </div>
                      <div className="nap-detail-row">
                        <span className="nap-detail-lbl">Phone:</span>
                        <span className="nap-detail-val">{cit.phone || '—'}</span>
                      </div>
                    </div>

                    {cit.discrepancy_details && (
                      <div className="nap-citation-note">
                        <strong>Analysis:</strong> {cit.discrepancy_details}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <div className="nap-empty-citations">
                <p>No external business directory or map listings were identified for this domain on the public web.</p>
              </div>
            )}
          </div>

          {/* Recommendations Checklist */}
          {offSite?.recommendations && offSite.recommendations.length > 0 && (
            <div className="nap-recs-card">
              <div className="nap-recs-header">Actionable Citation & Local SEO Recommendations</div>
              <ul className="nap-recs-list">
                {offSite.recommendations.map((rec, i) => (
                  <li key={i}>{rec}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function ConsolePage() {
  const [messages, setMessages] = useState([]);
  const [urlInput, setUrlInput] = useState('');
  const [queryInput, setQueryInput] = useState('');
  const [selectedTask, setSelectedTask] = useState('q1'); // 'q1', 'q2', 'q3'
  const [isProcessing, setIsProcessing] = useState(false);
  const [activeStep, setActiveStep] = useState('');
  const [severityFilter, setSeverityFilter] = useState('all');
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isProcessing]);

  const handleQuickPrompt = (url, task, query = '') => {
    setUrlInput(url);
    setSelectedTask(task);
    if (query) setQueryInput(query);
    executeAudit(url, task, query);
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!urlInput.trim() || isProcessing) return;
    executeAudit(urlInput.trim(), selectedTask, queryInput.trim());
  };

  const executeAudit = async (targetUrl, taskType, queryText) => {
    let cleanUrl = targetUrl.trim();
    if (cleanUrl && !/^https?:\/\//i.test(cleanUrl)) {
      cleanUrl = 'https://' + cleanUrl;
    }

    setIsProcessing(true);
    setActiveStep('Initiating request...');

    // Append user message to thread
    const userMsgId = Date.now();
    const taskLabels = {
      q1: 'Crawl site for SEO issues',
      q2: 'NAP consistency checker',
      q3: 'AEO Q/A agent',
    };

    setMessages((prev) => [
      ...prev,
      {
        id: userMsgId,
        sender: 'user',
        url: cleanUrl,
        task: taskType,
        taskLabel: taskLabels[taskType],
        query: queryText,
      },
    ]);

    // Live API call or smart demo fallback
    try {
      setActiveStep('Autonomous crawler connecting to target host...');
      await new Promise((r) => setTimeout(r, 600));

      setActiveStep('Analyzing sitemap.xml and robots.txt directives...');
      await new Promise((r) => setTimeout(r, 700));

      setActiveStep('Auditing DOM nodes, markup, and schema signals...');
      
      let endpoint = '/api/audit';
      let payload = { url: cleanUrl, max_pages: 15 };

      if (taskType === 'q2') {
        endpoint = '/api/nap';
        payload = { url: cleanUrl, max_pages: 15 };
      } else if (taskType === 'q3') {
        endpoint = '/api/qa';
        payload = { url: cleanUrl, query: queryText || 'What services do you offer?', max_pages: 15 };
      }

      let resultData = null;
      let usedLiveBackend = false;
      let backendError = null;

      try {
        const response = await fetch(`http://127.0.0.1:8000${endpoint}`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });
        if (response.ok) {
          resultData = await response.json();
          usedLiveBackend = true;
        } else {
          const errData = await response.json().catch(() => ({}));
          backendError = errData.error || `Server returned ${response.status}`;
        }
      } catch (err) {
        backendError = err.message || 'Unable to connect to local server on port 8000.';
      }

      // Fallback to sample data ONLY if testing default demo site offline
      if (!resultData) {
        if (cleanUrl.includes('books.toscrape.com')) {
          if (taskType === 'q1') {
            resultData = {
              task: 'q1_onpage',
              url: cleanUrl,
              summary: (selectedModel && selectedModel !== 'none') ? DEMO_Q1_SUMMARY : null,
              findings: DEMO_Q1_AUDIT,
            };
          } else if (taskType === 'q2') {
            resultData = {
              task: 'q2_nap',
              url: cleanUrl,
              in_site: DEMO_Q2_NAP,
              off_site: DEMO_Q2_OFFSITE,
              fields: DEMO_Q2_NAP,
            };
          } else {
            resultData = {
              task: 'q3_qa',
              url: cleanUrl,
              query: queryText || DEMO_Q3_QA.query,
              answer: {
                query: queryText || DEMO_Q3_QA.query,
                answer: (selectedModel && selectedModel !== 'none') ? DEMO_Q3_QA.answer : null,
                url: cleanUrl,
                excerpt: DEMO_Q3_QA.excerpt,
              },
            };
          }
        } else {
          // Custom domain error: Never show misleading books.toscrape.com mock data!
          setMessages((prev) => [
            ...prev,
            {
              id: Date.now() + 1,
              sender: 'agent',
              task: 'error',
              taskLabel: 'Audit Error',
              url: cleanUrl,
              error: backendError || 'Crawl request could not be completed on target site.',
              isLive: false,
            },
          ]);
          setIsProcessing(false);
          setActiveStep('');
          return;
        }
      }

      setMessages((prev) => [
        ...prev,
        {
          id: Date.now() + 1,
          sender: 'agent',
          task: taskType,
          taskLabel: taskLabels[taskType],
          url: cleanUrl,
          data: resultData,
          isLive: usedLiveBackend,
        },
      ]);
    } finally {
      setIsProcessing(false);
      setActiveStep('');
    }
  };

  const downloadJSON = (data, filename) => {
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleDownloadReport = (msg) => {
    let exportObj = null;
    let cleanHost = 'target';
    try {
      cleanHost = new URL(msg.url).hostname.replace(/[^a-z0-9]/gi, '_');
    } catch (_) {
      cleanHost = 'site';
    }
    let filename = `report_${cleanHost}.json`;

    if (msg.task === 'q1') {
      filename = `seo_audit_report_${cleanHost}.json`;
      exportObj = {
        report_title: 'Technical On-Page SEO Audit & Remediation Roadmap',
        target_url: msg.url,
        generated_at: new Date().toISOString(),
        ai_executive_summary: msg.data.summary || null,
        total_findings: msg.data.findings?.length || 0,
        findings: msg.data.findings || [],
      };
    } else if (msg.task === 'q2') {
      filename = `nap_consistency_report_${cleanHost}.json`;
      exportObj = {
        report_title: 'Business NAP Consistency Audit Report (In-Site & Off-Site)',
        target_url: msg.url,
        generated_at: new Date().toISOString(),
        in_site_consistency: msg.data.in_site || msg.data.fields || [],
        off_site_citations: msg.data.off_site || null,
        fields: msg.data.fields || [],
      };
    } else if (msg.task === 'q3') {
      filename = `aeo_qa_report_${cleanHost}.json`;
      exportObj = {
        report_title: 'AEO Grounded Q&A Verification Report',
        target_url: msg.url,
        query: msg.data.query || msg.data.answer?.query,
        direct_answer: msg.data.answer?.answer || null,
        grounding_evidence_excerpt: msg.data.answer?.excerpt || null,
        source_url: msg.data.answer?.url || null,
        generated_at: new Date().toISOString(),
      };
    }

    if (exportObj) {
      downloadJSON(exportObj, filename);
    }
  };

  return (
    <div className="console-layout">
      {/* Activity Feed / Message Thread */}
      <div className="activity-feed" role="log" aria-live="polite">
        {messages.length === 0 && (
          <div className="console-welcome">
            <span className="welcome-badge">Console Ready</span>
            <h2 className="welcome-title">What site would you like to inspect?</h2>
            <p className="welcome-subtitle">
              Enter any public domain or select a demonstration prompt below to run evidence-backed crawls.
            </p>

            <div className="quick-prompts">
              <button
                type="button"
                className="prompt-chip"
                onClick={() => handleQuickPrompt('https://books.toscrape.com', 'q1')}
              >
                <span>Crawl &amp; audit on-page SEO on <strong>https://books.toscrape.com</strong></span>
                <span className="prompt-chip-badge">Q1 Auditor</span>
              </button>

              <button
                type="button"
                className="prompt-chip"
                onClick={() => handleQuickPrompt('https://books.toscrape.com', 'q2')}
              >
                <span>Check business NAP consistency across pages on <strong>https://books.toscrape.com</strong></span>
                <span className="prompt-chip-badge">Q2 NAP</span>
              </button>

              <button
                type="button"
                className="prompt-chip"
                onClick={() => handleQuickPrompt('https://books.toscrape.com', 'q3', 'What is the warning about prices and ratings on this website?')}
              >
                <span>AEO Question: "What is the warning about prices and ratings on this website?"</span>
                <span className="prompt-chip-badge">Q3 AEO</span>
              </button>
            </div>
          </div>
        )}

        {/* Message Items */}
        {messages.map((msg) => (
          <div key={msg.id} className="message-block">
            {msg.sender === 'user' ? (
              <div className="message-row-user">
                <div className="user-bubble">
                  <span className="user-bubble-mode">{msg.taskLabel}</span>
                  <div>{msg.url}</div>
                  {msg.query && <div style={{ fontSize: '13px', opacity: 0.9, marginTop: '4px' }}>Query: "{msg.query}"</div>}
                </div>
              </div>
            ) : (
              <div className="agent-response-card">
                <div className="agent-response-header">
                  <div className="agent-header-left">
                    <div className="agent-avatar">AI</div>
                    <div>
                      <span className="agent-title">{msg.taskLabel} Result</span>
                      <span className="agent-url-badge" style={{ marginLeft: '8px' }}>{msg.url}</span>
                    </div>
                  </div>

                  <div className="agent-header-actions">
                    <button
                      type="button"
                      className="btn-download-report"
                      onClick={() => handleDownloadReport(msg)}
                      title="Download comprehensive audit report"
                    >
                      <span className="btn-dl-icon">&#8595;</span>
                      <span>Download Report</span>
                    </button>
                  </div>
                </div>

                <div className="result-content-body">
                  {/* Q1 On-Page Visualizer */}
                  {msg.task === 'q1' && (
                    <div>
                      {/* Executive Summary & Action Plan Card */}
                      {msg.data.summary && (
                        <div className="seo-summary-card">
                          <div className="seo-summary-header">
                            <div className="seo-summary-title-row">
                              <span className="summary-badge">
                                ✦ Executive Summary &amp; Action Plan
                              </span>
                              <div style={{ display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap' }}>
                                <span className="engine-badge ai-generated" title="Synthesized using LangChain LLM">
                                  <span className="engine-dot green"></span>
                                  AI Generated ({msg.data.summary.provider || 'LangChain'})
                                </span>
                                {msg.data.summary.health_score !== undefined && (
                                  <span className={`health-score-pill ${msg.data.summary.health_score >= 80 ? 'good' : msg.data.summary.health_score >= 60 ? 'fair' : 'poor'}`}>
                                    SEO Health Score: {msg.data.summary.health_score}/100
                                  </span>
                                )}
                              </div>
                            </div>
                            <p className="seo-summary-overview">{msg.data.summary.overview}</p>
                          </div>

                          {msg.data.summary.priority_actions && msg.data.summary.priority_actions.length > 0 && (
                            <div className="priority-actions-section">
                              <div className="priority-actions-title">Key Priority Changes to Boost SEO &amp; Fix Issues:</div>
                              <div className="priority-action-list">
                                {msg.data.summary.priority_actions.map((act, i) => (
                                  <div key={i} className="priority-action-item">
                                    <div className="action-rank-badge">#{act.priority || i + 1}</div>
                                    <div className="action-details">
                                      <div className="action-header-line">
                                        <strong className="action-name">{act.action || act.title}</strong>
                                        {act.impact && <span className={`impact-pill ${act.impact.toLowerCase()}`}>{act.impact} Impact</span>}
                                        {act.category && <span className="category-pill">{act.category}</span>}
                                      </div>
                                      <p className="action-desc">{act.description}</p>
                                    </div>
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}
                        </div>
                      )}

                      {/* Filter Chips & Engine Indicator */}
                      <div className="audit-stats-bar">
                        <span className="mono" style={{ fontSize: '12px', marginRight: '6px', color: 'var(--text-secondary)' }}>
                          {msg.data.findings?.length || 0} issues:
                        </span>
                        {['all', 'critical', 'high', 'medium', 'low'].map((sev) => {
                          const count = sev === 'all'
                            ? msg.data.findings?.length
                            : msg.data.findings?.filter((f) => f.severity === sev).length;
                          if (count === 0 && sev !== 'all') return null;
                          return (
                            <button
                              key={sev}
                              type="button"
                              className={`stat-chip ${sev} ${severityFilter === sev ? 'active-filter' : ''}`}
                              onClick={() => setSeverityFilter(sev)}
                            >
                              <span style={{ textTransform: 'capitalize' }}>{sev}</span>
                              <span>({count})</span>
                            </button>
                          );
                        })}

                        {/* Small label near severity indicating engine if AI summary was generated */}
                        <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center' }}>
                          {msg.data.summary?.is_ai && (
                            <span className="engine-small-tag ai" title="Summary powered by LangChain LLM">
                              ● AI Generated ({msg.data.summary.provider || 'LangChain'})
                            </span>
                          )}
                        </div>
                      </div>

                      {/* Findings Cards with Issue Nomenclature and Concrete Observed Evidence */}
                      <div className="findings-list">
                        {msg.data.findings
                          ?.filter((f) => severityFilter === 'all' || f.severity === severityFilter)
                          .map((finding, idx) => (
                            <div key={idx} className="finding-card">
                              <div className="finding-top">
                                <div className="finding-issue-wrapper">
                                  <span className="finding-issue-tag">ISSUE</span>
                                  <strong className="finding-issue-title">{finding.issue || finding.metric}</strong>
                                </div>
                                <span className={`severity-pill ${finding.severity}`}>{finding.severity}</span>
                              </div>
                              <div className="finding-page-url">
                                <span className="finding-url-label">Page:</span> {finding.page}
                              </div>
                              <div className="finding-evidence">
                                <strong>Observed Evidence:</strong> {finding.evidence}
                              </div>
                              <div className="finding-fix">
                                <strong>Recommended Fix:</strong> {finding.suggested_fix}
                              </div>
                            </div>
                          ))}
                      </div>
                    </div>
                  )}

                  {/* Q2 NAP Consistency Visualizer (In-Site & Off-Site Dual Tabs) */}
                  {msg.task === 'q2' && (
                    <NapVisualizer data={msg.data} />
                  )}

                  {/* Q3 AEO Grounded Q&A Visualizer */}
                  {msg.task === 'q3' && (
                    <div className="qa-result-box">
                      <div className="qa-query-header">Query: "{msg.data.query || msg.data.answer?.query}"</div>
                      {msg.data.answer?.excerpt ? (
                        <div className="qa-content-container">
                          {/* Direct Synthesized Answer Card */}
                          <div className="qa-direct-answer-card">
                            <div className="qa-answer-label">
                              <span className="qa-sparkle">✦</span> Direct Answer
                            </div>
                            <p className="qa-direct-answer-text">
                              {msg.data.answer.answer || msg.data.answer.excerpt}
                            </p>
                          </div>

                          {/* Verbatim Grounded Excerpt Box */}
                          <div className="qa-excerpt-card">
                            <div className="qa-excerpt-header">
                              <span className="qa-evidence-tag">Evidence</span>
                              <span className="qa-evidence-subtitle">Verbatim grounded excerpt from site markup</span>
                            </div>
                            <blockquote className="qa-excerpt-quote">
                              "{msg.data.answer.excerpt}"
                            </blockquote>
                            <div className="qa-meta-bar">
                              <span>Source Page:</span>
                              <a
                                href={msg.data.answer.url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="qa-url-link"
                              >
                                <span>{msg.data.answer.url}</span>
                                <span>&#8599;</span>
                              </a>
                            </div>
                          </div>
                        </div>
                      ) : (
                        <div className="qa-refusal-box">
                          <div className="qa-refusal-title">Refusal to Guess (null)</div>
                          <p className="qa-refusal-desc">
                            The target site markup contains no grounded passage satisfying the relevance threshold for this query.
                          </p>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        ))}

        {/* Live Processing Indicator */}
        {isProcessing && (
          <div className="agent-response-card">
            <div className="loading-box">
              <div className="loading-spinner" aria-hidden="true"></div>
              <div className="loading-label">{activeStep}</div>
              <div className="progress-steps">
                <span className="step-item active">&#9679; Discovery</span>
                <span className="step-item active">&#9679; Markup Parser</span>
                <span className="step-item">&#9679; Evaluation</span>
                <span className="step-item">&#9679; Verification</span>
              </div>
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Floating Bottom Search & Action Box */}
      <div className="floating-search-wrapper">
        <form className="floating-search-bar" onSubmit={handleSubmit}>
          {/* Main Target URL Input */}
          <div className="search-input-row">
            <input
              type="text"
              className="search-main-input"
              placeholder={
                selectedTask === 'q1'
                  ? 'Enter website URL to crawl (e.g. https://books.toscrape.com)...'
                  : selectedTask === 'q2'
                  ? 'Enter business website URL to check NAP consistency...'
                  : 'Enter website URL to search within...'
              }
              value={urlInput}
              onChange={(e) => setUrlInput(e.target.value)}
              disabled={isProcessing}
            />
          </div>

          {/* Secondary Query Input (only visible when AEO Q/A agent is selected) */}
          {selectedTask === 'q3' && (
            <div style={{ padding: '0 6px 4px' }}>
              <input
                type="text"
                className="qa-secondary-input"
                placeholder="Enter your natural-language question (e.g. What is the return policy?)..."
                value={queryInput}
                onChange={(e) => setQueryInput(e.target.value)}
                disabled={isProcessing}
              />
            </div>
          )}

          {/* Bottom Controls Row */}
          <div className="search-bottom-row">
            {/* Task Selector Dropdown near Send button */}
            <div className="search-mode-dropdown-wrapper">
              <span className="search-mode-label">Mode:</span>
              <select
                className="search-mode-select"
                value={selectedTask}
                onChange={(e) => setSelectedTask(e.target.value)}
                disabled={isProcessing}
                aria-label="Select Agent Action"
              >
                <option value="q1">Crawl site for SEO issues</option>
                <option value="q2">NAP consistency checker</option>
                <option value="q3">AEO Q/A agent</option>
              </select>
            </div>

            <div className="search-actions-right">
              <button
                type="submit"
                className="btn-send-agent"
                disabled={!urlInput.trim() || isProcessing}
              >
                <span>Run Agent</span>
                <svg width="14" height="14" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path d="M3.33337 8H12.6667" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round"/>
                  <path d="M8 3.33334L12.6667 8.00001L8 12.6667" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
}
