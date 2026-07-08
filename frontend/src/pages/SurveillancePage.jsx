import React, { useEffect, useRef, useState } from 'react';
import { Camera, ShieldAlert, Cpu, Activity, UserCheck, Moon } from 'lucide-react';
import { useSurveillance } from '../context/SurveillanceContext';
import './SurveillancePage.css';

const SurveillancePage = () => {
  const { 
    isStreaming, 
    streamError, 
    systemStats, 
    faces, 
    threats, 
    videoRef, 
    toggleSurveillance,
    lowLightMode,
    setLowLightMode
  } = useSurveillance();

  const [isMirrored, setIsMirrored] = useState(true);
  const videoContainerRef = useRef(null);

  // When streaming is on, attach the global video element to our local container
  useEffect(() => {
    const container = videoContainerRef.current;
    const video = videoRef.current;
    
    if (isStreaming && container && video) {
      // Avoid reparenting if it's already there
      if (!container.contains(video)) {
        container.innerHTML = '';
        container.appendChild(video);
        video.className = 'live-video';
      }
    }
    
    // Cleanup: When navigating away from this page, remove the video node from the DOM 
    // so it doesn't get stuck in a detached React tree state
    return () => {
      if (container && video && container.contains(video)) {
        container.removeChild(video);
      }
    };
  }, [isStreaming, videoRef]);

  return (
    <div className="surveillance-container">
      <div className="video-section">
        <div className="video-card glass-card">
          <div className="video-header">
            <div className="flex-center" style={{ gap: '0.5rem' }}>
              <div className={`status-dot ${isStreaming ? 'active' : ''}`}></div>
              <h3>Camera Feed 01 (Main Entrance)</h3>
            </div>
            <div className="video-controls" style={{ display: 'flex', gap: '0.5rem' }}>
              {isStreaming ? (
                <button className="btn-danger" onClick={toggleSurveillance}>Stop Feed</button>
              ) : (
                <button className="btn-primary" onClick={toggleSurveillance}>Start Feed</button>
              )}
              <button 
                className={`btn-secondary ${lowLightMode ? 'active-night' : ''}`} 
                onClick={() => setLowLightMode(!lowLightMode)}
                style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', backgroundColor: lowLightMode ? '#222' : '', color: lowLightMode ? '#00f0ff' : '' }}
              >
                <Moon size={16} /> Night Vision
              </button>
              <button 
                className={`btn-secondary ${isMirrored ? 'active' : ''}`} 
                onClick={() => setIsMirrored(!isMirrored)}
                style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', backgroundColor: isMirrored ? 'rgba(59, 130, 246, 0.2)' : '', color: isMirrored ? '#60a5fa' : '' }}
              >
                Mirror
              </button>
            </div>
          </div>

          <div className="video-wrapper">
            {streamError ? (
              <div className="video-placeholder error">
                <ShieldAlert size={48} />
                <p>{streamError}</p>
              </div>
            ) : !isStreaming ? (
              <div className="video-placeholder">
                <Camera size={48} />
                <p>Camera offline. Click 'Start Feed' to connect.</p>
              </div>
            ) : (
              <div className="video-container" style={{ transform: isMirrored ? 'scaleX(-1)' : 'none' }}>
                {/* The global video element gets injected here */}
                <div ref={videoContainerRef} style={{ width: '100%', height: '100%' }}></div>
                
                {/* Bounding Boxes Overlay */}
                <div className="overlay-container">
                  {/* Face Boxes */}
                  {faces.map((face, idx) => {
                    const vW = videoRef.current?.videoWidth || 640;
                    const vH = videoRef.current?.videoHeight || 480;
                    
                    const left = (face.bbox.x1 / vW) * 100;
                    const top = (face.bbox.y1 / vH) * 100;
                    const width = ((face.bbox.x2 - face.bbox.x1) / vW) * 100;
                    const height = ((face.bbox.y2 - face.bbox.y1) / vH) * 100;
                    
                    const isStranger = face.is_stranger;
                    const threatLevel = face.threat_level;
                    
                    return (
                      <div 
                        key={`face-${idx}`}
                        className={`bbox ${isStranger ? 'stranger' : 'recognized'}`}
                        style={{
                          left: `${left}%`,
                          top: `${top}%`,
                          width: `${width}%`,
                          height: `${height}%`,
                          borderColor: ['orange', 'red', 'critical'].includes(threatLevel) ? 'var(--alert-red)' : ''
                        }}
                      >
                        <div className="bbox-label" style={{ 
                          backgroundColor: ['orange', 'red', 'critical'].includes(threatLevel) ? 'var(--alert-red)' : '',
                          transform: isMirrored ? 'scaleX(-1)' : 'none'
                        }}>
                          <span className="name">{face.person_name}</span>
                          <span className="conf">{(face.confidence * 100).toFixed(1)}%</span>
                        </div>
                        {threatLevel !== 'green' && threatLevel !== 'yellow' && (
                          <div className="threat-badge" style={{
                            position: 'absolute', top: '-25px', right: 0, background: 'var(--alert-red)', color: 'white', padding: '2px 6px', fontSize: '10px', borderRadius: '4px', fontWeight: 'bold',
                            transform: isMirrored ? 'scaleX(-1)' : 'none'
                          }}>
                            {threatLevel.toUpperCase()} THREAT
                          </div>
                        )}
                      </div>
                    );
                  })}
                  
                  {/* Threat Object Boxes */}
                  {threats.map((threat, idx) => {
                    const vW = videoRef.current?.videoWidth || 640;
                    const vH = videoRef.current?.videoHeight || 480;
                    
                    const left = (threat.bbox.x1 / vW) * 100;
                    const top = (threat.bbox.y1 / vH) * 100;
                    const width = ((threat.bbox.x2 - threat.bbox.x1) / vW) * 100;
                    const height = ((threat.bbox.y2 - threat.bbox.y1) / vH) * 100;
                    
                    return (
                      <div 
                        key={`threat-${idx}`}
                        className="bbox threat-object"
                        style={{
                          left: `${left}%`,
                          top: `${top}%`,
                          width: `${width}%`,
                          height: `${height}%`,
                          borderColor: 'var(--alert-red)',
                          borderStyle: 'dashed'
                        }}
                      >
                        <div className="bbox-label" style={{ 
                          backgroundColor: 'var(--alert-red)',
                          transform: isMirrored ? 'scaleX(-1)' : 'none'
                        }}>
                          <span className="name">WEAPON: {threat.label.toUpperCase()}</span>
                          <span className="conf">{(threat.confidence * 100).toFixed(1)}%</span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
      
      <div className="side-panel">
        <div className="glass-card stat-panel">
          <h3>Telemetry</h3>
          <div className="telemetry-grid">
            <div className="t-item">
              <Cpu size={18} className="text-muted" />
              <div>
                <p className="label">Processing Latency</p>
                <p className="value">{typeof systemStats.latency === 'number' ? systemStats.latency.toFixed(1) : systemStats.latency} ms</p>
              </div>
            </div>
            <div className="t-item">
              <Activity size={18} className="text-muted" />
              <div>
                <p className="label">Pipeline FPS</p>
                <p className="value">{systemStats.fps}</p>
              </div>
            </div>
          </div>
        </div>

        <div className="glass-card recent-detections">
          <h3>Live Detections</h3>
          <div className="detection-list">
            {faces.length === 0 && isStreaming && (
              <p className="text-muted text-center py-4">No faces in frame</p>
            )}
            
            {faces.map((face, i) => (
              <div key={i} className={`detection-item ${face.is_stranger ? 'danger' : 'safe'}`}>
                <div className="icon">
                  {face.is_stranger ? <ShieldAlert size={20} /> : <UserCheck size={20} />}
                </div>
                <div className="info">
                  <p className="name">{face.person_name}</p>
                  <p className="scores">
                    <span title="Hybrid Confidence">C: {(face.confidence * 100).toFixed(0)}%</span>
                    <span title="Threat Level" style={{ 
                      color: ['orange', 'red', 'critical'].includes(face.threat_level) ? 'var(--alert-red)' : 
                             face.threat_level === 'yellow' ? 'var(--warning-yellow)' : 'var(--text-muted)' 
                    }}>
                      T: {face.threat_level.toUpperCase()}
                    </span>
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default SurveillancePage;
