"use client";

import { useState, useRef, useEffect } from "react";
import 'katex/dist/katex.min.css';
import { InlineMath, BlockMath } from 'react-katex';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function Home() {
  // ── State ──
  const [docId, setDocId] = useState(null);
  const [docName, setDocName] = useState("");
  const [docStatus, setDocStatus] = useState(null); // null | "uploading" | "processing" | "completed" | "error"
  const [messages, setMessages] = useState([]);
  const [query, setQuery] = useState("");
  const [isAsking, setIsAsking] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const [error, setError] = useState(null);

  const fileInputRef = useRef(null);
  const messagesEndRef = useRef(null);
  const pollRef = useRef(null);

  // ── Auto-scroll chat ──
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // ── Poll status ──
  useEffect(() => {
    if (docStatus === "processing" && docId) {
      pollRef.current = setInterval(async () => {
        try {
          const res = await fetch(`${API_BASE}/api/status/${docId}`);
          const data = await res.json();
          if (data.status === "completed") {
            setDocStatus("completed");
            clearInterval(pollRef.current);
          }
        } catch (err) {
          // keep polling
        }
      }, 3000);

      return () => clearInterval(pollRef.current);
    }
  }, [docStatus, docId]);

  // ── Upload handler ──
  async function handleUpload(file) {
    if (!file || !file.name.toLowerCase().endsWith(".pdf")) {
      setError("Please select a PDF file");
      return;
    }

    setError(null);
    setDocStatus("uploading");
    setDocName(file.name);
    setMessages([]);

    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch(`${API_BASE}/api/upload`, {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Upload failed");
      }

      const data = await res.json();
      setDocId(data.doc_id);
      setDocStatus("processing");
    } catch (err) {
      setError(err.message);
      setDocStatus("error");
    }
  }

  // ── Chat handler ──
  async function handleAsk(e) {
    e.preventDefault();
    if (!query.trim() || !docId || docStatus !== "completed") return;

    const userQuery = query.trim();
    setQuery("");
    setIsAsking(true);

    // Add user message
    setMessages((prev) => [...prev, { role: "user", content: userQuery }]);

    try {
      const res = await fetch(`${API_BASE}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ doc_id: docId, query: userQuery }),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Chat failed");
      }

      const data = await res.json();

      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: data.answer,
          reasoning: data.reasoning,
          sources: data.sources,
        },
      ]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: `Error: ${err.message}` },
      ]);
    } finally {
      setIsAsking(false);
    }
  }

  // ── Drag & Drop ──
  function handleDragOver(e) {
    e.preventDefault();
    setDragOver(true);
  }

  function handleDragLeave() {
    setDragOver(false);
  }

  function handleDrop(e) {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    handleUpload(file);
  }

  // ── Render ──
  return (
    <>
      {/* Navbar */}
      <nav className="navbar">
        <div className="navbar-inner">
          <div className="logo">
            <div className="logo-icon">🌲</div>
            Vectorless RAG
          </div>
        </div>
      </nav>

      <main className="container main-content">
        {/* ── Upload Section ── */}
        {!docId && (
          <section style={{ animation: "fadeSlideIn 0.5s ease" }}>
            <h1 className="section-title">Chat with your Documents</h1>
            <p className="section-subtitle">
              Upload a PDF and ask questions — powered by tree-based reasoning,
              no vector database needed.
            </p>

            <div
              className={`upload-zone ${dragOver ? "drag-over" : ""}`}
              onClick={() => fileInputRef.current?.click()}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
            >
              <div className="upload-zone-icon">
                {docStatus === "uploading" ? "⏳" : "📄"}
              </div>
              <div className="upload-zone-title">
                {docStatus === "uploading"
                  ? "Uploading..."
                  : "Drop your PDF here or click to browse"}
              </div>
              <div className="upload-zone-subtitle">
                Supports PDF files • Max 50MB
              </div>
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf"
                className="hidden"
                onChange={(e) => handleUpload(e.target.files[0])}
              />
            </div>

            {error && (
              <div className="mt-16" style={{ color: "var(--accent-red)" }}>
                ⚠️ {error}
              </div>
            )}
          </section>
        )}

        {/* ── Document Status ── */}
        {docId && (
          <section style={{ animation: "fadeSlideIn 0.4s ease" }}>
            <div className="doc-card mb-16">
              <div className="doc-card-info">
                <div className="doc-card-icon">📄</div>
                <div>
                  <div className="doc-card-name">{docName}</div>
                  <div className="doc-card-id">{docId}</div>
                </div>
              </div>
              <div className="flex items-center gap-12">
                {docStatus === "processing" && (
                  <span className="badge badge-processing">
                    <span className="spinner" style={{ width: 12, height: 12, borderWidth: 2 }} />
                    Processing
                  </span>
                )}
                {docStatus === "completed" && (
                  <span className="badge badge-ready">✓ Ready</span>
                )}
                {docStatus === "error" && (
                  <span className="badge badge-error">✕ Error</span>
                )}
                <button
                  className="btn btn-secondary"
                  onClick={() => {
                    setDocId(null);
                    setDocName("");
                    setDocStatus(null);
                    setMessages([]);
                    setError(null);
                  }}
                >
                  New Upload
                </button>
              </div>
            </div>

            {/* ── Processing State ── */}
            {docStatus === "processing" && (
              <div className="empty-state">
                <div className="empty-state-icon animate-pulse">🌳</div>
                <div className="empty-state-text">
                  Building document tree structure...
                </div>
                <div
                  style={{
                    fontSize: "var(--font-size-xs)",
                    color: "var(--text-tertiary)",
                    marginTop: 8,
                  }}
                >
                  PageIndex is analyzing your document. This may take a minute.
                </div>
              </div>
            )}

            {/* ── Chat Interface ── */}
            {docStatus === "completed" && (
              <div className="chat-container">
                <div className="chat-header">
                  <h2 className="chat-header-title">💬 Chat</h2>
                  <span
                    style={{
                      fontSize: "var(--font-size-xs)",
                      color: "var(--text-tertiary)",
                    }}
                  >
                    Powered by DeepSeek + PageIndex Tree Search
                  </span>
                </div>

                {/* Messages */}
                <div className="chat-messages">
                  {messages.length === 0 && (
                    <div className="empty-state">
                      <div className="empty-state-icon">💡</div>
                      <div className="empty-state-text">
                        Ask a question about your document
                      </div>
                      <div
                        style={{
                          fontSize: "var(--font-size-xs)",
                          color: "var(--text-tertiary)",
                          marginTop: 4,
                        }}
                      >
                        Try: &quot;What are the main findings?&quot; or &quot;Summarize
                        section 3&quot;
                      </div>
                    </div>
                  )}

                  {messages.map((msg, i) => (
                    <Message key={i} message={msg} />
                  ))}

                  {isAsking && (
                    <div className="message message-assistant">
                      <div className="message-label">Assistant</div>
                      <div className="message-bubble">
                        <div className="typing-dots">
                          <span />
                          <span />
                          <span />
                        </div>
                      </div>
                    </div>
                  )}

                  <div ref={messagesEndRef} />
                </div>

                {/* Input */}
                <div className="chat-input-area">
                  <form className="chat-input-form" onSubmit={handleAsk}>
                    <input
                      className="input"
                      type="text"
                      placeholder="Ask a question about your document..."
                      value={query}
                      onChange={(e) => setQuery(e.target.value)}
                      disabled={isAsking}
                      autoFocus
                    />
                    <button
                      type="submit"
                      className="btn btn-primary"
                      disabled={isAsking || !query.trim()}
                    >
                      {isAsking ? (
                        <span className="spinner" style={{ width: 16, height: 16, borderWidth: 2 }} />
                      ) : (
                        "Send →"
                      )}
                    </button>
                  </form>
                </div>
              </div>
            )}
          </section>
        )}
      </main>
    </>
  );
}

// ── Message Component ──
function Message({ message }) {
  const [showReasoning, setShowReasoning] = useState(false);
  const [showSources, setShowSources] = useState(false);

  const isUser = message.role === "user";

  // Simple math rendering: split by $$ and $
  const renderContent = (text) => {
    const parts = text.split(/(\$\$[\s\S]*?\$\$|\$[\s\S]*?\$)/g);
    return parts.map((part, i) => {
      if (part.startsWith('$$') && part.endsWith('$$')) {
        const math = part.slice(2, -2);
        return <BlockMath key={i} math={math} />;
      } else if (part.startsWith('$') && part.endsWith('$') && part.length > 2) {
        const math = part.slice(1, -1);
        return <InlineMath key={i} math={math} />;
      } else {
        return <span key={i}>{part}</span>;
      }
    });
  };

  return (
    <div className={`message ${isUser ? "message-user" : "message-assistant"}`}>
      <div className="message-label">{isUser ? "You" : "Assistant"}</div>
      <div className="message-bubble">
        {renderContent(message.content)}
      </div>

      {/* Reasoning */}
      {message.reasoning && (
        <>
          <button
            className="reasoning-toggle"
            onClick={() => setShowReasoning(!showReasoning)}
          >
            {showReasoning ? "▼" : "▶"} Tree Search Reasoning
          </button>
          {showReasoning && (
            <div className="reasoning-content">{message.reasoning}</div>
          )}
        </>
      )}

      {/* Sources */}
      {message.sources && message.sources.length > 0 && (
        <div className="sources-container">
          <button
            className="sources-toggle"
            onClick={() => setShowSources(!showSources)}
          >
            {showSources ? "▼" : "▶"} Sources ({message.sources.length})
          </button>
          {showSources && (
            <div className="sources-content">
              {message.sources.map((src, i) => (
                <div key={i} className="source-card">
                  <div className="source-card-header">
                    <span className="source-card-title">{src.title}</span>
                    {src.page_index != null && (
                      <span className="source-card-page">
                        Page {src.page_index}
                      </span>
                    )}
                  </div>
                  <div className="source-card-preview">{src.text_preview}</div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
