import { Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import { AuthProvider, useAuth } from './context/AuthContext';
import { SurveillanceProvider } from './context/SurveillanceContext';

// Layout
import Layout from './components/Layout/Layout';

// Pages
import LoginPage from './pages/LoginPage';
import DashboardPage from './pages/DashboardPage';
import RegisterUserPage from './pages/RegisterUserPage';
import UsersPage from './pages/UsersPage';
import SurveillancePage from './pages/SurveillancePage';
import AlertsPage from './pages/AlertsPage';
import AnalyticsPage from './pages/AnalyticsPage';
import ModelManagementPage from './pages/ModelManagementPage';
import SettingsPage from './pages/SettingsPage';

// Protected Route Wrapper
const ProtectedRoute = ({ children }) => {
  const { isAuthenticated, loading } = useAuth();
  
  if (loading) {
    return <div className="flex-center" style={{ height: '100vh' }}>Loading...</div>;
  }
  
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }
  
  return children;
};

function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      
      <Route path="/" element={
        <ProtectedRoute>
          <Layout />
        </ProtectedRoute>
      }>
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route path="dashboard" element={<DashboardPage />} />
        <Route path="surveillance" element={<SurveillancePage />} />
        <Route path="alerts" element={<AlertsPage />} />
        <Route path="users" element={<UsersPage />} />
        <Route path="users/register" element={<RegisterUserPage />} />
        <Route path="analytics" element={<AnalyticsPage />} />
        <Route path="models" element={<ModelManagementPage />} />
        <Route path="settings" element={<SettingsPage />} />
      </Route>
      
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}

function App() {
  return (
    <AuthProvider>
      <Toaster 
        position="top-right"
        toastOptions={{
          style: {
            background: 'var(--bg-secondary)',
            color: 'var(--text-primary)',
            border: '1px solid var(--glass-border)',
          },
          success: {
            iconTheme: { primary: 'var(--accent-green)', secondary: '#111' },
          },
          error: {
            iconTheme: { primary: 'var(--accent-red)', secondary: '#111' },
          },
        }}
      />
      <SurveillanceProvider>
        <AppRoutes />
      </SurveillanceProvider>
    </AuthProvider>
  );
}

export default App;
