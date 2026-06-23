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
  const [loading, setLoading] = useState(true);

  const fetchAnalytics = async () => {
    try {
      const res = await apiClient.get('/analytics');
      setAnalytics(res.data);
    } catch (error) {
      console.error('Failed to fetch analytics', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAnalytics();
    // Poll every 5 seconds for live dashboard updates
    const interval = setInterval(fetchAnalytics, 5000);
    return () => clearInterval(interval);
  }, []);

  if (loading && !analytics) {
    return <div className="flex-center" style={{ height: '100%' }}>Loading Dashboard...</div>;
  }

  // Safe destructuring with defaults to prevent null crashes
  const {
    system_metrics = { fps: 0, latency_ms: 0, cpu_percent: 0, memory_percent: 0 },
    total_users = 0,
    today_recognized = 0,
    today_strangers = 0,
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
            <h3>Recognized Today</h3>
            <div className="stat-icon bg-green"><Activity size={20} /></div>
          </div>
          <div className="stat-value">{today_recognized}</div>
          <div className="stat-footer">
            <span className="text-green">Active</span>
            <span className="text-muted"> recognitions today</span>
          </div>
        </div>

        <div className="stat-card glass-card">
          <div className="stat-header">
            <h3>Stranger Alerts</h3>
            <div className="stat-icon bg-red"><ShieldAlert size={20} /></div>
          </div>
          <div className="stat-value text-red">{today_strangers}</div>
          <div className="stat-footer">
            <span className="text-muted">Unrecognized faces</span>
          </div>
        </div>

        <div className="stat-card glass-card">
          <div className="stat-header">
            <h3>System Health</h3>
            <div className="stat-icon bg-purple"><Cpu size={20} /></div>
          </div>
          <div className="stat-value">{(system_metrics.fps || 0).toFixed(1)} FPS</div>
          <div className="stat-footer flex-between">
            <span className="text-muted">CPU: {system_metrics.cpu_percent || 0}%</span>
            <span className="text-muted">RAM: {system_metrics.memory_percent || 0}%</span>
          </div>
        </div>
      </div>

      {/* Charts */}
      <div className="charts-grid">
        <div className="chart-card glass-card">
          <h3>Hourly Traffic (Today)</h3>
          <div className="chart-wrapper">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={hourly_traffic}>
                <defs>
                  <linearGradient id="colorCount" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="var(--accent-blue)" stopOpacity={0.8}/>
                    <stop offset="95%" stopColor="var(--accent-blue)" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--glass-border)" vertical={false} />
                <XAxis dataKey="hour" stroke="var(--text-muted)" />
                <YAxis stroke="var(--text-muted)" />
                <Tooltip 
                  contentStyle={{ backgroundColor: 'var(--bg-secondary)', borderColor: 'var(--glass-border)' }}
                  itemStyle={{ color: 'var(--text-primary)' }}
                />
                <Area type="monotone" dataKey="count" name="Detections" stroke="var(--accent-blue)" fillOpacity={1} fill="url(#colorCount)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="system-info-card glass-card">
          <h3>SNN Model Status</h3>
          <div className="model-stats">
            <div className="model-stat-row">
              <span className="label">Recognition Accuracy</span>
              <span className="value text-gradient">{(recognition_accuracy || 0).toFixed(1)}%</span>
            </div>
            <div className="model-stat-row">
              <span className="label">Hybrid Architecture</span>
              <span className="value">SNN + Cosine</span>
            </div>
            <div className="model-stat-row">
              <span className="label">Pipeline Latency</span>
              <span className="value">{system_metrics.latency_ms || 0} ms</span>
            </div>
          </div>
          
          <div className="system-diagram">
            <div className="diagram-node">Camera</div>
            <div className="diagram-arrow">→</div>
            <div className="diagram-node">MTCNN</div>
            <div className="diagram-arrow">→</div>
            <div className="diagram-node">ResNet</div>
            <div className="diagram-arrow">→</div>
            <div className="diagram-node highlight">SNN</div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default DashboardPage;
