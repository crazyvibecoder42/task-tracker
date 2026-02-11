'use client';

import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { useRouter } from 'next/navigation';
import { API_BASE } from '@/lib/api';

// User type matching backend UserResponse
export interface User {
  id: number;
  name: string;
  email: string;
  role: 'admin' | 'editor' | 'viewer';
  is_active: boolean;
  email_verified: boolean;
  created_at: string;
}

interface AuthContextType {
  user: User | null;
  loading: boolean;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  hasRole: (role: 'admin' | 'editor' | 'viewer') => boolean;
  refetchUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

// Token management
const TOKEN_KEY = 'access_token';

export const getAccessToken = () => {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem(TOKEN_KEY);
};

export const setAccessToken = (token: string) => {
  if (typeof window === 'undefined') return;
  localStorage.setItem(TOKEN_KEY, token);
};

export const clearAccessToken = () => {
  if (typeof window === 'undefined') return;
  localStorage.removeItem(TOKEN_KEY);
};

export function AuthProvider({ children }: { children: ReactNode }) {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  // Fetch current user from /api/auth/me
  const fetchUser = async () => {
    let token = getAccessToken();

    // If no access token, attempt to refresh first (handles page reload with only refresh cookie)
    if (!token) {
      console.debug('[AuthContext] No access token found, attempting refresh');
      try {
        const refreshResponse = await fetch(`${API_BASE}/api/auth/refresh`, {
          method: 'POST',
          credentials: 'include',
        });

        if (refreshResponse.ok) {
          const { access_token } = await refreshResponse.json();
          setAccessToken(access_token);
          token = access_token;
          console.debug('[AuthContext] Token refreshed successfully');
        } else {
          // No valid refresh token, user is not authenticated
          console.debug('[AuthContext] No valid refresh token, user not authenticated');
          setUser(null);
          setLoading(false);
          return;
        }
      } catch (error) {
        console.error('[AuthContext] Refresh failed:', error);
        setUser(null);
        setLoading(false);
        return;
      }
    }

    try {
      const response = await fetch(`${API_BASE}/api/auth/me`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
        credentials: 'include',
      });

      if (response.ok) {
        const userData = await response.json();
        setUser(userData);
      } else if (response.status === 401) {
        // Token might be expired, try refreshing
        console.debug('[AuthContext] Token expired, attempting refresh');
        try {
          const refreshResponse = await fetch(`${API_BASE}/api/auth/refresh`, {
            method: 'POST',
            credentials: 'include',
          });

          if (refreshResponse.ok) {
            const { access_token } = await refreshResponse.json();
            setAccessToken(access_token);
            console.debug('[AuthContext] Token refreshed, retrying user fetch');

            // Retry fetching user with new token
            const retryResponse = await fetch(`${API_BASE}/api/auth/me`, {
              headers: {
                Authorization: `Bearer ${access_token}`,
              },
              credentials: 'include',
            });

            if (retryResponse.ok) {
              const userData = await retryResponse.json();
              setUser(userData);
            } else {
              // Failed even after refresh
              console.debug('[AuthContext] User fetch failed after refresh, clearing token');
              clearAccessToken();
              setUser(null);
            }
          } else {
            // Refresh failed, clear token
            console.debug('[AuthContext] Token refresh failed, clearing token');
            clearAccessToken();
            setUser(null);
          }
        } catch (refreshError) {
          console.error('[AuthContext] Error during token refresh:', refreshError);
          clearAccessToken();
          setUser(null);
        }
      } else {
        // Other error (not 401)
        console.debug('[AuthContext] Failed to fetch user, clearing token');
        clearAccessToken();
        setUser(null);
      }
    } catch (error) {
      console.error('[AuthContext] Error fetching user:', error);
      clearAccessToken();
      setUser(null);
    } finally {
      setLoading(false);
    }
  };

  // Initialize auth state on mount
  useEffect(() => {
    console.debug('[AuthContext] Initializing auth state');
    fetchUser();
  }, []);

  // Login method
  const login = async (email: string, password: string) => {
    console.debug('[AuthContext] Login attempt for:', email);
    setLoading(true);

    try {
      const response = await fetch(`${API_BASE}/api/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include', // Important for refresh token cookie
        body: JSON.stringify({ email, password }),
      });

      if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Login failed' }));
        throw new Error(error.detail || 'Invalid email or password');
      }

      const data = await response.json();
      setAccessToken(data.access_token);

      // Fetch user info after successful login
      await fetchUser();
      console.info('[AuthContext] Login successful for:', email);
    } catch (error) {
      setLoading(false);
      throw error;
    }
  };

  // Logout method
  const logout = async () => {
    console.debug('[AuthContext] Logout initiated');
    const token = getAccessToken();

    try {
      // Always call logout endpoint to clear refresh token cookie
      // Backend doesn't require authentication for logout (handles broken auth states)
      await fetch(`${API_BASE}/api/auth/logout`, {
        method: 'POST',
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        credentials: 'include',
      });
      console.debug('[AuthContext] Logout endpoint called successfully');
    } catch (error) {
      console.error('[AuthContext] Logout API call failed:', error);
      // Continue with local cleanup even if API call fails
    } finally {
      // Always clear local state regardless of API call success
      clearAccessToken();
      setUser(null);
      console.info('[AuthContext] Logout successful, tokens cleared');

      // CRITICAL: Redirect to login immediately to prevent components from making API calls
      router.push('/login');
    }
  };

  // Check if user has specific role
  const hasRole = (role: 'admin' | 'editor' | 'viewer'): boolean => {
    if (!user) return false;

    const roleHierarchy = {
      admin: 3,
      editor: 2,
      viewer: 1,
    };

    return roleHierarchy[user.role] >= roleHierarchy[role];
  };

  const isAuthenticated = !!user;

  const value: AuthContextType = {
    user,
    loading,
    isAuthenticated,
    login,
    logout,
    hasRole,
    refetchUser: fetchUser,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

// Custom hook to use auth context
export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
