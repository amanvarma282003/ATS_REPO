import React, { ReactNode } from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';

interface PrivateRouteProps {
  children: ReactNode;
  allowedRole?: 'CANDIDATE' | 'RECRUITER';
}

const PrivateRoute: React.FC<PrivateRouteProps> = ({ children, allowedRole }) => {
  const { isAuthenticated, user, initializing } = useAuth();

  if (initializing) {
    return <div>Loading...</div>;
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  if (allowedRole && user?.role !== allowedRole) {
    const fallbackPath = user?.role === 'CANDIDATE'
      ? '/candidate/dashboard'
      : user?.role === 'RECRUITER'
        ? '/recruiter/dashboard'
        : '/login';
    return <Navigate to={fallbackPath} replace />;
  }

  return <>{children}</>;
};

export default PrivateRoute;
