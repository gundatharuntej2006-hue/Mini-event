export type UserRole = 'ORGANIZER' | 'MARSHAL' | 'JUDGE' | 'PUBLIC_PROJECTOR';

export interface User {
  id: string;
  email: string;
  name: string;
  role: UserRole;
  isActive: boolean;
  createdAt: string;
}

export interface AuthResponse {
  accessToken: string;
  tokenType: string;
  user: User;
}

export interface LoginCredentials {
  email: string;
  password: string;
}

export interface RegisterUserInput {
  email: string;
  name: string;
  password: string;
  role: UserRole;
}
