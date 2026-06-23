import React, { useState } from 'react';
import { Cpu, Play, Loader, CheckCircle } from 'lucide-react';
import apiClient from '../api/client';
import toast from 'react-hot-toast';

const ModelManagementPage = () => {
  const [epochs, setEpochs] = useState(50);
  const [lr, setLr] = useState(0.001);
  const [isTraining, setIsTraining] = useState(false);
  const [trainingStatus, setTrainingStatus] = useState(null); // 'queued', 'training', 'completed'

  // In a real app we'd poll /api/train/status
  // For the MVP, since it's synchronous or mocked in background, we just simulate status changes

  const handleTrain = async () => {
    setIsTraining(true);
    setTrainingStatus('training');
    toast.success('Training job queued on Redis');
    
    try {
      const res = await apiClient.post('/train', {
        epochs: parseInt(epochs),
        learning_rate: parseFloat(lr),
        batch_size: 32
      });
      
      // Simulate real-time progress for demo purposes
      // In production, this would be a WebSocket or polling the /api/train/status endpoint
      setTimeout(() => {
        setTrainingStatus('completed');
        setIsTraining(false);
        toast.success('SNN Training completed. New model activated.');
      }, 3000);
      
    } catch (error) {
      toast.error('Failed to start training');
      setIsTraining(false);
      setTrainingStatus(null);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
      <div className="glass-card" style={{ maxWidth: '600px' }}>
        <h2 style={{ marginBottom: '1.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <Cpu className="text-gradient" /> Retrain SNN Model
        </h2>
        
        <p className="text-muted" style={{ marginBottom: '2rem' }}>
          The Spiking Neural Network acts as the classifier for the Hybrid Engine. 
          When new users are registered, retraining the SNN ensures the network recognizes their specific spike signatures.
        </p>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem', marginBottom: '2rem' }}>
          <div>
            <label style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--text-secondary)' }}>Epochs</label>
            <input 
              type="number" 
              className="glass-input" 
              value={epochs} 
              onChange={e => setEpochs(e.target.value)} 
              min="10" 
              max="1000"
              disabled={isTraining}
            />
          </div>
          
          <div>
            <label style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--text-secondary)' }}>Learning Rate</label>
            <input 
              type="number" 
              className="glass-input" 
              value={lr} 
              onChange={e => setLr(e.target.value)} 
              step="0.001"
              disabled={isTraining}
            />
          </div>
        </div>

        <button 
          className="btn-primary" 
          style={{ width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem' }}
          onClick={handleTrain}
          disabled={isTraining}
        >
          {isTraining ? (
            <><Loader className="animate-spin" size={18} /> Training in Progress...</>
          ) : (
            <><Play size={18} /> Start Training Job</>
          )}
        </button>
      </div>
      
      {trainingStatus === 'completed' && (
        <div className="glass-card" style={{ maxWidth: '600px', borderColor: 'var(--accent-green)', background: 'rgba(0,255,136,0.05)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
            <CheckCircle color="var(--accent-green)" size={32} />
            <div>
              <h3 style={{ color: 'var(--accent-green)' }}>Training Completed</h3>
              <p className="text-muted">Model v{Math.floor(Date.now() / 1000)} is now active.</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ModelManagementPage;
