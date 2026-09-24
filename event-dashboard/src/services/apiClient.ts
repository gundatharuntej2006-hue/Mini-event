import { API_CONFIG } from './apiConfig';
import { ApiResponse, ApiError } from '../types';

/**
 * Clean HTTP client for FastAPI endpoints.
 * Handles timeouts, network errors, and structured responses.
 */
/**
 * Clean HTTP client for FastAPI endpoints.
 * Handles timeouts, network errors, and structured responses.
 * Automatically attaches stored JWT Bearer tokens for authenticated staff requests.
 */
class ApiClient {
  private tokenKey = 'event_hq_token';
  private inMemoryToken: string | null = null;

  public setToken(token: string): void {
    this.inMemoryToken = token;
    if (typeof window !== 'undefined' && window.localStorage) {
      window.localStorage.setItem(this.tokenKey, token);
    }
  }

  public getToken(): string | null {
    if (this.inMemoryToken) {
      return this.inMemoryToken;
    }
    if (typeof window !== 'undefined' && window.localStorage) {
      return window.localStorage.getItem(this.tokenKey) || window.localStorage.getItem('auth_token');
    }
    return null;
  }

  public clearToken(): void {
    this.inMemoryToken = null;
    if (typeof window !== 'undefined' && window.localStorage) {
      window.localStorage.removeItem(this.tokenKey);
      window.localStorage.removeItem('auth_token');
    }
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<ApiResponse<T>> {
    const cleanEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
    let url: string;
    if (cleanEndpoint.startsWith(API_CONFIG.apiPrefix) || cleanEndpoint.startsWith('/api/')) {
      url = `${API_CONFIG.baseUrl}${cleanEndpoint}`;
    } else {
      url = `${API_CONFIG.baseUrl}${API_CONFIG.apiPrefix}${cleanEndpoint}`;
    }

    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      Accept: 'application/json',
      ...((options.headers as Record<string, string>) || {}),
    };

    // Attach JWT Bearer token if present and not already provided
    const token = this.getToken();
    if (token && !headers['Authorization'] && !headers['authorization']) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), API_CONFIG.timeoutMs);

    try {
      const response = await fetch(url, {
        ...options,
        headers,
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        let message = response.statusText;
        if (typeof errorData.detail === 'string') {
          message = errorData.detail;
        } else if (Array.isArray(errorData.detail)) {
          message = errorData.detail.map((e: any) => e.msg || JSON.stringify(e)).join(', ');
        } else if (errorData.message) {
          message = errorData.message;
        }

        const apiError: ApiError = {
          status: response.status,
          message,
        };

        if (response.status === 401 && token) {
          if (typeof window !== 'undefined') {
            window.dispatchEvent(new CustomEvent('auth_session_expired', { detail: apiError }));
          }
        }
        throw apiError;
      }

      return await response.json();
    } catch (err: unknown) {
      clearTimeout(timeoutId);
      throw err;
    }
  }

  async get<T>(endpoint: string): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, { method: 'GET' });
  }

  async post<T>(endpoint: string, body: unknown): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, {
      method: 'POST',
      body: JSON.stringify(body),
    });
  }

  async put<T>(endpoint: string, body: unknown): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, {
      method: 'PUT',
      body: JSON.stringify(body),
    });
  }

  async patch<T>(endpoint: string, body: unknown): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, {
      method: 'PATCH',
      body: JSON.stringify(body),
    });
  }

  async delete<T>(endpoint: string): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, { method: 'DELETE' });
  }
}

export const apiClient = new ApiClient();

