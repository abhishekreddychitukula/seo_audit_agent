import React from 'react';

export default function LandingPage({ onLaunchConsole }) {
  return (
    <main className="landing-container">
      {/* Hero Section */}
      <section className="landing-hero" aria-labelledby="hero-title">
        <div className="hero-pill">
          <span className="hero-pill-badge">v2.0 READY</span>
          <span>Zero Paid Subscriptions · Multi-Provider AI Fallback</span>
        </div>

        <h1 id="hero-title" className="landing-title">
          Autonomous SEO Auditing <br />
          <span className="landing-title-subtle">&amp; Grounded Answer Retrieval.</span>
        </h1>

        <p className="landing-description">
          An evidence-backed agentic platform that crawls, evaluates on-page markup, verifies 
          local business NAP consistency, and retrieves exact answer passages without hallucination.
        </p>

        {/* Primary CTA: "Check your site" */}
        <div>
          <button
            className="hero-cta-btn"
            onClick={onLaunchConsole}
            type="button"
          >
            <span>Check your site</span>
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M3.33337 8H12.6667" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round"/>
              <path d="M8 3.33334L12.6667 8.00001L8 12.6667" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </button>
        </div>
      </section>

      {/* 3 Core Capability Modules */}
      <section className="capabilities-grid" aria-label="Core Capabilities">
        <article className="capability-card">
          <span className="card-num">01 // AUDITOR</span>
          <h2 className="card-title">On-Page SEO Crawler</h2>
          <p className="card-desc">
            Evaluates server-returned markup and response headers for 20+ search engine crawler criteria: 
            click-depth, redirect chains, orphan detection, robots noindex, canonicals, render-blocking assets, 
            and sitewide duplicate title cannibalization.
          </p>
          <div className="card-deliverable-pill">
            <span>Outputs:</span>
            <strong className="mono">audit.json</strong>
          </div>
        </article>

        <article className="capability-card">
          <span className="card-num">02 // CONSISTENCY</span>
          <h2 className="card-title">NAP Consistency Checker</h2>
          <p className="card-desc">
            Finds all pages where a business is mentioned via sitemaps, JSON-LD, address elements, and footers. 
            Applies rule-based normalizers to separate cosmetic formatting from genuine mismatches with transparent confidence scoring.
          </p>
          <div className="card-deliverable-pill">
            <span>Outputs:</span>
            <strong className="mono">nap_report.json</strong>
          </div>
        </article>

        <article className="capability-card">
          <span className="card-num">03 // GROUNDED AEO</span>
          <h2 className="card-title">Grounded Q&amp;A Agent</h2>
          <p className="card-desc">
            Answers search queries by extracting the exact, unaltered verbatim passage from the page markup. 
            Employs BM25 lexical ranking and strict grounding thresholds—guaranteeing null refusal rather than guessing.
          </p>
          <div className="card-deliverable-pill">
            <span>Outputs:</span>
            <strong className="mono">answer.json</strong>
          </div>
        </article>
      </section>

      {/* Understated Trust & Architectural Highlights */}
      <section className="trust-strip" aria-label="Design Principles">
        <div className="trust-item">
          <div className="trust-icon" aria-hidden="true">&#10003;</div>
          <span className="trust-text">No paid API subscriptions or connectors</span>
        </div>
        <div className="trust-item">
          <div className="trust-icon" aria-hidden="true">&#10003;</div>
          <span className="trust-text">Verifiable markup evidence per finding</span>
        </div>
        <div className="trust-item">
          <div className="trust-icon" aria-hidden="true">&#10003;</div>
          <span className="trust-text">Dynamic LLM switching &amp; automatic fallback</span>
        </div>
        <div className="trust-item">
          <div className="trust-icon" aria-hidden="true">&#10003;</div>
          <span className="trust-text">Generalizes autonomously to unseen domains</span>
        </div>
      </section>
    </main>
  );
}
