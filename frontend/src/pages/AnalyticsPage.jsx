import React, { useState, useEffect, useRef } from 'react';
import { Activity, Zap, Shield, Download } from 'lucide-react';
import {
  AreaChart,
  Area,
  LineChart,
  Line,
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

const AnalyticsPage = () => {
  const [liveEvents, setLiveEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const ws = useRef(null);

  useEffect(() => {
    // 1. Fetch historical events to pre-fill the charts
    const fetchRecentEvents = async () => {
      try {
        const res = await apiClient.get('/events?limit=50');
        const formatted = res.data.events.reverse().map(formatEventData);
        setLiveEvents(formatted);
      } catch (error) {
        console.error('Failed to fetch recent events', error);
      } finally {
        setLoading(false);
      }
    };
    fetchRecentEvents();

    // 2. Connect WebSocket for live updates
    const token = localStorage.getItem('token');
    const wsUrl = import.meta.env.VITE_API_URL 
      ? import.meta.env.VITE_API_URL.replace('http', 'ws') + `/api/events/ws?token=${token}`
      : `ws://${window.location.host}/api/events/ws?token=${token}`;

    ws.current = new WebSocket(wsUrl);

    ws.current.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.event_type) {
          const formatted = formatEventData(data);
          setLiveEvents(prev => {
            const newEvents = [...prev, formatted];
            if (newEvents.length > 50) newEvents.shift(); // Keep last 50
            return newEvents;
          });
        }
      } catch (err) {
        console.error("WS Parse Error", err);
      }
    };

    return () => {
      if (ws.current) ws.current.close();
    };
  }, []);

  const formatEventData = (e) => ({
    time: new Date(e.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
    name: e.person_name || 'Unknown',
    cnnLatency: e.cnn_latency_ms || 0,
    snnLatency: e.snn_latency_ms || 0,
    hybridLatency: e.hybrid_latency_ms || 0,
    stability: e.stability_score || 0,
    confidence: (e.confidence || 0) * 100,
    cnnMACs: e.cnn_macs || 0,
    snnSpikes: e.snn_spikes_ac || 0,
    isSwitch: e.is_identity_switch ? 1 : 0,
    threatConf: (e.threat_confidence || 0) * 100,
    threatPers: e.threat_persistence || 0
  });

  if (loading) {
    return <div className="flex-center" style={{ height: '100%' }}>Loading Telemetry...</div>;
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.25rem' }}>
            <Activity className="text-accent" /> Hybrid AI Telemetry
          </h2>
          <p className="text-muted">Real-time SNN performance and efficiency metrics</p>
        </div>
        <button className="btn-secondary flex-center" style={{ gap: '0.5rem' }}>
          <Download size={16} /> Export Data
        </button>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: '1.5rem' }}>
        
        {/* Latency Comparison */}
        <div className="glass-card" style={{ height: '350px', display: 'flex', flexDirection: 'column' }}>
          <h3 style={{ marginBottom: '1.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Zap size={18} className="text-accent" /> Inference Latency (CNN vs SNN)
          </h3>
          <div style={{ flex: 1, minHeight: 0 }}>
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={liveEvents}>
                <defs>
                  <linearGradient id="colorCnn" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="var(--accent-red)" stopOpacity={0.4}/>
                    <stop offset="95%" stopColor="var(--accent-red)" stopOpacity={0}/>
                  </linearGradient>
                  <linearGradient id="colorSnn" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="var(--accent-green)" stopOpacity={0.4}/>
                    <stop offset="95%" stopColor="var(--accent-green)" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--glass-border)" vertical={false} />
                <XAxis dataKey="time" stroke="var(--text-muted)" fontSize={12} />
                <YAxis stroke="var(--text-muted)" fontSize={12} unit=" ms" />
                <Tooltip 
                  contentStyle={{ backgroundColor: 'var(--bg-secondary)', borderColor: 'var(--glass-border)', color: '#fff', borderRadius: '8px' }}
                  itemStyle={{ color: 'var(--text-primary)' }}
                />
                <Legend />
                <Area type="monotone" dataKey="cnnLatency" name="CNN Latency" stroke="var(--accent-red)" strokeWidth={2} fillOpacity={1} fill="url(#colorCnn)" dot={{ r: 3, strokeWidth: 0 }} activeDot={{ r: 6, stroke: 'var(--bg-card)', strokeWidth: 2 }} />
                <Area type="monotone" dataKey="snnLatency" name="SNN Latency" stroke="var(--accent-green)" strokeWidth={2} fillOpacity={1} fill="url(#colorSnn)" dot={{ r: 3, strokeWidth: 0 }} activeDot={{ r: 6, stroke: 'var(--bg-card)', strokeWidth: 2 }} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Recognition Confidence History */}
        <div className="glass-card" style={{ height: '350px', display: 'flex', flexDirection: 'column' }}>
          <h3 style={{ marginBottom: '1.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Activity size={18} className="text-accent" /> Recognition Confidence History
          </h3>
          <div style={{ flex: 1, minHeight: 0 }}>
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={liveEvents}>
                <defs>
                  <linearGradient id="colorConfidence" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="var(--accent-blue)" stopOpacity={0.8}/>
                    <stop offset="95%" stopColor="var(--accent-blue)" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--glass-border)" vertical={false} />
                <XAxis dataKey="time" stroke="var(--text-muted)" fontSize={12} />
                <YAxis stroke="var(--text-muted)" fontSize={12} domain={[0, 100]} unit="%" />
                <Tooltip 
                  contentStyle={{ backgroundColor: 'var(--bg-secondary)', borderColor: 'var(--glass-border)', color: '#fff', borderRadius: '8px' }}
                />
                <Legend />
                <Area type="monotone" dataKey="confidence" name="AI Confidence (%)" stroke="var(--accent-blue)" strokeWidth={2} fillOpacity={1} fill="url(#colorConfidence)" dot={{ r: 3, strokeWidth: 0 }} activeDot={{ r: 6, stroke: 'var(--bg-card)', strokeWidth: 2 }} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Threat Intelligence Lab */}
        <div className="glass-card" style={{ height: '350px', display: 'flex', flexDirection: 'column' }}>
          <h3 style={{ marginBottom: '1.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Shield size={18} style={{ color: 'var(--alert-red)' }} /> Threat Intelligence Confidence & Persistence
          </h3>
          <div style={{ flex: 1, minHeight: 0 }}>
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={liveEvents}>
                <defs>
                  <linearGradient id="colorThreat" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="var(--alert-red)" stopOpacity={0.4}/>
                    <stop offset="95%" stopColor="var(--alert-red)" stopOpacity={0}/>
                  </linearGradient>
                  <linearGradient id="colorPers" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="var(--warning-yellow)" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="var(--warning-yellow)" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--glass-border)" vertical={false} />
                <XAxis dataKey="time" stroke="var(--text-muted)" fontSize={12} />
                <YAxis yAxisId="left" stroke="var(--text-muted)" fontSize={12} domain={[0, 100]} unit="%" />
                <YAxis yAxisId="right" orientation="right" stroke="var(--text-muted)" fontSize={12} domain={[0, 10]} />
                <Tooltip 
                  contentStyle={{ backgroundColor: 'var(--bg-secondary)', borderColor: 'var(--glass-border)', color: '#fff', borderRadius: '8px' }}
                />
                <Legend />
                <Area yAxisId="left" type="monotone" dataKey="threatConf" name="Threat Confidence (%)" stroke="var(--alert-red)" strokeWidth={2} fillOpacity={1} fill="url(#colorThreat)" dot={{ r: 3, strokeWidth: 0 }} activeDot={{ r: 6, stroke: 'var(--bg-card)', strokeWidth: 2 }} />
                <Area yAxisId="right" type="step" dataKey="threatPers" name="Persistence Frames" stroke="var(--warning-yellow)" strokeWidth={2} fillOpacity={1} fill="url(#colorPers)" dot={{ r: 3, strokeWidth: 0 }} activeDot={{ r: 6, stroke: 'var(--bg-card)', strokeWidth: 2 }} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

      </div>
    </div>
  );
};

export default AnalyticsPage;
