import React, { useState, useEffect } from 'react';
import apiClient from '../api/client';
import { Activity, Users, ShieldAlert, Cpu } from 'lucide-react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import './DashboardPage.css';

const DashboardPage = () => {
  const [analytics, setAnalytics] = useState(null);
  const [recentEvents, setRecentEvents] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchDashboardData = async () => {
    try {
      const [analyticsRes, eventsRes] = await Promise.all([
        apiClient.get('/analytics'),
        apiClient.get('/events?limit=5')
      ]);
      setAnalytics(analyticsRes.data);
      setRecentEvents(eventsRes.data.events || []);
    } catch (error) {
      console.error('Failed to fetch dashboard data', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
    // Poll every 5 seconds for live dashboard updates
    const interval = setInterval(fetchDashboardData, 5000);
    return () => clearInterval(interval);
  }, []);

  if (loading && !analytics) {
    return <div className="flex-center" style={{ height: '100%' }}>Loading Dashboard...</div>;
  }

  // Safe destructuring with defaults to prevent null crashes
  const {
    system_metrics = { fps: 0, latency_ms: 0, cpu_percent: 0, memory_percent: 0 },
    total_users = 0,
    total_recognized = 0,
    total_strangers = 0,
    recognition_accuracy = 0,
    hourly_traffic = [],
  } = analytics || {};

  return (
    <div className="dashboard-container">
      {/* Stat Cards */}
      <div className="stats-grid">
        <div className="stat-card glass-card">
          <div className="stat-header">
            <h3>Registered Identities</h3>
            <div className="stat-icon bg-blue"><Users size={20} /></div>
          </div>
          <div className="stat-value">{total_users}</div>
          <div className="stat-footer">
            <span className="text-muted">Stored in Offline DB</span>
          </div>
        </div>

        <div className="stat-card glass-card">
          <div className="stat-header">
            <h3>Total Recognized</h3>
            <div className="stat-icon bg-green"><Activity size={20} /></div>
          </div>
          <div className="stat-value">{total_recognized}</div>
          <div className="stat-footer">
            <span className="text-green">Active</span>
            <span className="text-muted"> all-time recognitions</span>
          </div>
        </div>

        <div className="stat-card glass-card">
          <div className="stat-header">
            <h3>Total Stranger Alerts</h3>
            <div className="stat-icon bg-red"><ShieldAlert size={20} /></div>
          </div>
          <div className="stat-value text-red">{total_strangers}</div>
          <div className="stat-footer">
            <span className="text-muted">All-time unverified faces</span>
          </div>
        </div>

        <div className="stat-card glass-card">
          <div className="stat-header">
            <h3>System Status</h3>
            <div className="stat-icon bg-purple"><Cpu size={20} /></div>
          </div>
          <div className="stat-value">{(recognition_accuracy || 0).toFixed(1)}% <span style={{fontSize: '0.875rem', fontWeight: 500, color: 'var(--text-secondary)'}}>Accuracy</span></div>
          <div className="stat-footer flex-between">
            <span className="text-green">Face Rec: Active</span>
            <span className="text-muted">{system_metrics.latency_ms || 0}ms Speed</span>
          </div>
        </div>
      </div>

      {/* Charts */}
      <div className="charts-grid">
        <div className="chart-card glass-card">
          <h3>Activity Overview</h3>
          <div className="chart-wrapper">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={hourly_traffic} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="colorCount" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="var(--accent-blue)" stopOpacity={0.5}/>
                    <stop offset="95%" stopColor="var(--accent-blue)" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--glass-border)" vertical={false} />
                <XAxis dataKey="hour" stroke="var(--text-muted)" tick={{fill: 'var(--text-muted)'}} />
                <YAxis stroke="var(--text-muted)" tick={{fill: 'var(--text-muted)'}} />
                <Tooltip 
                  contentStyle={{ backgroundColor: 'var(--bg-secondary)', borderColor: 'var(--glass-border)', borderRadius: '8px' }}
                  itemStyle={{ color: 'var(--text-primary)' }}
                />
                <Area type="monotone" dataKey="count" name="Activity Level" stroke="var(--accent-blue)" strokeWidth={2} fillOpacity={1} fill="url(#colorCount)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="system-info-card glass-card" style={{ display: 'flex', flexDirection: 'column' }}>
          <h3>Security Timeline</h3>
          <div className="recent-activity-list" style={{ display: 'flex', flexDirection: 'column', paddingLeft: '1rem', overflowY: 'auto' }}>
            {recentEvents.length > 0 ? recentEvents.map((event, idx) => {
              const isThreat = event.threat_level !== 'green' && event.threat_level !== 'yellow';
              return (
              <div key={idx} style={{ 
                position: 'relative', 
                paddingBottom: '1.5rem', 
                paddingLeft: '1.5rem', 
                borderLeft: idx === recentEvents.length - 1 ? 'none' : `2px solid ${isThreat ? 'var(--alert-red)' : 'var(--glass-border)'}` 
              }}>
                <div style={{
                  position: 'absolute',
                  left: '-6px',
                  top: '0',
                  width: '10px',
                  height: '10px',
                  borderRadius: '50%',
                  background: isThreat ? 'var(--alert-red)' : 'var(--accent-blue)',
                  boxShadow: isThreat ? '0 0 10px var(--alert-red)' : 'none'
                }}></div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginTop: '-4px' }}>
                  <div style={{ display: 'flex', flexDirection: 'column' }}>
                    <span style={{ fontWeight: 600, color: isThreat ? 'var(--alert-red)' : 'inherit' }}>
                      {event.threat_type !== 'none' ? `Weapon Detected: ${event.threat_type.toUpperCase()}` : 
                       event.event_type === 'stranger' ? 'Stranger Detected' : event.person_name}
                    </span>
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{new Date(event.timestamp).toLocaleTimeString()}</span>
                    {event.threat_score > 0 && (
                      <span style={{ fontSize: '0.7rem', color: 'var(--warning-yellow)', marginTop: '4px' }}>
                        Threat Score: {event.threat_score}
                      </span>
                    )}
                  </div>
                  <div>
                    <span style={{ padding: '0.2rem 0.6rem', borderRadius: '4px', fontSize: '0.75rem', fontWeight: 500, background: isThreat ? 'rgba(239, 68, 68, 0.15)' : 'rgba(16, 185, 129, 0.15)', color: isThreat ? 'var(--alert-red)' : 'var(--accent-green)' }}>
                      {isThreat ? 'Alert Triggered' : 'Cleared'}
                    </span>
                  </div>
                </div>
              </div>
            )}) : (
              <div className="text-muted text-center mt-4">No recent activity</div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default DashboardPage;
