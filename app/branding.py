PRODUCT_NAME = "Veridian"
PRODUCT_TAGLINE = "Private document intelligence"
PRODUCT_INTRO = (
    "Ask a question about your indexed documents. "
    "Veridian answers only from material you have provided."
)
PRODUCT_DESCRIPTION = "Grounded answers from your documents. Fully offline."

CUSTOM_CSS = """
:root {
    --va-bg: #090a0d;
    --va-surface: #111318;
    --va-surface-raised: #171a21;
    --va-border: #252a34;
    --va-border-subtle: #1c2029;
    --va-text: #eceef2;
    --va-text-muted: #8b92a0;
    --va-accent: #5c7f9e;
    --va-accent-soft: rgba(92, 127, 158, 0.12);
    --va-success: #4a8f6a;
    --va-danger: #9e5c5c;
}

.gradio-container {
    max-width: 1280px !important;
    margin: 0 auto !important;
    font-family: ui-sans-serif, system-ui, -apple-system, 'Segoe UI', sans-serif !important;
}

.va-shell {
    padding: 0 0 2rem 0;
}

.va-header {
    padding: 2rem 0 1.75rem 0;
    border-bottom: 1px solid var(--va-border-subtle);
    margin-bottom: 1.75rem;
    text-align: center;
}

.va-brand {
    font-size: 1.75rem;
    font-weight: 600;
    letter-spacing: -0.03em;
    color: var(--va-text);
    line-height: 1.2;
    margin: 0;
}

.va-tagline {
    font-size: 0.9375rem;
    font-weight: 400;
    color: var(--va-text-muted);
    margin: 0.35rem 0 0 0;
    letter-spacing: 0.01em;
}

.va-intro {
    font-size: 0.8125rem;
    font-weight: 400;
    color: var(--va-text-muted);
    margin: 0.65rem auto 0;
    max-width: 34rem;
    line-height: 1.55;
    opacity: 0.9;
}

.va-cites {
    margin-top: 1.25rem;
    padding-top: 1rem;
    border-top: 1px solid var(--va-border-subtle);
}

.va-cites-label {
    font-size: 0.6875rem;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--va-text-muted);
    margin: 0 0 0.625rem 0;
}

.va-cite-item {
    background: var(--va-surface);
    border: 1px solid var(--va-border-subtle);
    border-left: 2px solid var(--va-accent);
    border-radius: 6px;
    padding: 0.5rem 0.625rem;
    margin-bottom: 0.4rem;
}

.va-cite-item:last-child {
    margin-bottom: 0;
}

.va-cite-meta {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    flex-wrap: wrap;
    margin-bottom: 0.25rem;
}

.va-cite-num {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 1.25rem;
    height: 1.25rem;
    padding: 0 0.3rem;
    font-size: 0.6875rem;
    font-weight: 600;
    color: var(--va-accent);
    background: var(--va-accent-soft);
    border-radius: 4px;
    font-family: ui-monospace, monospace;
}

.va-cite-file {
    font-size: 0.75rem;
    font-weight: 500;
    color: var(--va-text);
}

.va-cite-page {
    font-size: 0.6875rem;
    color: var(--va-text-muted);
    font-family: ui-monospace, monospace;
}

.va-cite-excerpt {
    font-size: 0.75rem;
    line-height: 1.45;
    color: var(--va-text-muted);
    margin: 0;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
}

.va-section-label {
    font-size: 0.6875rem;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--va-text-muted);
    margin: 0 0 0.75rem 0;
}

.va-status-card {
    background: var(--va-surface-raised);
    border: 1px solid var(--va-border);
    border-radius: 10px;
    padding: 1rem 1.125rem;
    margin-bottom: 0.5rem;
}

.va-status-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.35rem 0;
    font-size: 0.8125rem;
    color: var(--va-text-muted);
    border-bottom: 1px solid var(--va-border-subtle);
}

.va-status-row:last-child {
    border-bottom: none;
}

.va-status-row span:last-child {
    color: var(--va-text);
    font-family: ui-monospace, 'SF Mono', 'IBM Plex Mono', monospace;
    font-size: 0.75rem;
}

.va-status-dot {
    display: inline-block;
    width: 7px;
    height: 7px;
    border-radius: 50%;
    margin-right: 8px;
    vertical-align: middle;
}

.va-status-dot.online { background: var(--va-success); box-shadow: 0 0 8px rgba(74, 143, 106, 0.45); }
.va-status-dot.offline { background: var(--va-danger); }

.va-panel-title {
    font-size: 1rem;
    font-weight: 600;
    color: var(--va-text);
    margin: 0 0 1rem 0;
    letter-spacing: -0.01em;
}

.va-footer-note {
    font-size: 0.75rem;
    color: var(--va-text-muted);
    margin-top: 1.5rem;
    padding-top: 1rem;
    border-top: 1px solid var(--va-border-subtle);
}

footer { display: none !important; }

.block {
    border-color: var(--va-border) !important;
    background: var(--va-surface) !important;
    border-radius: 10px !important;
}

.contain {
    background: var(--va-bg) !important;
}

button.primary {
    background: var(--va-accent) !important;
    border: none !important;
    font-weight: 500 !important;
    letter-spacing: 0.01em !important;
}

button.primary:hover {
    filter: brightness(1.08);
}

button.secondary {
    background: transparent !important;
    border: 1px solid var(--va-border) !important;
    color: var(--va-text-muted) !important;
}

label span {
    font-weight: 500 !important;
    font-size: 0.8125rem !important;
    color: var(--va-text-muted) !important;
}

textarea, input {
    font-family: ui-sans-serif, system-ui, sans-serif !important;
}

.va-answer {
    font-size: 0.9375rem;
    line-height: 1.65;
    color: var(--va-text);
    margin: 0 0 0.25rem 0;
}

.va-answer-refused {
    color: var(--va-text-muted);
}

/* ---- Chat panel ---- */
.va-chat-column > .block,
.va-chat-column > .form {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    padding: 0 !important;
}

.va-chat-column .panel-wrap,
.va-chat-column [class*="chatbot"] > .wrap {
    background: var(--va-surface) !important;
    border: 1px solid var(--va-border) !important;
    border-radius: 12px !important;
    padding: 0.75rem !important;
}

.va-chat-column .prose.chatbot.md,
.va-chat-column .md {
    font-size: 0.9375rem !important;
    line-height: 1.65 !important;
    color: var(--va-text) !important;
}

.va-chat-column .prose.chatbot.md p {
    margin: 0 0 0.75rem 0 !important;
}

.va-chat-column .prose.chatbot.md p:last-child {
    margin-bottom: 0 !important;
}

.va-chat-column .user-row.bubble,
.va-chat-column .bubble.user-row {
    background: rgba(92, 127, 158, 0.14) !important;
    border: 1px solid rgba(92, 127, 158, 0.28) !important;
    border-radius: 16px 16px 4px 16px !important;
    padding: 0.7rem 0.95rem !important;
    margin-left: auto !important;
    max-width: 78% !important;
    color: var(--va-text) !important;
    font-size: 0.9rem !important;
    line-height: 1.55 !important;
}

.va-chat-column .bot-row.bubble,
.va-chat-column .bubble.bot-row {
    background: var(--va-surface-raised) !important;
    border: 1px solid var(--va-border) !important;
    border-radius: 16px 16px 16px 4px !important;
    padding: 0.85rem 1rem !important;
    max-width: 94% !important;
    color: var(--va-text) !important;
    font-size: 0.9375rem !important;
    line-height: 1.65 !important;
}

.va-chat-column .panel.user-row,
.va-chat-column .panel.bot-row {
    padding: 0.35rem 0 !important;
}

.va-composer-row {
    gap: 0.625rem !important;
    align-items: stretch !important;
    margin-top: 0.75rem !important;
}

.va-composer-row textarea,
.va-composer-row .wrap {
    background: var(--va-surface-raised) !important;
    border-color: var(--va-border) !important;
    border-radius: 10px !important;
    font-size: 0.9rem !important;
    line-height: 1.5 !important;
}

.va-composer-row textarea:focus {
    border-color: var(--va-accent) !important;
    box-shadow: 0 0 0 1px rgba(92, 127, 158, 0.25) !important;
}

.va-composer-row button.primary {
    border-radius: 10px !important;
    min-height: 42px !important;
}

footer { display: none !important; }
"""
