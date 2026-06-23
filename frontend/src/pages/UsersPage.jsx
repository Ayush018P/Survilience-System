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
                  <button className="btn-icon danger" onClick={() => handleDelete(user.id, user.name)}>
                    <Trash2 size={16} />
                  </button>
                </div>
              </div>
              
              <div className="user-card-body">
                <h3>{user.name}</h3>
                <p className="emp-id">{user.employee_id}</p>
                <div className="badge">{user.department}</div>
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
