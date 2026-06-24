import React, { useState, useRef, useEffect } from 'react';
import { Bot, User, Send, FileText, Loader, Zap } from 'lucide-react';
import apiClient from '../api/client';
import './AIAssistantPage.css';

const AIAssistantPage = () => {
  const [messages, setMessages] = useState([
    { role: 'assistant', content: 'Hello! I am your NeuroGuard AI Security Assistant powered by Groq. How can I help you analyze today\'s security events?' }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [reportLoading, setReportLoading] = useState(false);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSend = async (e) => {
    e.preventDefault();
    if (!input.trim()) return;

    const userMessage = input.trim();
    setInput('');
    setMessages(prev => [...prev, { role: 'user', content: userMessage }]);
    setLoading(true);

    try {
      const res = await apiClient.post('/llm/chat', { query: userMessage });
      setMessages(prev => [...prev, { role: 'assistant', content: res.data.answer }]);
    } catch (error) {
      console.error('Failed to send message', error);
      setMessages(prev => [...prev, { role: 'assistant', content: 'Sorry, I encountered an error communicating with the Groq API. Please check the backend configuration.' }]);
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateReport = async () => {
    setReportLoading(true);
    try {
      const res = await apiClient.post('/llm/report');
      setMessages(prev => [...prev, { 
        role: 'assistant', 
        content: `**Daily Executive Security Report generated:**\n\n${res.data.report}` 
      }]);
    } catch (error) {
      console.error('Failed to generate report', error);
      setMessages(prev => [...prev, { role: 'assistant', content: 'Failed to generate the report.' }]);
    } finally {
      setReportLoading(false);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: 'calc(100vh - 8rem)' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
        <div>
          <h2 style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.25rem' }}>
            <Zap className="text-accent-blue" /> Groq AI Security Assistant
          </h2>
          <p className="text-muted">Ask questions about anomalies or generate executive summaries.</p>
        </div>
        <button 
          onClick={handleGenerateReport} 
          disabled={reportLoading}
          className="btn-primary flex-center" 
          style={{ gap: '0.5rem', background: 'var(--accent-blue)', borderColor: 'var(--accent-blue)' }}
        >
          {reportLoading ? <Loader className="spin" size={16} /> : <FileText size={16} />} 
          Generate Daily Report
        </button>
      </div>

      <div className="glass-card chat-container" style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        <div className="chat-messages" style={{ flex: 1, overflowY: 'auto', padding: '1.5rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          {messages.map((msg, idx) => (
            <div key={idx} className={`chat-bubble-wrapper ${msg.role}`}>
              <div className="chat-avatar flex-center">
                {msg.role === 'assistant' ? <Bot size={20} /> : <User size={20} />}
              </div>
              <div className="chat-bubble">
                {msg.content.split('\n').map((line, i) => (
                  <span key={i}>
                    {line}
                    <br />
                  </span>
                ))}
              </div>
            </div>
          ))}
          {loading && (
            <div className="chat-bubble-wrapper assistant">
              <div className="chat-avatar flex-center"><Bot size={20} /></div>
              <div className="chat-bubble loading-dots">
                <span>.</span><span>.</span><span>.</span>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        <div className="chat-input-area" style={{ padding: '1rem', borderTop: '1px solid var(--glass-border)', background: 'rgba(0,0,0,0.2)' }}>
          <form onSubmit={handleSend} style={{ display: 'flex', gap: '1rem' }}>
            <input 
              type="text" 
              className="glass-input" 
              style={{ flex: 1 }}
              placeholder="Ask about today's anomalies..." 
              value={input}
              onChange={e => setInput(e.target.value)}
              disabled={loading || reportLoading}
            />
            <button 
              type="submit" 
              className="btn-primary flex-center"
              disabled={!input.trim() || loading || reportLoading}
            >
              <Send size={18} />
            </button>
          </form>
        </div>
      </div>
    </div>
  );
};

export default AIAssistantPage;
