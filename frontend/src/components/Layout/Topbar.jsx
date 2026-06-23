import React from 'react';
import { useLocation } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { useSurveillance } from '../../context/SurveillanceContext';
import { User, Video, VideoOff } from 'lucide-react';
import './Layout.css';

const Topbar = () => {
  const { user } = useAuth();
  const { isStreaming, toggleSurveillance } = useSurveillance();
  const location = useLocation();
  
  // Format the path to a readable title
  const getPageTitle = () => {
    const path = location.pathname.split('/').pop() || 'Dashboard';
    return path.charAt(0).toUpperCase() + path.slice(1).replace('-', ' ');
  };

  return (
    <header className="topbar glass-panel">
      <div className="topbar-left">
        <h1 className="page-title">{getPageTitle()}</h1>
      </div>
      
      <div className="topbar-right">
        <div className="surveillance-toggle" onClick={toggleSurveillance} style={{
          display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer',
          padding: '0.5rem 1rem', borderRadius: '20px',
          background: isStreaming ? 'rgba(34, 197, 94, 0.1)' : 'rgba(255, 255, 255, 0.05)',
          border: `1px solid ${isStreaming ? 'var(--accent-green)' : 'var(--glass-border)'}`,
          transition: 'all 0.3s ease'
        }}>
          {isStreaming ? (
            <>
              <span className="pulse-dot" style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--accent-green)', boxShadow: '0 0 8px var(--accent-green)', animation: 'pulse 2s infinite' }}></span>
              <Video size={16} className="text-green" style={{ color: 'var(--accent-green)' }} />
              <span style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--accent-green)' }}>Surveillance ON</span>
            </>
          ) : (
            <>
              <VideoOff size={16} className="text-muted" />
              <span className="text-muted" style={{ fontSize: '0.85rem', fontWeight: 500 }}>Surveillance OFF</span>
            </>
          )}
        </div>
        
        <div className="user-profile">
          <div className="avatar">
            <User size={20} />
          </div>
          <div className="user-info">
            <span className="user-name">{user?.username || 'Admin'}</span>
            <span className="user-role">{user?.role || 'Administrator'}</span>
          </div>
        </div>
      </div>
    </header>
  );
};

export default Topbar;
