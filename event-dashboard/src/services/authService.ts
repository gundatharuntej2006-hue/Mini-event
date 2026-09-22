import { apiClient } from './apiClient';
import { isLiveMode, onAppModeChange } from './apiConfig';
import { User, UserRole, LoginCredentials, RegisterUserInput, AuthResponse } from '../types';

const USER_STORAGE_KEY = 'event_hq_current_user';

class AuthService {
  private currentUser: User | null = null;
  private listeners: Set<(user: User | null) => void> = new Set();

  constructor() {
    this.loadUserFromStorage();

    // Listen for mode changes to ensure mock credentials are never applied to Live mode
    onAppModeChange((mode) => {
      if (mode === 'live') {
        // When in live mode, staff roles (ORGANIZER, MARSHAL, JUDGE) MUST have an active token!
        if (!apiClient.getToken()) {
          if (this.currentUser && ['ORGANIZER', 'MARSHAL', 'JUDGE'].includes(this.currentUser.role)) {
            this.saveUserToStorage(null);
          }
        } else {
          this.fetchMe().catch(() => {});
        }
      } else {
        // When switching back to demo mode, restore default demo user if null
        if (!this.currentUser) {
          this.setDemoUser('ORGANIZER');
        }
      }
    });

    // Listen for global session expiration events dispatched by apiClient on 401
    if (typeof window !== 'undefined') {
      window.addEventListener('auth_session_expired', () => {
        if (isLiveMode()) {
          this.logout();
        }
      });
    }
  }

  private loadUserFromStorage(): void {
    if (typeof window !== 'undefined' && window.localStorage) {
      const stored = window.localStorage.getItem(USER_STORAGE_KEY);
      if (stored) {
        try {
          const parsed = JSON.parse(stored) as User;
          // Security guard: in live mode, staff roles are NEVER trusted without a token!
          if (isLiveMode() && ['ORGANIZER', 'MARSHAL', 'JUDGE'].includes(parsed.role) && !apiClient.getToken()) {
            this.currentUser = null;
            window.localStorage.removeItem(USER_STORAGE_KEY);
          } else {
            this.currentUser = parsed;
          }
        } catch {
          this.currentUser = null;
        }
      }
    }
  }

  public saveUserToStorage(user: User | null): void {
    const isSameUser =
      (!this.currentUser && !user) ||
      (Boolean(this.currentUser) &&
        Boolean(user) &&
        this.currentUser?.id === user?.id &&
        this.currentUser?.role === user?.role &&
        this.currentUser?.email === user?.email &&
        this.currentUser?.name === user?.name);

    this.currentUser = user;
    if (typeof window !== 'undefined' && window.localStorage) {
      if (user) {
        window.localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(user));
      } else {
        window.localStorage.removeItem(USER_STORAGE_KEY);
      }
    }
    if (!isSameUser) {
      this.notifyListeners();
    }
  }

  private notifyListeners(): void {
    this.listeners.forEach((listener) => {
      try {
        listener(this.currentUser);
      } catch (err) {
        console.error('Auth listener error:', err);
      }
    });
  }

  public subscribe(listener: (user: User | null) => void): () => void {
    this.listeners.add(listener);
    listener(this.currentUser);
    return () => {
      this.listeners.delete(listener);
    };
  }

  public getCurrentUser(): User | null {
    // In Live Mode, staff roles strictly require a valid Bearer token
    if (isLiveMode() && this.currentUser && ['ORGANIZER', 'MARSHAL', 'JUDGE'].includes(this.currentUser.role)) {
      if (!apiClient.getToken()) {
        return null;
      }
    }
    return this.currentUser;
  }

  public isAuthenticated(): boolean {
    return !!apiClient.getToken() && !!this.currentUser;
  }

  public hasRole(requiredRoles: UserRole[]): boolean {
    const user = this.getCurrentUser();
    if (!user) return false;
    return requiredRoles.includes(user.role);
  }

  public isOrganizer(): boolean {
    return this.getCurrentUser()?.role === 'ORGANIZER';
  }

  public isMarshal(): boolean {
    return this.getCurrentUser()?.role === 'MARSHAL';
  }

  public isJudge(): boolean {
    return this.getCurrentUser()?.role === 'JUDGE';
  }

  public isPublicProjector(): boolean {
    return this.getCurrentUser()?.role === 'PUBLIC_PROJECTOR';
  }

  /**
   * Log in via FastAPI backend /auth/login
   */
  public async login(credentials: LoginCredentials): Promise<User> {
    try {
      const response = await apiClient.post<AuthResponse>('/auth/login', credentials);
      if (!response.success || !response.data) {
        throw new Error(response.message || 'Login failed');
      }

      const token = (response.data as any).accessToken || (response.data as any).access_token;
      const user = response.data.user;
      if (!token) {
        throw new Error('Server response did not contain access token');
      }
      apiClient.setToken(token);
      this.saveUserToStorage(user);
      return user;
    } catch (err: unknown) {
      const apiErr = err as { message?: string; detail?: string };
      throw new Error(apiErr.detail || apiErr.message || 'Invalid email or password');
    }
  }

  /**
   * Fetch latest profile from backend /auth/me
   */
  public async fetchMe(): Promise<User | null> {
    const token = apiClient.getToken();
    if (!token) {
      if (isLiveMode() && this.currentUser && ['ORGANIZER', 'MARSHAL', 'JUDGE'].includes(this.currentUser.role)) {
        this.saveUserToStorage(null);
      }
      return null;
    }

    try {
      const response = await apiClient.get<User>('/auth/me');
      if (response.success && response.data) {
        this.saveUserToStorage(response.data);
        return response.data;
      }
      return null;
    } catch {
      // If token is invalid or expired, clear it
      this.logout();
      return null;
    }
  }

  /**
   * Register a new privileged user (Organizer only)
   */
  public async registerUser(input: RegisterUserInput): Promise<User> {
    const response = await apiClient.post<User>('/auth/register', input);
    if (!response.success || !response.data) {
      throw new Error(response.message || 'Registration failed');
    }
    return response.data;
  }

  /**
   * Log out and clear stored session
   */
  public logout(): void {
    apiClient.clearToken();
    this.saveUserToStorage(null);
  }

  /**
   * Set a demo profile for local offline / demo testing
   */
  public setDemoUser(role: UserRole = 'ORGANIZER'): User {
    const demoUser: User = {
      id: `demo-${role.toLowerCase()}`,
      name:
        role === 'ORGANIZER'
          ? 'Lead Organizer'
          : role === 'MARSHAL'
          ? 'Operations Marshal'
          : role === 'JUDGE'
          ? 'Faculty Judge'
          : 'Projector Display',
      email: `${role.toLowerCase()}@bmsit.in`,
      role,
      isActive: true,
      createdAt: new Date().toISOString(),
    };
    this.saveUserToStorage(demoUser);
    return demoUser;
  }

  /**
   * Explicitly set public projector spectator mode (unauthenticated read-only)
   */
  public setProjectorView(): User {
    apiClient.clearToken();
    const projectorUser: User = {
      id: 'usr-public-projector',
      name: 'Public Projector Display',
      email: 'projector@bmsit.in',
      role: 'PUBLIC_PROJECTOR',
      isActive: true,
      createdAt: new Date().toISOString(),
    };
    this.saveUserToStorage(projectorUser);
    return projectorUser;
  }
}

export const authService = new AuthService();
