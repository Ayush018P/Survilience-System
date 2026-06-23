import React, { useState } from 'react';
import { Settings, Save } from 'lucide-react';
import toast from 'react-hot-toast';

const SettingsPage = () => {
  const [settings, setSettings] = useState({
    recognition_threshold: 0.65,
    snn_weight: 0.6,
    cosine_weight: 0.4,
    min_face_size: 40,
    notification_retention_days: 30
  });

  const handleChange = (e) => {
    setSettings({ ...settings, [e.target.name]: e.target.value });
  };

  const handleSave = (e) => {
    e.preventDefault();
    // In a real app we'd POST this to an API
    toast.success('System settings updated successfully');
  };

  return (
    <div style={{ maxWidth: '800px' }}>
      <h2 style={{ marginBottom: '2rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
        <Settings /> System Configuration
      </h2>

      <form onSubmit={handleSave} style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
        <div className="glass-card">
          <h3 style={{ marginBottom: '1.5rem', color: 'var(--accent-blue)' }}>Hybrid Engine Weights</h3>
          
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem' }}>
            <div>
              <label style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                <span style={{ color: 'var(--text-secondary)' }}>SNN Weight</span>
                <span style={{ color: 'var(--text-primary)' }}>{settings.snn_weight}</span>
              </label>
              <input 
                type="range" 
                name="snn_weight" 
                min="0" max="1" step="0.05" 
                value={settings.snn_weight} 
                onChange={handleChange}
                style={{ width: '100%', accentColor: 'var(--accent-purple)' }}
              />
              <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.5rem' }}>
                Influence of the Spiking Neural Network on final decision.
              </p>
            </div>
            
            <div>
              <label style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                <span style={{ color: 'var(--text-secondary)' }}>Cosine Similarity Weight</span>
                <span style={{ color: 'var(--text-primary)' }}>{settings.cosine_weight}</span>
              </label>
              <input 
                type="range" 
                name="cosine_weight" 
                min="0" max="1" step="0.05" 
                value={settings.cosine_weight} 
                onChange={handleChange}
                style={{ width: '100%', accentColor: 'var(--accent-blue)' }}
              />
            </div>
          </div>
        </div>

        <div className="glass-card">
          <h3 style={{ marginBottom: '1.5rem', color: 'var(--accent-blue)' }}>Detection Parameters</h3>
          
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem' }}>
            <div>
              <label style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--text-secondary)' }}>Recognition Confidence Threshold</label>
              <input 
                type="number" 
                name="recognition_threshold" 
                className="glass-input" 
                step="0.01" 
                min="0" max="1"
                value={settings.recognition_threshold} 
                onChange={handleChange}
              />
              <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.5rem' }}>
                Scores below this trigger a "Stranger" alert.
              </p>
            </div>
            
            <div>
              <label style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--text-secondary)' }}>Minimum Face Size (pixels)</label>
              <input 
                type="number" 
                name="min_face_size" 
                className="glass-input" 
                value={settings.min_face_size} 
                onChange={handleChange}
              />
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '1rem' }}>
          <button type="submit" className="btn-primary flex-center" style={{ gap: '0.5rem' }}>
            <Save size={18} /> Save Configuration
          </button>
        </div>
      </form>
    </div>
  );
};

export default SettingsPage;
