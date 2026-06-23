import React, { useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Camera, Upload, CheckCircle, AlertCircle, Video } from 'lucide-react';
import apiClient from '../api/client';
import toast from 'react-hot-toast';

const RegisterUserPage = () => {
  const [formData, setFormData] = useState({
    name: '',
    employee_id: '',
    department: '',
    role: 'employee'
  });
  
  const [photos, setPhotos] = useState([]);
  const [isCapturing, setIsCapturing] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [simulatedVideo, setSimulatedVideo] = useState(null);
  
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const fileInputRef = useRef(null);
  const navigate = useNavigate();

  const handleInputChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleVideoUpload = (e) => {
    const file = e.target.files[0];
    if (file) {
      const url = URL.createObjectURL(file);
      setSimulatedVideo(url);
      stopCamera();
    }
  };

  const startCamera = async () => {
    try {
      // 1. Force the <video> element to mount FIRST
      setIsCapturing(true);
      
      // 2. Wait a fraction of a second for React to attach the ref
      setTimeout(async () => {
        if (simulatedVideo) {
          if (videoRef.current) {
            videoRef.current.srcObject = null;
            videoRef.current.src = simulatedVideo;
            videoRef.current.loop = true;
            videoRef.current.play().catch(e => console.error(e));
          }
        } else {
          try {
            const stream = await navigator.mediaDevices.getUserMedia({ video: true });
            if (videoRef.current) {
              videoRef.current.src = "";
              videoRef.current.srcObject = stream;
            }
          } catch (err) {
            toast.error('Failed to access camera');
            setIsCapturing(false);
          }
        }
      }, 50);
    } catch (err) {
      toast.error('Failed to initialize camera');
      setIsCapturing(false);
    }
  };

  const stopCamera = () => {
    if (videoRef.current) {
      if (videoRef.current.srcObject) {
        videoRef.current.srcObject.getTracks().forEach(t => t.stop());
        videoRef.current.srcObject = null;
      } else if (videoRef.current.src) {
        videoRef.current.pause();
      }
      setIsCapturing(false);
    }
  };

  const capturePhoto = () => {
    if (photos.length >= 10) {
      toast.error('Maximum 10 photos allowed');
      return;
    }
    
    const video = videoRef.current;
    const canvas = canvasRef.current;
    
    if (video && canvas) {
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      const ctx = canvas.getContext('2d');
      ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
      
      // Convert to blob
      canvas.toBlob((blob) => {
        if (blob) {
          const file = new File([blob], `capture_${Date.now()}.jpg`, { type: 'image/jpeg' });
          setPhotos(prev => [...prev, file]);
          toast.success(`Captured photo ${photos.length + 1}/10`);
        }
      }, 'image/jpeg', 0.9);
    }
  };

  const removePhoto = (index) => {
    setPhotos(photos.filter((_, i) => i !== index));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (photos.length < 3) {
      toast.error('Please capture at least 3 photos for reliable registration');
      return;
    }
    
    setIsSubmitting(true);
    const data = new FormData();
    data.append('name', formData.name);
    data.append('employee_id', formData.employee_id);
    data.append('department', formData.department);
    data.append('role', formData.role);
    
    photos.forEach(photo => {
      data.append('photos', photo);
    });
    
    try {
      await apiClient.post('/users/register', data, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      });
      toast.success('User registered successfully! SNN retraining recommended.');
      navigate('/users');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Registration failed');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2rem' }}>
      {/* Form Section */}
      <div className="glass-card">
        <h2 style={{ marginBottom: '1.5rem' }}>Personal Information</h2>
        <form id="register-form" onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          <div>
            <label style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--text-secondary)' }}>Full Name</label>
            <input required name="name" type="text" className="glass-input" value={formData.name} onChange={handleInputChange} />
          </div>
          
          <div>
            <label style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--text-secondary)' }}>Employee ID</label>
            <input required name="employee_id" type="text" className="glass-input" value={formData.employee_id} onChange={handleInputChange} />
          </div>
          
          <div>
            <label style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--text-secondary)' }}>Department</label>
            <input required name="department" type="text" className="glass-input" value={formData.department} onChange={handleInputChange} />
          </div>
          
          <div style={{ marginTop: '1rem', padding: '1rem', background: 'rgba(255,170,0,0.1)', border: '1px solid rgba(255,170,0,0.3)', borderRadius: '8px' }}>
            <div style={{ display: 'flex', gap: '0.5rem', color: 'var(--accent-amber)', marginBottom: '0.5rem' }}>
              <AlertCircle size={20} />
              <strong style={{ fontSize: '0.875rem' }}>Biometric Data Policy</strong>
            </div>
            <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              Face encodings are stored purely as 512-dimensional vectors in the local offline database. Raw images are not persistently stored unless involved in a security event.
            </p>
          </div>
          
          <button type="submit" className="btn-primary" disabled={isSubmitting || photos.length < 3} style={{ marginTop: '1rem' }}>
            {isSubmitting ? 'Processing Registration...' : 'Complete Registration'}
          </button>
        </form>
      </div>
      
      {/* Biometric Capture Section */}
      <div className="glass-card" style={{ display: 'flex', flexDirection: 'column' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
          <h2>Biometric Capture</h2>
          <span style={{ fontSize: '0.875rem', color: photos.length >= 3 ? 'var(--accent-green)' : 'var(--accent-amber)' }}>
            {photos.length}/10 Photos (Min 3)
          </span>
        </div>
        
        <div style={{ 
          width: '100%', 
          aspectRatio: '4/3', 
          background: '#000', 
          borderRadius: '8px',
          overflow: 'hidden',
          position: 'relative',
          marginBottom: '1.5rem',
          border: '1px solid var(--glass-border)'
        }}>
          {isCapturing ? (
            <>
              <video ref={videoRef} autoPlay playsInline muted style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
              <canvas ref={canvasRef} style={{ display: 'none' }} />
              <div style={{ position: 'absolute', bottom: '1rem', left: '0', width: '100%', display: 'flex', justifyContent: 'center', gap: '1rem' }}>
                <button className="btn-primary" onClick={capturePhoto} style={{ padding: '0.5rem 2rem', borderRadius: '20px' }}>
                  <Camera size={20} style={{ marginRight: '0.5rem', verticalAlign: 'middle' }} />
                  Capture
                </button>
                <button className="btn-danger" onClick={stopCamera} style={{ borderRadius: '20px' }}>Stop</button>
              </div>
            </>
          ) : (
            <div className="flex-center" style={{ height: '100%', flexDirection: 'column', gap: '1rem' }}>
              <Camera size={48} className="text-muted" />
              <div style={{ display: 'flex', gap: '1rem' }}>
                <button type="button" className="btn-primary" onClick={startCamera}>Start Camera</button>
                <button type="button" className="btn-secondary flex-center" onClick={() => fileInputRef.current?.click()} style={{ gap: '0.5rem' }}>
                  <Video size={16} /> Load Video
                </button>
                <input 
                  type="file" 
                  accept="video/mp4,video/webm" 
                  style={{ display: 'none' }} 
                  ref={fileInputRef} 
                  onChange={handleVideoUpload} 
                />
              </div>
              {simulatedVideo && (
                <div style={{ color: 'var(--accent-blue)', fontSize: '0.875rem' }}>
                  Simulated video loaded. Click "Start Camera".
                </div>
              )}
            </div>
          )}
        </div>
        
        {/* Photo Gallery */}
        <div>
          <h4 style={{ marginBottom: '1rem', fontSize: '0.875rem', color: 'var(--text-secondary)' }}>Captured Samples</h4>
          <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
            {photos.map((photo, i) => (
              <div key={i} style={{ position: 'relative', width: '60px', height: '60px', borderRadius: '4px', overflow: 'hidden' }}>
                <img src={URL.createObjectURL(photo)} alt={`Sample ${i}`} style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                <button 
                  onClick={() => removePhoto(i)}
                  style={{ position: 'absolute', top: 0, right: 0, background: 'rgba(255,0,0,0.7)', color: 'white', padding: '2px 4px', fontSize: '10px' }}
                >
                  ✕
                </button>
              </div>
            ))}
            {photos.length === 0 && (
              <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>No photos captured yet.</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default RegisterUserPage;
