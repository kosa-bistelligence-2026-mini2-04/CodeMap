import React, { useState, useEffect, useRef } from 'react';
import { Send, RefreshCw, CheckCircle2, AlertCircle, Clock, Terminal } from 'lucide-react';
import ReactMarkdown from 'react-markdown';

const API_BASE_URL = 'http://127.0.0.1:8000';

function App() {
  const [githubUrl, setGithubUrl] = useState('');
  const [repoId, setRepoId] = useState(localStorage.getItem('last_repo_id') || '');
  const [status, setStatus] = useState('pending');
  const [question, setQuestion] = useState('');
  const [chatHistory, setChatHistory] = useState([]);
  const [isQuerying, setIsQuerying] = useState(false);
  const [isIndexing, setIsIndexing] = useState(false);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [chatHistory]);

  // Polling for index status
  useEffect(() => {
    let interval;
    if (repoId && (status === 'pending' || status === 'indexing')) {
      interval = setInterval(async () => {
        try {
          const resp = await fetch(`${API_BASE_URL}/repos/${repoId}/status`);
          const data = await resp.json();
          if (data.status) {
            setStatus(data.status);
          }
        } catch (e) {
          console.error("Status check failed", e);
        }
      }, 3000);
    }
    return () => clearInterval(interval);
  }, [repoId, status]);

  const addRepo = async () => {
    if (!githubUrl) return;
    setIsIndexing(true);
    try {
      const resp = await fetch(`${API_BASE_URL}/repos`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ github_url: githubUrl.trim() }),
      });
      const data = await resp.json();
      setRepoId(data.repo_id);
      setStatus(data.status);
      localStorage.setItem('last_repo_id', data.repo_id);
    } catch (e) {
      console.error("Add repo failed", e);
      setStatus('error');
    } finally {
      setIsIndexing(false);
    }
  };

  const handleQuery = async (e) => {
    e.preventDefault();
    if (!question || !repoId || isQuerying) return;

    const userMsg = { role: 'user', content: question };
    setChatHistory(prev => [...prev, userMsg, { role: 'ai', content: '' }]);
    setQuestion('');
    setIsQuerying(true);

    try {
      const response = await fetch(`${API_BASE_URL}/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ repo_id: repoId, question }),
      });

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let fullContent = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');

        lines.forEach(line => {
          if (line.startsWith('data: ')) {
            const content = line.substring(6);
            if (content === '[DONE]') return;
            fullContent += content;
            setChatHistory(prev => {
              const newHist = [...prev];
              newHist[newHist.length - 1].content = fullContent;
              return newHist;
            });
          }
        });
      }
    } catch (e) {
      console.error("Query failed", e);
      setChatHistory(prev => [...prev.slice(0, -1), { role: 'ai', content: '⚠️ Error: Failed to generate response.' }]);
    } finally {
      setIsQuerying(false);
    }
  };

  const getStatusIcon = (st) => {
    switch (st) {
      case 'ready': return <CheckCircle2 size={16} />;
      case 'indexing': return <RefreshCw size={16} className="spinner" />;
      case 'pending': return <Clock size={16} />;
      case 'error': return <AlertCircle size={16} />;
      default: return null;
    }
  };

  return (
    <div className="App">
      <header className="glass">
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1rem' }}>
          <Terminal color="var(--primary)" size={32} />
          <h1 style={{ letterSpacing: '-0.025em' }}>CodeBase Q&A</h1>
          {repoId && (
            <div className={`status-badge ${status}`} style={{ marginLeft: 'auto' }}>
              {getStatusIcon(status)}
              {status.toUpperCase()}
            </div>
          )}
        </div>
        
        <div className="repo-input-container">
          <input 
            type="text" 
            placeholder="Search repository URL (e.g. https://github.com/Manas2412/CodeBase-Q-A-with-RAG)"
            value={githubUrl}
            onChange={(e) => setGithubUrl(e.target.value)}
          />
          <button onClick={addRepo} disabled={isIndexing || !githubUrl}>
            {isIndexing ? <RefreshCw className="spinner" /> : 'Connect'}
          </button>
        </div>
      </header>

      <main className="chat-container glass">
        <div className="messages">
          {chatHistory.length === 0 && (
            <div style={{ textAlign: 'center', marginTop: '10%', color: 'var(--text-dim)' }}>
              <Terminal size={48} style={{ marginBottom: '1rem', opacity: 0.5 }} />
              <h3>Enter a repository to start analyzing code</h3>
              <p>Ask architectural questions, find bugs, or explain logic in seconds.</p>
            </div>
          )}
          {chatHistory.map((m, i) => (
            <div key={i} className={`message ${m.role}`}>
              {m.role === 'ai' ? (
                <ReactMarkdown>{m.content}</ReactMarkdown>
              ) : (
                m.content
              )}
            </div>
          ))}
          <div ref={messagesEndRef} />
        </div>

        <form className="chat-input-area" onSubmit={handleQuery}>
          <div style={{ display: 'flex', gap: '1rem' }}>
            <input 
              type="text" 
              placeholder={status === 'ready' ? "Ask about the code..." : "Wait for indexing to complete..."}
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              disabled={status !== 'ready' || isQuerying}
            />
            <button type="submit" disabled={status !== 'ready' || isQuerying || !question}>
              {isQuerying ? <RefreshCw className="spinner" /> : <Send size={18} />}
            </button>
          </div>
        </form>
      </main>

      <footer style={{ textAlign: 'center', margin: '1rem 0', color: 'var(--text-dim)', fontSize: '0.8rem' }}>
        Built with FastAPI, Redis, PostgreSQL + pgvector & Voyage AI
      </footer>
    </div>
  );
}

export default App;
