import { apiGet, apiPost, testBackendConnection as testConnection } from './api';

// Re-export testBackendConnection so it can be imported from auth
export { testConnection as testBackendConnection };


interface User {
  id: string;
  email: string;
  full_name: string;
  created_at: string;
  updated_at: string;
}

interface Token {
  access_token: string;
  user: User;
}

class AuthService {
  private static instance: AuthService;
  private token: string | null = null;
  private user: User | null = null;

  private constructor() {
    // Load token from localStorage on initialization
    this.token = localStorage.getItem('access_token');
    const storedUser = localStorage.getItem('user');
    if (storedUser) {
      this.user = JSON.parse(storedUser);
    }
  }

  public static getInstance(): AuthService {
    if (!AuthService.instance) {
      AuthService.instance = new AuthService();
    }
    return AuthService.instance;
  }

  public getToken(): string | null {
    return this.token;
  }

  public getUser(): User | null {
    return this.user;
  }

  public isAuthenticated(): boolean {
    return this.token !== null && this.user !== null;
  }

  public async login(email: string, password: string): Promise<Token> {
    try {
      const response: Token = await apiPost('/auth/login', { email, password });
      this.token = response.access_token;
      this.user = response.user;
      
      // Store in localStorage
      localStorage.setItem('access_token', response.access_token);
      localStorage.setItem('user', JSON.stringify(response.user));
      
      return response;
    } catch (error) {
      this.token = null;
      this.user = null;
      throw error;
    }
  }

  public async register(email: string, password: string, full_name: string): Promise<Token> {
    try {
      const response: Token = await apiPost('/auth/register', { 
        email, 
        password, 
        full_name 
      });
      this.token = response.access_token;
      this.user = response.user;
      
      // Store in localStorage
      localStorage.setItem('access_token', response.access_token);
      localStorage.setItem('user', JSON.stringify(response.user));
      
      return response;
    } catch (error) {
      throw error;
    }
  }

  public async logout(): Promise<void> {
    try {
      await apiPost('/auth/logout');
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      // Clear local state regardless of API call result
      this.token = null;
      this.user = null;
      localStorage.removeItem('access_token');
      localStorage.removeItem('user');
    }
  }

  public async getCurrentUser(): Promise<User> {
    try {
      const user: User = await apiGet('/auth/me');
      this.user = user;
      localStorage.setItem('user', JSON.stringify(user));
      return user;
    } catch (error) {
      // If getting current user fails, clear auth state
      this.token = null;
      this.user = null;
      localStorage.removeItem('access_token');
      localStorage.removeItem('user');
      throw error;
    }
  }

  public async updateCurrentUser(updates: Partial<User>): Promise<User> {
    try {
      const updatedUser: User = await apiPost('/auth/me', updates);
      this.user = updatedUser;
      localStorage.setItem('user', JSON.stringify(updatedUser));
      return updatedUser;
    } catch (error) {
      throw error;
    }
  }
}

// Export a singleton instance
const authService = AuthService.getInstance();
export default authService;
