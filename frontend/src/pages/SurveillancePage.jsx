import React, { useRef, useEffect, useState, useCallback } from 'react';
import { Camera, ShieldAlert, Cpu, Activity, UserCheck, Video } from 'lucide-react';
import './SurveillancePage.css';

const SurveillancePage = () => {
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const wsRef = useRef(null);
  const fileInputRef = useRef(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [systemStats, setSystemStats] = useState({ fps: 0, latency: 0 });
  const [faces, setFaces] = useState([]);
  const [threats, setThreats] = useState([]);
  const [streamError, setStreamError] = useState(null);
  const [simulatedVideo, setSimulatedVideo] = useState(null);
  const isWaitingForResponse = useRef(false);
  const audioCtxRef = useRef(null);
  const sirenIntervalRef = useRef(null);

  // Handle video upload simulation
  const handleVideoUpload = (e) => {
    const file = e.target.files[0];
    if (file) {
      const url = URL.createObjectURL(file);
      setSimulatedVideo(url);
      setStreamError(null);
      // Stop current camera if running
      stopCamera();
    }
  };

  // Initialize Camera or Video
  const startCamera = async () => {
    try {
      setIsStreaming(true);
      
      setTimeout(async () => {
        if (simulatedVideo) {
          // Use simulated video
          if (videoRef.current) {
            videoRef.current.srcObject = null;
            videoRef.current.src = simulatedVideo;
            videoRef.current.loop = true;
            videoRef.current.play().catch(e => console.error("Play failed", e));
            setStreamError(null);
          }
        } else {
          // Use real webcam
          try {
            const stream = await navigator.mediaDevices.getUserMedia({
              video: { width: { ideal: 640 }, height: { ideal: 480 }, facingMode: "user" }
            });
            if (videoRef.current) {
              videoRef.current.src = "";
              videoRef.current.srcObject = stream;
              setStreamError(null);
            }
          } catch (err) {
            console.error("Camera access denied or error:", err);
            setStreamError("Failed to access camera. Please check permissions or use Simulation Mode.");
            setIsStreaming(false);
          }
        }
      }, 50);
    } catch (err) {
      console.error("Initialization error:", err);
      setStreamError("Failed to initialize camera.");
      setIsStreaming(false);
    }
  };

  const stopCamera = () => {
    if (videoRef.current) {
      if (videoRef.current.srcObject) {
        const tracks = videoRef.current.srcObject.getTracks();
        tracks.forEach(track => track.stop());
        videoRef.current.srcObject = null;
      } else if (videoRef.current.src) {
        videoRef.current.pause();
        // keep src so it can be resumed
      }
      setIsStreaming(false);
    }
  };

  // Initialize WebSocket
  const connectWebSocket = useCallback(() => {
    const token = localStorage.getItem('token');
    if (!token) return;

    // Determine ws URL based on environment
    let wsUrl;
    if (import.meta.env.VITE_API_URL) {
      const urlObj = new URL(import.meta.env.VITE_API_URL);
      const wsProtocol = urlObj.protocol === 'https:' ? 'wss:' : 'ws:';
      wsUrl = `${wsProtocol}//${urlObj.host}/ws/surveillance?token=${token}`;
    } else {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      wsUrl = `${protocol}//${window.location.host}/ws/surveillance?token=${token}`;
    }
    
    const ws = new WebSocket(wsUrl);
    
    ws.onopen = () => console.log("WebSocket Connected");
    
    ws.onmessage = (event) => {
      isWaitingForResponse.current = false;
      const data = JSON.parse(event.data);
      if (data.error) {
        console.error("WS Error:", data.error);
        return;
      }
      
      
      setFaces(data.results || []);
      setThreats(data.threats || []);
      
      // Siren Trigger Logic
      let shouldPlaySiren = false;
      if (data.results) {
        for (const res of data.results) {
          if (['orange', 'red', 'critical'].includes(res.threat_level) && res.threat_persistence >= 3) {
            shouldPlaySiren = true;
            break;
          }
        }
      }
      
      if (shouldPlaySiren && !sirenIntervalRef.current) {
        playSiren();
      } else if (!shouldPlaySiren && sirenIntervalRef.current) {
        stopSiren();
      }

      setSystemStats({
        fps: data.processing_time_ms > 0 ? (1000 / data.processing_time_ms).toFixed(1) : 0,
        latency: data.processing_time_ms
      });
    };
    
    ws.onclose = () => {
      console.log("WebSocket Disconnected");
      // Auto reconnect after 2 seconds if streaming
      if (isStreaming) {
        setTimeout(connectWebSocket, 2000);
      }
    };
    
    wsRef.current = ws;
  }, [isStreaming]);

  // Main Loop: Send frames to backend
  useEffect(() => {
    let animationFrameId;

    const processFrame = () => {
      if (!isStreaming || !videoRef.current || !canvasRef.current || !wsRef.current) {
        animationFrameId = requestAnimationFrame(processFrame);
        return;
      }

      // Check if video is actually playing
      if (videoRef.current.videoWidth === 0) {
        animationFrameId = requestAnimationFrame(processFrame);
        return;
      }

      // Only send if WS is open AND we are NOT waiting for the previous frame to finish
      if (wsRef.current.readyState === WebSocket.OPEN && !isWaitingForResponse.current) {
        const video = videoRef.current;
        const canvas = canvasRef.current;
        const ctx = canvas.getContext('2d');

        if (canvas.width !== video.videoWidth) {
          canvas.width = video.videoWidth;
          canvas.height = video.videoHeight;
        }

        ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
        const base64Image = canvas.toDataURL('image/jpeg', 0.6); // Reduced quality for speed
        
        isWaitingForResponse.current = true; // Lock until backend responds
        wsRef.current.send(JSON.stringify({
          frame: base64Image,
          frame_id: Date.now()
        }));
      }
      
      animationFrameId = requestAnimationFrame(processFrame);
    };

    if (isStreaming) {
      connectWebSocket();
      processFrame();
    } else if (wsRef.current) {
      wsRef.current.close();
    }

    return () => {
      cancelAnimationFrame(animationFrameId);
    };
  }, [isStreaming, connectWebSocket]);

  // Clean up on unmount
  useEffect(() => {
    return () => {
      stopCamera();
      stopSiren();
    };
  }, []);

  // Audio Context Siren (No external files needed)
  const playSiren = () => {
    if (!audioCtxRef.current) {
      audioCtxRef.current = new (window.AudioContext || window.webkitAudioContext)();
    }
    
    let isHigh = true;
    sirenIntervalRef.current = setInterval(() => {
      if (!audioCtxRef.current) return;
      const osc = audioCtxRef.current.createOscillator();
      const gainNode = audioCtxRef.current.createGain();
      
      osc.type = 'square';
      osc.frequency.setValueAtTime(isHigh ? 800 : 400, audioCtxRef.current.currentTime);
      gainNode.gain.setValueAtTime(0.1, audioCtxRef.current.currentTime);
      gainNode.gain.exponentialRampToValueAtTime(0.01, audioCtxRef.current.currentTime + 0.4);
      
      osc.connect(gainNode);
      gainNode.connect(audioCtxRef.current.destination);
      osc.start();
      osc.stop(audioCtxRef.current.currentTime + 0.4);
      
      isHigh = !isHigh;
    }, 500);
  };

  const stopSiren = () => {
    if (sirenIntervalRef.current) {
      clearInterval(sirenIntervalRef.current);
      sirenIntervalRef.current = null;
    }
  };

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
                <button className="btn-danger" onClick={stopCamera}>Stop Feed</button>
              ) : (
                <>
                  <button className="btn-secondary flex-center" onClick={() => fileInputRef.current?.click()} style={{ gap: '0.5rem', padding: '0.5rem 1rem' }}>
                    <Video size={16} /> Simulate Video
                  </button>
                  <input 
                    type="file" 
                    accept="video/mp4,video/webm" 
                    style={{ display: 'none' }} 
                    ref={fileInputRef} 
                    onChange={handleVideoUpload} 
                  />
                  <button className="btn-primary" onClick={startCamera}>Start Feed</button>
                </>
              )}
            </div>
          </div>
          
          {simulatedVideo && !isStreaming && (
            <div style={{ padding: '0.5rem 1rem', background: 'rgba(0,150,255,0.1)', color: 'var(--accent-blue)', fontSize: '0.875rem' }}>
              Simulated video loaded. Click "Start Feed" to begin.
            </div>
          )}

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
              <div className="video-container">
                <video 
                  ref={videoRef} 
                  autoPlay 
                  playsInline 
                  muted 
                  className="live-video"
                />
                <canvas 
                  ref={canvasRef} 
                  className="hidden-canvas"
                />
                
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
                        <div className="bbox-label" style={{ backgroundColor: ['orange', 'red', 'critical'].includes(threatLevel) ? 'var(--alert-red)' : '' }}>
                          <span className="name">{face.person_name}</span>
                          <span className="conf">{(face.confidence * 100).toFixed(1)}%</span>
                        </div>
                        {threatLevel !== 'green' && threatLevel !== 'yellow' && (
                          <div className="threat-badge" style={{
                            position: 'absolute', top: '-25px', right: 0, background: 'var(--alert-red)', color: 'white', padding: '2px 6px', fontSize: '10px', borderRadius: '4px', fontWeight: 'bold'
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
                        <div className="bbox-label" style={{ backgroundColor: 'var(--alert-red)' }}>
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

