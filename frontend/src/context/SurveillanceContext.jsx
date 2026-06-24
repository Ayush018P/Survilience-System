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
  // We keep video and canvas in memory, but they can be attached to DOM later if needed
  const videoRef = useRef(document.createElement('video'));
  const canvasRef = useRef(document.createElement('canvas'));
  
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

  // Stop Camera
  const stopCamera = useCallback(() => {
    if (videoRef.current) {
      if (videoRef.current.srcObject) {
        const tracks = videoRef.current.srcObject.getTracks();
        tracks.forEach(track => track.stop());
        videoRef.current.srcObject = null;
      } else if (videoRef.current.src) {
        videoRef.current.pause();
      }
    }
    setIsStreaming(false);
    stopSiren();
    setFaces([]);
    setThreats([]);
  }, []);

  // Start Camera
  const startCamera = useCallback(async () => {
    try {
      // Small delay to ensure any previous streams are completely closed
      stopCamera();
      
      setTimeout(async () => {
        try {
          const stream = await navigator.mediaDevices.getUserMedia({
            video: { width: { ideal: 640 }, height: { ideal: 480 }, facingMode: "user" }
          });
          
          if (videoRef.current) {
            videoRef.current.src = "";
            videoRef.current.srcObject = stream;
            // Need to autoPlay the memory video element for frames to render
            videoRef.current.autoplay = true;
            videoRef.current.playsInline = true;
            videoRef.current.muted = true;
            videoRef.current.play().catch(e => console.error(e));
            
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

  // Siren Logic
  const playSiren = useCallback(() => {
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

  // WebSocket
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
      console.log("Global WebSocket Disconnected");
      if (isStreaming) {
        setTimeout(connectWebSocket, 2000);
      }
    };
    
    wsRef.current = ws;
  }, [isStreaming, playSiren, stopSiren]);

  // Main Streaming Loop
  useEffect(() => {
    let animationFrameId;

    const processFrame = () => {
      if (!isStreaming || !videoRef.current || !canvasRef.current || !wsRef.current) {
        animationFrameId = requestAnimationFrame(processFrame);
        return;
      }

      if (videoRef.current.videoWidth === 0) {
        animationFrameId = requestAnimationFrame(processFrame);
        return;
      }

      if (wsRef.current.readyState === WebSocket.OPEN && !isWaitingForResponse.current) {
        const video = videoRef.current;
        const canvas = canvasRef.current;
        const ctx = canvas.getContext('2d');

        if (canvas.width !== video.videoWidth) {
          canvas.width = video.videoWidth;
          canvas.height = video.videoHeight;
        }

        ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
        const base64Image = canvas.toDataURL('image/jpeg', 0.6);
        
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
