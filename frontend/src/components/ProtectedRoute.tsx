import React, { useEffect, useState } from 'react';
import { Navigate } from 'react-router-dom';
import { useUser } from '@clerk/clerk-react';
import { apiClient } from '../services/api';

interface ProtectedRouteProps {
  children: React.ReactNode;
  role?: 'admin';
}

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ children, role }) => {
  const { user, isLoaded } = useUser();
  const [isAuthorized, setIsAuthorized] = useState<boolean | null>(null);
  const [isChecking, setIsChecking] = useState(true);
  
  useEffect(() => {
    const checkAuthorization = async () => {
      if (!isLoaded) return;
      
      if (!user) {
        setIsAuthorized(false);
        setIsChecking(false);
        return;
      }
      
      if (role === 'admin') {
        try {
          // Check if user has admin privileges via backend
          const userData = await apiClient.getCurrentUser();
          setIsAuthorized(userData.isAdmin);
        } catch (error) {
          console.error('Authorization check failed:', error);
          setIsAuthorized(false);
        }
      } else {
        // No special role required, just logged in
        setIsAuthorized(true);
      }
      
      setIsChecking(false);
    };
    
    checkAuthorization();
  }, [user, isLoaded, role]);
  
  // Still loading user data
  if (!isLoaded || isChecking) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading...</p>
        </div>
      </div>
    );
  }
  
  // Not authorized
  if (!isAuthorized) {
    return <Navigate to="/chat" replace />;
  }
  
  // Authorized
  return <>{children}</>;
};




