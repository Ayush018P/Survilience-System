import React from 'react';
import { useLocation } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { User } from 'lucide-react';
import './Layout.css';

const Topbar = () => {
  const { user } = useAuth();
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
        <div className="status-indicator">
          <span className="dot pulse-green"></span>
          <span>System Online</span>
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
