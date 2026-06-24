import React from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { 
  LayoutDashboard, 
  Camera, 
  Users, 
  UserPlus, 
  Bell, 
  BarChart2, 
  Database, 
  Settings,
  LogOut,
  ShieldAlert,
  Bot,
  X
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import './Layout.css';

const Sidebar = ({ isOpen, closeSidebar }) => {
  const { logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  const navItems = [
    { name: 'Dashboard', path: '/dashboard', icon: <LayoutDashboard size={20} /> },
    { name: 'Live Surveillance', path: '/surveillance', icon: <Camera size={20} /> },
    { name: 'Alerts', path: '/alerts', icon: <Bell size={20} /> },
    { name: 'Users', path: '/users', icon: <Users size={20} /> },
    { name: 'Register User', path: '/users/register', icon: <UserPlus size={20} /> },
    { name: 'Analytics', path: '/analytics', icon: <BarChart2 size={20} /> },
    { name: 'Threat Insights', path: '/threats', icon: <ShieldAlert size={20} /> },
    { name: 'AI Assistant', path: '/assistant', icon: <Bot size={20} /> },
    { name: 'Models', path: '/models', icon: <Database size={20} /> },
    { name: 'Settings', path: '/settings', icon: <Settings size={20} /> },
  ];

  return (
    <aside className={`sidebar glass-panel ${isOpen ? 'open' : ''}`}>
      <div className="sidebar-header" style={{ justifyContent: 'space-between', width: '100%' }}>
        <div className="logo flex-center">
          <div className="logo-icon"></div>
          <h2>NeuroGuard <span>AI</span></h2>
        </div>
        <button className="mobile-close-btn" onClick={closeSidebar} style={{ display: 'none', background: 'transparent', border: 'none', color: 'var(--text-secondary)', cursor: 'pointer' }}>
          <X size={24} />
        </button>
      </div>
      
      <nav className="sidebar-nav">
        <ul>
          {navItems.map((item) => (
            <li key={item.path}>
              <NavLink 
                to={item.path} 
                className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}
              >
                {item.icon}
                <span>{item.name}</span>
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>
      
      <div className="sidebar-footer">
        <button onClick={handleLogout} className="logout-btn">
          <LogOut size={20} />
          <span>Logout</span>
        </button>
      </div>
    </aside>
  );
};

export default Sidebar;
