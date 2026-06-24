import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { UserPlus, Search, Trash2, Cpu, FileImage } from 'lucide-react';
import apiClient from '../api/client';
import toast from 'react-hot-toast';
import './UsersPage.css';

const UsersPage = () => {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');

  const fetchUsers = async () => {
    try {
      setLoading(true);
      const res = await apiClient.get(`/users${search ? `?search=${search}` : ''}`);
      setUsers(res.data.users);
    } catch (error) {
      toast.error('Failed to load users');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    // Debounce search
    const timer = setTimeout(() => {
      fetchUsers();
    }, 500);
    return () => clearTimeout(timer);
  }, [search]);

  const handleDelete = async (id, name) => {
    if (!window.confirm(`Are you sure you want to delete ${name}? This will remove all their biometric data.`)) {
      return;
    }
    
    try {
      await apiClient.delete(`/users/${id}`);
      toast.success(`${name} deleted successfully`);
      fetchUsers();
    } catch (error) {
      toast.error('Failed to delete user');
    }
  };
  const handleUpdateRisk = async (user) => {
    const newRisk = window.prompt(`Enter new Risk Level (0-100) for ${user.name}:`, user.risk_level || 0);
    if (newRisk === null) return;
    
    const riskInt = parseInt(newRisk);
    if (isNaN(riskInt) || riskInt < 0 || riskInt > 100) {
      toast.error('Risk level must be a number between 0 and 100');
      return;
    }
    
    let reason = user.watchlist_reason;
    if (riskInt >= 30) {
      reason = window.prompt(`Enter reason for elevated risk (Watchlist):`, reason || '');
    } else {
      reason = null;
    }
    
    try {
      await apiClient.put(`/users/${user.id}`, {
        risk_level: riskInt,
        watchlist_reason: reason,
        zone_access_level: user.zone_access_level
      });
      toast.success('Risk profile updated');
      fetchUsers();
    } catch (error) {
      toast.error('Failed to update risk profile');
    }
  };

  return (
    <div className="users-container">
      <div className="users-header">
        <div className="search-bar">
          <Search size={20} className="text-muted" />
          <input 
            type="text" 
            placeholder="Search by name, EMP ID, or department..." 
            className="glass-input"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        
        <Link to="/users/register" className="btn-primary flex-center" style={{ gap: '0.5rem' }}>
          <UserPlus size={20} />
          <span>Register User</span>
        </Link>
      </div>

      <div className="users-grid">
        {loading ? (
          <div className="flex-center" style={{ gridColumn: '1 / -1', padding: '3rem' }}>Loading...</div>
        ) : users.length === 0 ? (
          <div className="empty-state" style={{ gridColumn: '1 / -1' }}>
            <p>No registered users found.</p>
          </div>
        ) : (
          users.map(user => (
            <div key={user.id} className="user-card glass-card">
              <div className="user-card-header">
                <div className="user-photo">
                  {user.photo_path ? (
                    <FileImage size={24} className="text-muted" /> // In real app, serve image via API
                  ) : (
                    <div className="avatar-placeholder">{user.name.charAt(0)}</div>
                  )}
                </div>
                <div className="user-actions">
                  <button className="btn-icon danger" onClick={() => handleDelete(user.id, user.name)} title="Delete User">
                    <Trash2 size={16} />
                  </button>
                </div>
              </div>
              
              <div className="user-card-body">
                <h3>{user.name} {user.risk_level >= 30 && <span className="watchlist-badge">⚠️ Watchlist</span>}</h3>
                <p className="emp-id">{user.employee_id} • Zone: {user.zone_access_level}</p>
                <div className="badge">{user.department}</div>
                
                <div className="risk-section" style={{ marginTop: '1rem', cursor: 'pointer' }} onClick={() => handleUpdateRisk(user)}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', color: '#888' }}>
                    <span>Risk Level: {user.risk_level}/100</span>
                    <span style={{ color: '#00f0ff' }}>Edit</span>
                  </div>
                  <div className="risk-bar" style={{ width: '100%', height: '4px', background: '#333', marginTop: '4px', borderRadius: '2px' }}>
                    <div style={{ width: `${user.risk_level}%`, height: '100%', background: user.risk_level >= 50 ? '#ff3366' : user.risk_level >= 20 ? '#ffaa00' : '#00f0ff', borderRadius: '2px' }}></div>
                  </div>
                  {user.watchlist_reason && <p style={{ fontSize: '0.75rem', color: '#ff3366', marginTop: '4px' }}>Reason: {user.watchlist_reason}</p>}
                </div>
              </div>
              
              <div className="user-card-footer">
                <div className="biometric-stat">
                  <Cpu size={14} className="text-accent" />
                  <span>{user.embedding_count} embeddings</span>
                </div>
                <div className={`status-dot ${user.has_centroid ? 'green' : 'red'}`} title={user.has_centroid ? 'Centroid Generated' : 'Missing Data'}></div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};

export default UsersPage;
