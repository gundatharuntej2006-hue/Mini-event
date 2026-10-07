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
    options: RequestInit = {},
    retryCount = 0
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

    const timeoutErrorMessage = `Request timed out after ${API_CONFIG.timeoutMs}ms. The server may be waking from sleep.`;
    const controller = new AbortController();
    let isTimeoutTriggered = false;

    const timeoutId = setTimeout(() => {
      isTimeoutTriggered = true;
      try {
        controller.abort(new Error(timeoutErrorMessage));
      } catch {
        controller.abort();
      }
    }, API_CONFIG.timeoutMs);

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

        // Retry 5xx server gateway/boot errors (e.g. 502/503/504 Bad Gateway during Render container startup)
        // Never retry 4xx client errors (400, 401, 403, 404, 422, etc.)
        if (retryCount < 1 && response.status >= 500) {
          await new Promise((resolve) => setTimeout(resolve, 1500));
          return this.request<T>(endpoint, options, retryCount + 1);
        }

        throw apiError;
      }

      return await response.json();
    } catch (err: unknown) {
      clearTimeout(timeoutId);

      // Normalize timeout aborts so they never display the unhelpful "signal is aborted without reason"
      let effectiveError = err;
      const isAbortError =
        isTimeoutTriggered ||
        (err instanceof DOMException && err.name === 'AbortError') ||
        (err instanceof Error && err.name === 'AbortError') ||
        (err instanceof Error && (err.message.includes('aborted') || err.message.includes('abort')));

      if (isAbortError) {
        effectiveError = new Error(timeoutErrorMessage);
      }

      // Check if transient network/connection failure or timeout and retry once
      const isNetworkOrTimeout =
        isAbortError ||
        (err instanceof TypeError && (err.message.includes('fetch') || err.message.includes('NetworkError') || err.message.includes('Failed to fetch')));

      if (retryCount < 1 && isNetworkOrTimeout) {
        await new Promise((resolve) => setTimeout(resolve, 1500));
        return this.request<T>(endpoint, options, retryCount + 1);
      }

      throw effectiveError;
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

