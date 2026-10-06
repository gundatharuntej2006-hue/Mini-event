import React, { useState, useEffect } from 'react';
import { Navigate } from 'react-router-dom';
import { authService } from '../../services/authService';
import { User } from '../../types';

interface StaffOnlyRouteProps {
  children: React.ReactElement;
}

const STAFF_ROLES = ['ORGANIZER', 'MARSHAL', 'JUDGE', 'ADMIN'];

/**
 * Route guard component that restricts access to authorized tournament staff.
 * If the current user is a public viewer (PUBLIC_PROJECTOR) or unauthenticated,
 * they are automatically redirected to the public Live Scoreboard (/scoreboard).
 */
export function StaffOnlyRoute({ children }: StaffOnlyRouteProps) {
  const [currentUser, setCurrentUser] = useState<User | null>(authService.getCurrentUser());

  useEffect(() => {
    const unsub = authService.subscribe((user) => {
      setCurrentUser(user);
    });
    return () => unsub();
  }, []);

  const isStaff = Boolean(currentUser && STAFF_ROLES.includes(currentUser.role));

  if (!isStaff) {
    return <Navigate to="/scoreboard" replace />;
  }

  return children;
}
