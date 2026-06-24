import React, { useState, useEffect } from 'react';
import { ShieldAlert, AlertTriangle, Target, Activity } from 'lucide-react';
import {
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend
} from 'recharts';
import apiClient from '../api/client';
import './ThreatInsightsPage.css';

const ThreatInsightsPage = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchThreats = async () => {
      try {
        const res = await apiClient.get('/analytics/threats?days=7');
        setData(res.data);
      } catch (error) {
        console.error('Failed to fetch threat analytics', error);
      } finally {
        setLoading(false);
      }
    };
    fetchThreats();
  }, []);

  if (loading) {
    return <div className="flex-center" style={{ height: '100%' }}>Loading Threat Intelligence...</div>;
  }

  if (!data) {
    return <div className="flex-center" style={{ height: '100%' }}>Error loading data.</div>;
  }

  const COLORS = ['#ef4444', '#f59e0b', '#3b82f6', '#10b981', '#8b5cf6'];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
      <div>
        <h2 style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.25rem' }}>
          <ShieldAlert className="text-alert" /> Threat Intelligence Dashboard
        </h2>
        <p className="text-muted">Advanced scoring and analytics for anomalous events.</p>
      </div>

      {/* KPI Cards */}
      <div className="threat-kpi-grid">
        <div className="glass-card kpi-card">
          <div className="kpi-icon flex-center" style={{ backgroundColor: 'rgba(239, 68, 68, 0.1)', color: '#ef4444' }}>
            <AlertTriangle size={24} />
          </div>
          <div className="kpi-content">
            <p className="text-muted">High Threats Today</p>
            <h3>{data.high_threat_count_today}</h3>
          </div>
        </div>
        <div className="glass-card kpi-card">
          <div className="kpi-icon flex-center" style={{ backgroundColor: 'rgba(245, 158, 11, 0.1)', color: '#f59e0b' }}>
            <Activity size={24} />
          </div>
          <div className="kpi-content">
            <p className="text-muted">Avg Threat Score</p>
            <h3>{data.average_threat_score.toFixed(1)}</h3>
          </div>
        </div>
        <div className="glass-card kpi-card">
          <div className="kpi-icon flex-center" style={{ backgroundColor: 'rgba(59, 130, 246, 0.1)', color: '#3b82f6' }}>
            <Target size={24} />
          </div>
          <div className="kpi-content">
            <p className="text-muted">Unique Threat Types</p>
            <h3>{data.threats_by_type.length}</h3>
          </div>
        </div>
      </div>

      {/* Charts */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))', gap: '1.5rem' }}>
        {/* Type Breakdown */}
        <div className="glass-card" style={{ height: '350px', display: 'flex', flexDirection: 'column' }}>
          <h3 style={{ marginBottom: '1rem' }}>Threat Distribution (Last 7 Days)</h3>
          <div style={{ flex: 1, minHeight: 0 }}>
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={data.threats_by_type}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={100}
                  paddingAngle={5}
                  dataKey="count"
                  nameKey="threat_type"
                  label
                >
                  {data.threats_by_type.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip 
                  contentStyle={{ backgroundColor: 'var(--bg-secondary)', borderColor: 'var(--glass-border)', color: '#fff' }}
                  itemStyle={{ color: 'var(--text-primary)' }}
                />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Over time */}
        <div className="glass-card" style={{ height: '350px', display: 'flex', flexDirection: 'column' }}>
          <h3 style={{ marginBottom: '1rem' }}>Threat Frequency Over Time</h3>
          <div style={{ flex: 1, minHeight: 0 }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={data.threats_over_time}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--glass-border)" vertical={false} />
                <XAxis dataKey="date" stroke="var(--text-muted)" fontSize={12} />
                <YAxis stroke="var(--text-muted)" fontSize={12} />
                <Tooltip 
                  contentStyle={{ backgroundColor: 'var(--bg-secondary)', borderColor: 'var(--glass-border)', color: '#fff' }}
                  itemStyle={{ color: 'var(--text-primary)' }}
                  cursor={{ fill: 'rgba(255,255,255,0.05)' }}
                />
                <Legend />
                <Bar dataKey="count" name="Threat Count" fill="#ef4444" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Recent High Threats Table */}
      <div className="glass-card">
        <h3 style={{ marginBottom: '1rem' }}>Recent High-Risk Events</h3>
        <div className="table-responsive">
          <table className="data-table">
            <thead>
              <tr>
                <th>Time</th>
                <th>Type</th>
                <th>Identity</th>
                <th>Threat Score</th>
                <th>Confidence</th>
              </tr>
            </thead>
            <tbody>
              {data.recent_high_threats.length === 0 ? (
                <tr>
                  <td colSpan="5" style={{ textAlign: 'center', padding: '2rem' }}>
                    No recent high threats.
                  </td>
                </tr>
              ) : (
                data.recent_high_threats.map((event) => (
                  <tr key={event.id}>
                    <td>{new Date(event.timestamp).toLocaleString()}</td>
                    <td><span className="badge badge-error">{event.threat_type}</span></td>
                    <td>{event.person_name || 'Unknown Stranger'}</td>
                    <td>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <div style={{ flex: 1, height: '6px', background: 'var(--bg-primary)', borderRadius: '3px', overflow: 'hidden' }}>
                          <div style={{ width: `${Math.min(event.threat_score, 100)}%`, background: '#ef4444', height: '100%' }}></div>
                        </div>
                        <span style={{ fontSize: '0.85rem' }}>{event.threat_score}</span>
                      </div>
                    </td>
                    <td>{(event.threat_confidence * 100).toFixed(1)}%</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default ThreatInsightsPage;
