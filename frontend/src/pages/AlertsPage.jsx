import React, { useState, useEffect, useCallback } from 'react';
import { ShieldAlert, AlertTriangle, UserCheck, Clock, Search, FileText } from 'lucide-react';
import apiClient from '../api/client';
import './AlertsPage.css';

const AlertsPage = () => {
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('all'); // all, stranger, recognized
  const [selectedEvent, setSelectedEvent] = useState(null);

  const fetchEvents = async () => {
    try {
      setLoading(true);
      const endpoint = filter === 'all' ? '/events' : `/events?event_type=${filter}`;
      const res = await apiClient.get(endpoint);
      setEvents(res.data.events);
    } catch (error) {
      console.error('Failed to fetch events:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchEvents();
  }, [filter]);

  // Connect to live events WebSocket
  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token) return;

    let wsUrl;
    if (import.meta.env.VITE_API_URL) {
      const urlObj = new URL(import.meta.env.VITE_API_URL);
      const wsProtocol = urlObj.protocol === 'https:' ? 'wss:' : 'ws:';
      wsUrl = `${wsProtocol}//${urlObj.host}/api/events/ws?token=${token}`;
    } else {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      wsUrl = `${protocol}//${window.location.host}/api/events/ws?token=${token}`;
    }
    
    const ws = new WebSocket(wsUrl);
    
    ws.onmessage = (event) => {
      const newEvent = JSON.parse(event.data);
      // Prepend to list if matches filter
      if (filter === 'all' || newEvent.event_type === filter) {
        setEvents(prev => [newEvent, ...prev].slice(0, 100)); // Keep last 100
      }
    };

    return () => ws.close();
  }, [filter]);

  const formatDate = (dateString) => {
    const d = new Date(dateString);
    return d.toLocaleString();
  };

  const handleExport = async () => {
    try {
      const res = await apiClient.get('/events/export?days=30', {
        responseType: 'blob',
      });
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `neuroguard_events_${Date.now()}.csv`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Export failed:', error);
    }
  };

  const handleDownloadPDF = async (eventId) => {
    try {
      const res = await apiClient.get(`/events/${eventId}/report`, {
        responseType: 'blob',
      });
      const url = window.URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `incident_report_${eventId}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Download failed:', error);
    }
  };

  return (
    <div className="alerts-container">
      <div className="alerts-header">
        <div className="filter-group">
          <button 
            className={`filter-btn ${filter === 'all' ? 'active' : ''}`}
            onClick={() => setFilter('all')}
          >
            All Events
          </button>
          <button 
            className={`filter-btn ${filter === 'stranger' ? 'active-red' : ''}`}
            onClick={() => setFilter('stranger')}
          >
            Strangers
          </button>
          <button 
            className={`filter-btn ${filter === 'recognized' ? 'active-green' : ''}`}
            onClick={() => setFilter('recognized')}
          >
            Recognized
          </button>
        </div>
        
        <button className="btn-secondary" onClick={handleExport}>
          Export CSV
        </button>
      </div>

      <div className="alerts-list glass-card">
        {loading ? (
          <div className="flex-center" style={{ padding: '3rem' }}>Loading events...</div>
        ) : events.length === 0 ? (
          <div className="empty-state">
            <ShieldAlert size={48} className="text-muted" />
            <p>No events found for the selected filter.</p>
          </div>
        ) : (
          <div className="table-responsive">
            <table className="alerts-table">
              <thead>
                <tr>
                  <th>Type</th>
                  <th>Identity</th>
                  <th>Threat Level</th>
                  <th>Time</th>
                  <th>Confidence</th>
                  <th>Details</th>
                </tr>
              </thead>
              <tbody>
                {events.map((evt) => (
                  <tr key={evt.id} className={evt.event_type === 'stranger' ? 'row-danger' : ''}>
                    <td>
                      <div className={`status-badge ${evt.event_type}`}>
                        {evt.event_type === 'stranger' ? <AlertTriangle size={14} /> : <UserCheck size={14} />}
                        {evt.event_type.toUpperCase()}
                      </div>
                    </td>
                    <td className="font-medium">
                      {evt.person_name}
                      {evt.threat_type !== 'none' && (
                        <div style={{ fontSize: '0.8rem', color: 'var(--alert-red)' }}>
                          Weapon: {evt.threat_type.toUpperCase()}
                        </div>
                      )}
                    </td>
                    <td>
                      <div className={`status-badge`} style={{
                        backgroundColor: ['orange', 'red', 'critical'].includes(evt.threat_level) ? 'rgba(255,50,50,0.1)' : 
                                       evt.threat_level === 'yellow' ? 'rgba(255,200,0,0.1)' : 'rgba(0,255,100,0.1)',
                        color: ['orange', 'red', 'critical'].includes(evt.threat_level) ? 'var(--alert-red)' : 
                               evt.threat_level === 'yellow' ? 'var(--warning-yellow)' : 'var(--text-muted)'
                      }}>
                        {evt.threat_level.toUpperCase()}
                      </div>
                    </td>
                    <td className="text-muted flex-center" style={{ justifyContent: 'flex-start', gap: '0.5rem' }}>
                      <Clock size={14} />
                      {formatDate(evt.timestamp)}
                    </td>
                    <td>
                      <div className="confidence-bar">
                        <div 
                          className={`fill ${evt.event_type}`} 
                          style={{ width: `${evt.confidence * 100}%` }}
                        ></div>
                        <span>{(evt.confidence * 100).toFixed(1)}%</span>
                      </div>
                    </td>
                    <td>
                      <button className="btn-icon" onClick={() => setSelectedEvent(evt)}>
                        <Search size={16} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {selectedEvent && (
        <div className="modal-overlay" onClick={() => setSelectedEvent(null)}>
          <div className="modal-content glass-panel" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h2>Event Details</h2>
              <button className="close-btn" onClick={() => setSelectedEvent(null)}>×</button>
            </div>
            <div className="modal-body">
              <div className="detail-grid">
                <div className="detail-item">
                  <label>Type:</label>
                  <span>{selectedEvent.event_type.toUpperCase()}</span>
                </div>
                <div className="detail-item">
                  <label>Identity:</label>
                  <span>{selectedEvent.person_name}</span>
                </div>
                <div className="detail-item">
                  <label>Time:</label>
                  <span>{formatDate(selectedEvent.timestamp)}</span>
                </div>
                <div className="detail-item">
                  <label>Confidence:</label>
                  <span>{(selectedEvent.confidence * 100).toFixed(1)}%</span>
                </div>
                <div className="detail-item">
                  <label>Threat Level:</label>
                  <span style={{
                    color: ['orange', 'red', 'critical'].includes(selectedEvent.threat_level) ? 'var(--alert-red)' : 
                           selectedEvent.threat_level === 'yellow' ? 'var(--warning-yellow)' : 'var(--accent-green)'
                  }}>
                    {selectedEvent.threat_level.toUpperCase()}
                  </span>
                </div>
                <div className="detail-item">
                  <label>Threat Type:</label>
                  <span>{selectedEvent.threat_type.toUpperCase()}</span>
                </div>
                <div className="detail-item">
                  <label>Threat Score:</label>
                  <span>{selectedEvent.threat_score} / 100</span>
                </div>
                {selectedEvent.snn_score !== null && selectedEvent.snn_score !== undefined && (
                  <div className="detail-item">
                    <label>SNN Score:</label>
                    <span>{selectedEvent.snn_score.toFixed(3)}</span>
                  </div>
                )}
                {selectedEvent.cosine_score !== null && selectedEvent.cosine_score !== undefined && (
                  <div className="detail-item">
                    <label>Cosine Score:</label>
                    <span>{selectedEvent.cosine_score.toFixed(3)}</span>
                  </div>
                )}
                {selectedEvent.hybrid_latency_ms !== null && selectedEvent.hybrid_latency_ms !== undefined && (
                  <div className="detail-item">
                    <label>Total Latency:</label>
                    <span>{selectedEvent.hybrid_latency_ms.toFixed(1)} ms</span>
                  </div>
                )}
              </div>
              
              {selectedEvent.snapshot_path && (
                <div className="snapshot-container mt-4">
                  <h4>Snapshot</h4>
                  <div className="text-muted text-sm" style={{ wordBreak: 'break-all' }}>
                    {selectedEvent.snapshot_path}
                  </div>
                </div>
              )}
              
              <div className="modal-actions" style={{ marginTop: '1.5rem', display: 'flex', gap: '1rem', justifyContent: 'flex-end' }}>
                <button 
                  className="btn-primary" 
                  onClick={() => handleDownloadPDF(selectedEvent.id)}
                  style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}
                >
                  <FileText size={16} /> Download Incident PDF
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default AlertsPage;
