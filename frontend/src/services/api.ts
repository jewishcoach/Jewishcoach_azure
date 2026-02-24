import axios from 'axios';
import type { AxiosInstance } from 'axios';

class ApiClient {
  private client: AxiosInstance;
  private token: string | null = null;

  constructor(baseURL: string = import.meta.env.VITE_API_URL || 'http://localhost:8000/api') {
    console.log('🔧 [API CLIENT] Initializing with baseURL:', baseURL);
    console.log('🔧 [API CLIENT] VITE_API_URL env:', import.meta.env.VITE_API_URL);
    
    this.client = axios.create({ 
      baseURL,
      withCredentials: true, // Enable CORS credentials
    });
    
    // Add token to every request
    this.client.interceptors.request.use((config) => {
      if (this.token) {
        config.headers.Authorization = `Bearer ${this.token}`;
      }
      return config;
    });
  }

  setToken(token: string) {
    this.token = token;
  }

  clearToken() {
    this.token = null;
  }

  getToken(): string | null {
    return this.token;
  }

  // Conversations
  async createConversation() {
    const response = await this.client.post('/chat/conversations');
    return response.data;
  }

  /** Pre-warm prompt cache for faster first response. Call when starting new chat. */
  async warmupCache() {
    try {
      await this.client.get('/chat/v2/warmup');
    } catch {
      // Ignore - warmup is best-effort
    }
  }

  async getConversations() {
    const response = await this.client.get('/chat/conversations');
    return response.data;
  }

  async getConversation(id: number) {
    const response = await this.client.get(`/chat/conversations/${id}`);
    return response.data;
  }

  async deleteConversation(id: number) {
    const response = await this.client.delete(`/chat/conversations/${id}`);
    return response.data;
  }

  // Insights (cognitive data)
  async getConversationInsights(conversationId: number) {
    try {
      // Use /insights/safe endpoint - never throws 404, returns empty data instead
      const response = await this.client.get(`/chat/conversations/${conversationId}/insights/safe`);
      
      // Check if conversation exists
      if (!response.data.exists) {
        console.warn(`[API] Conversation ${conversationId} not found, returning empty insights`);
        return {
          current_stage: 'S0',
          saturation_score: 0.0,
          cognitive_data: {},
          metrics: {},
          exists: false
        };
      }
      
      return response.data;
    } catch (error) {
      console.error('[API] Error fetching insights:', error);
      // Return empty structure on error to prevent UI crashes
      return {
        current_stage: 'S0',
        saturation_score: 0.0,
        cognitive_data: {},
        metrics: {},
        exists: false,
        error: true
      };
    }
  }

  // Messages (streaming handled separately in useChat)
  getMessageStreamUrl(conversationId: number) {
    return `${this.client.defaults.baseURL}/chat/conversations/${conversationId}/messages`;
  }

  // User Info
  async getCurrentUser() {
    const response = await this.client.get('/users/me');
    return response.data;
  }

  // User Preferences
  async getUserPreferences() {
    const response = await this.client.get('/users/me/preferences');
    return response.data;
  }

  async updateUserPreferences(prefs: { voice_gender?: string; voice_language?: string }) {
    const response = await this.client.patch('/users/me/preferences', prefs);
    return response.data;
  }

  // Journal
  async getJournal(conversationId: number) {
    const response = await this.client.get(`/journal/${conversationId}`);
    return response.data;
  }

  async saveJournal(conversationId: number, content: string) {
    const response = await this.client.post(`/journal/${conversationId}`, { content });
    return response.data;
  }

  // Tools
  async submitToolResponse(conversationId: number, toolType: string, data: any) {
    const response = await this.client.post(`/tools/${conversationId}/submit`, {
      tool_type: toolType,
      data
    });
    return response.data;
  }

  async getToolHistory(conversationId: number) {
    const response = await this.client.get(`/tools/${conversationId}/history`);
    return response.data;
  }

  // Resources (for Resource Library)
  async getResources(phase: string) {
    // TODO: Implement backend endpoint for this
    // For now, return empty array
    return [];
  }

  // Admin Endpoints
  async getAdminFlags(resolved?: boolean, severity?: string, issueType?: string) {
    const params = new URLSearchParams();
    if (resolved !== undefined) params.append('resolved', String(resolved));
    if (severity) params.append('severity', severity);
    if (issueType) params.append('issue_type', issueType);
    
    const response = await this.client.get(`/admin/flags?${params.toString()}`);
    return response.data;
  }

  async getAdminStats() {
    const response = await this.client.get('/admin/stats');
    return response.data;
  }

  async resolveFlag(flagId: number) {
    const response = await this.client.patch(`/admin/flags/${flagId}/resolve`);
    return response.data;
  }

  async getFlagDetails(flagId: number) {
    const response = await this.client.get(`/admin/flags/${flagId}`);
    return response.data;
  }
}

export const apiClient = new ApiClient();

