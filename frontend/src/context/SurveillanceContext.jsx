import React, { createContext, useContext, useState, useRef, useEffect, useCallback } from 'react';
import toast from 'react-hot-toast';

const SurveillanceContext = createContext(null);

export const useSurveillance = () => {
  const context = useContext(SurveillanceContext);
  if (!context) {
    throw new Error('useSurveillance must be used within a SurveillanceProvider');
  }
  return context;
};

export const SurveillanceProvider = ({ children }) => {
  // We keep video and canvas in memory. Don't attach to DOM directly here, React gets weird about stream lifecycles.
  const videoRef = useRef(document.createElement('video'));
  const canvasRef = useRef(document.createElement('canvas'));
  const streamRef = useRef(null);
  
  const wsRef = useRef(null);
  const audioCtxRef = useRef(null);
  const sirenIntervalRef = useRef(null);
  const isWaitingForResponse = useRef(false);

  const [isStreaming, setIsStreaming] = useState(false);
  const [systemStats, setSystemStats] = useState({ fps: 0, latency: 0 });
  const [faces, setFaces] = useState([]);
  const [threats, setThreats] = useState([]);
  const [streamError, setStreamError] = useState(null);
  const [lowLightMode, setLowLightMode] = useState(false);

  const stopCamera = useCallback(() => {
    // Hard stop tracks. MediaStream API sometimes leaves the green light on if we just pause.
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
      streamRef.current = null;
    }
    if (videoRef.current) {
      if (videoRef.current.srcObject) {
        const tracks = videoRef.current.srcObject.getTracks();
        tracks.forEach(track => track.stop());
        videoRef.current.srcObject = null;
      }
      videoRef.current.removeAttribute('src');
    }
    setIsStreaming(false);
    stopSiren();
    setFaces([]);
    setThreats([]);
    setSystemStats({ fps: 0, latency: 0 });
    
    // CRITICAL: Reset the response lock, otherwise if we stopped while waiting for a WS frame, 
    // the next session will be permanently deadlocked!
    isWaitingForResponse.current = false; 
  }, []);

  const startCamera = useCallback(async () => {
    try {
      // Small delay to ensure previous tracks are fully dead before asking hardware for a new one
      stopCamera();
      
      setTimeout(async () => {
        try {
          const stream = await navigator.mediaDevices.getUserMedia({
            video: { facingMode: "user" }
          });
          streamRef.current = stream;
          
          if (videoRef.current) {
            videoRef.current.src = "";
            videoRef.current.srcObject = stream;
            // Hack: Safari iOS requires autoplay and muted or it completely blocks the video feed
            // We MUST set these as HTML attributes, not just JS properties, for mobile Safari
            videoRef.current.setAttribute('autoplay', '');
            videoRef.current.setAttribute('muted', '');
            videoRef.current.setAttribute('playsinline', '');
            videoRef.current.autoplay = true;
            videoRef.current.playsInline = true;
            videoRef.current.muted = true;
            
            // On mobile, play() must sometimes be deferred slightly until the stream is ready
            setTimeout(() => {
              videoRef.current.play().catch(e => {
                console.error("Mobile play() blocked:", e);
                // Force play on next user interaction if blocked
                document.body.addEventListener('touchstart', () => {
                  videoRef.current.play().catch(console.error);
                }, { once: true });
              });
            }, 50);
            
            setStreamError(null);
            setIsStreaming(true);
            toast.success("Surveillance Feed Started");
          }
        } catch (err) {
          console.error("Camera access denied or error:", err);
          setStreamError("Failed to access camera. Please check permissions.");
          setIsStreaming(false);
          toast.error("Camera access denied");
        }
      }, 100);
    } catch (err) {
      console.error("Initialization error:", err);
      setStreamError("Failed to initialize camera.");
      setIsStreaming(false);
    }
  }, [stopCamera]);

  const playSiren = useCallback(() => {
    // Browsers block AudioContext unless explicitly triggered by user interaction
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
  }, []);

  const stopSiren = useCallback(() => {
    if (sirenIntervalRef.current) {
      clearInterval(sirenIntervalRef.current);
      sirenIntervalRef.current = null;
    }
  }, []);

  const connectWebSocket = useCallback(() => {
    const token = localStorage.getItem('token');
    if (!token) return;

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
    
    ws.onopen = () => console.log("Global WebSocket Connected");
    
    ws.onmessage = (event) => {
      isWaitingForResponse.current = false;
      const data = JSON.parse(event.data);
      if (data.error) {
        console.error("WS Error:", data.error);
        return;
      }
      
      setFaces(data.results || []);
      setThreats(data.threats || []);
      
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
      console.log("Global WebSocket Disconnected");
      if (isStreaming) {
        // Simple reconnect backoff
        setTimeout(connectWebSocket, 2000);
      }
    };
    
    wsRef.current = ws;
  }, [isStreaming, playSiren, stopSiren]);

  useEffect(() => {
    let animationFrameId;
    let lastFrameTime = 0;
    // TODO: 12 FPS is a sweet spot for bandwidth, but maybe we make this configurable later - Ayush
    const TARGET_FPS = 12; 
    const frameInterval = 1000 / TARGET_FPS;

    const processFrame = (timestamp) => {
      if (!isStreaming || !videoRef.current || !canvasRef.current || !wsRef.current) {
        animationFrameId = requestAnimationFrame(processFrame);
        return;
      }

      if (timestamp - lastFrameTime < frameInterval) {
        animationFrameId = requestAnimationFrame(processFrame);
        return;
      }

      if (videoRef.current.videoWidth === 0) {
        animationFrameId = requestAnimationFrame(processFrame);
        return;
      }

      // Ping-pong style: don't send next frame until backend responds. Stops queue buildup.
      if (wsRef.current.readyState === WebSocket.OPEN && !isWaitingForResponse.current) {
        lastFrameTime = timestamp;
        const video = videoRef.current;
        const canvas = canvasRef.current;
        const ctx = canvas.getContext('2d');

        let drawWidth = video.videoWidth;
        let drawHeight = video.videoHeight;
        
        // Downscale to 640px to prevent 4K mobile cameras from murdering the network
        const MAX = 640;
        if (drawWidth > drawHeight && drawWidth > MAX) {
          drawHeight = Math.round(drawHeight * (MAX / drawWidth));
          drawWidth = MAX;
        } else if (drawHeight > drawWidth && drawHeight > MAX) {
          drawWidth = Math.round(drawWidth * (MAX / drawHeight));
          drawHeight = MAX;
        }

        if (canvas.width !== drawWidth || canvas.height !== drawHeight) {
          canvas.width = drawWidth;
          canvas.height = drawHeight;
        }

        ctx.drawImage(video, 0, 0, drawWidth, drawHeight);
        
        const base64Image = canvas.toDataURL('image/jpeg', 0.5);
        
        isWaitingForResponse.current = true;
        wsRef.current.send(JSON.stringify({
          frame: base64Image,
          frame_id: Date.now(),
          enhance_low_light: lowLightMode
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

  const toggleSurveillance = () => {
    if (isStreaming) {
      stopCamera();
    } else {
      startCamera();
    }
  };

  const value = {
    isStreaming,
    streamError,
    systemStats,
    faces,
    threats,
    videoRef, // Provide ref so UI can attach
    toggleSurveillance,
    startCamera,
    stopCamera,
    lowLightMode,
    setLowLightMode
  };

  return (
    <SurveillanceContext.Provider value={value}>
      {children}
    </SurveillanceContext.Provider>
  );
};
