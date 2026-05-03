import axios from 'axios';
import type { AxiosInstance } from 'axios';
import { getApiBase } from '../config';

/**
 * Starlette/FastAPI return 400 for path params that are not valid integers
 * (e.g. /chat/conversations/undefined/insights/safe). Normalize before any request.
 */
export function normalizeConversationId(id: unknown): number | null {
  if (id === null || id === undefined) return null;
  if (typeof id === 'number') {
    if (!Number.isFinite(id) || !Number.isInteger(id) || id < 1) return null;
    return id;
  }
  const s = String(id).trim();
  if (!s || s === 'undefined' || s === 'null' || s === 'NaN') return null;
  const n = parseInt(s, 10);
  if (!Number.isFinite(n) || String(n) !== s) return null;
  if (n < 1) return null;
  return n;
}

class ApiClient {
  private client: AxiosInstance;
  private token: string | null = null;

  constructor(baseURL: string = getApiBase()) {
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

  /**
   * Pre-warm Azure / connection for faster first coach response.
   * Base URL already includes `/api` (see getApiBase); path must be `/chat/v2/warmup` (not `/api/...` twice).
   * No-op without auth token (avoids 401 when hook runs before Clerk sets token).
   */
  async warmupCache(language: string = 'he') {
    if (!this.getToken()) return;
    const lang = language.toLowerCase().startsWith('en') ? 'en' : 'he';
    try {
      await this.client.get('/chat/v2/warmup', { params: { language: lang } });
    } catch (e) {
      console.debug('[API] warmupCache failed (non-fatal)', e);
    }
  }

  /** After a V2 station checkpoint: pause for the day vs continue (shapes next coach turn). */
  async sendStationIntent(conversationId: number, intent: 'pause_here' | 'continue_coaching') {
    const cid = normalizeConversationId(conversationId);
    if (cid === null) throw new Error('Invalid conversation id');
    const response = await this.client.post('/chat/v2/station-intent', {
      conversation_id: cid,
      intent,
    });
    return response.data;
  }

  async getConversations() {
    const response = await this.client.get('/chat/conversations');
    return response.data;
  }

  async getConversation(id: number) {
    const cid = normalizeConversationId(id);
    if (cid === null) throw new Error('Invalid conversation id');
    const response = await this.client.get(`/chat/conversations/${cid}`);
    return response.data;
  }

  async deleteConversation(id: number) {
    const cid = normalizeConversationId(id);
    if (cid === null) throw new Error('Invalid conversation id');
    const response = await this.client.delete(`/chat/conversations/${cid}`);
    return response.data;
  }

  // Insights (cognitive data)
  async getConversationInsights(conversationId: number) {
    const cid = normalizeConversationId(conversationId);
    if (cid === null) {
      return {
        current_stage: 'S0',
        saturation_score: 0.0,
        cognitive_data: {},
        metrics: {},
        exists: false,
      };
    }
    try {
      // Use /insights/safe endpoint - never throws 404, returns empty data instead
      const response = await this.client.get(`/chat/conversations/${cid}/insights/safe`);
      
      // Check if conversation exists
      if (!response.data.exists) {
        console.warn(`[API] Conversation ${cid} not found, returning empty insights`);
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
    const cid = normalizeConversationId(conversationId);
    if (cid === null) throw new Error('Invalid conversation id');
    return `${this.client.defaults.baseURL}/chat/conversations/${cid}/messages`;
  }

  // User Info
  async getCurrentUser() {
    const response = await this.client.get('/users/me', {
      params: { _: Date.now() },
      headers: { 'Cache-Control': 'no-cache', Pragma: 'no-cache' },
    });
    return response.data;
  }

  /** Debug: why admin button is missing (authenticated). */
  async getAdminDiagnosis() {
    const response = await this.client.get('/users/me/admin-diagnosis', {
      params: { _: Date.now() },
      headers: { 'Cache-Control': 'no-cache', Pragma: 'no-cache' },
    });
    return response.data;
  }

  /** One-time promote when server has ADMIN_PROMOTE_SECRET set. */
  async claimAdmin(secret: string) {
    const response = await this.client.post('/users/me/claim-admin', { secret });
    return response.data;
  }

  // Dashboard (profile + stats + recent conversations)
  async getDashboard() {
    const response = await this.client.get('/profile/dashboard');
    return response.data;
  }

  async getBillingOverview() {
    const response = await this.client.get('/billing/overview');
    return response.data;
  }

  async updateProfile(data: { display_name?: string; gender?: string }) {
    await this.client.patch('/profile/me', data);
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
    const cid = normalizeConversationId(conversationId);
    if (cid === null) throw new Error('Invalid conversation id');
    const response = await this.client.get(`/journal/${cid}`);
    return response.data;
  }

  async saveJournal(conversationId: number, content: string) {
    const cid = normalizeConversationId(conversationId);
    if (cid === null) throw new Error('Invalid conversation id');
    const response = await this.client.post(`/journal/${cid}`, { content });
    return response.data;
  }

  // Tools
  async submitToolResponse(conversationId: number, toolType: string, data: any) {
    const cid = normalizeConversationId(conversationId);
    if (cid === null) throw new Error('Invalid conversation id');
    const response = await this.client.post(`/tools/${cid}/submit`, {
      tool_type: toolType,
      data
    });
    return response.data;
  }

  async getToolHistory(conversationId: number) {
    const cid = normalizeConversationId(conversationId);
    if (cid === null) throw new Error('Invalid conversation id');
    const response = await this.client.get(`/tools/${cid}/history`);
    return response.data;
  }

  // Resources (for Resource Library)
  async getResources(phase: string) {
    // TODO: Implement backend endpoint for this
    // For now, return empty array
    return [];
  }

  // Speech - requires auth
  async getSpeechToken(): Promise<{ token: string; region: string }> {
    const response = await this.client.get('/speech/token');
    return response.data;
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

  async getAdminUsers(skip = 0, limit = 50, search?: string) {
    const params = new URLSearchParams({ skip: String(skip), limit: String(limit) });
    if (search?.trim()) params.set('search', search.trim());
    const response = await this.client.get(`/admin/users?${params.toString()}`);
    return response.data;
  }

  async getAdminUserDetail(userId: number) {
    const response = await this.client.get(`/admin/users/${userId}`);
    return response.data;
  }

  // Admin — onboarding email sequences (new-user drip)
  async getOnboardingEmailMeta() {
    const response = await this.client.get('/admin/onboarding-email/meta');
    return response.data;
  }

  async listOnboardingEmailSequences() {
    const response = await this.client.get('/admin/onboarding-email/sequences');
    return response.data;
  }

  async createOnboardingEmailSequence(payload: {
    name: string;
    description?: string | null;
    is_active?: boolean;
    is_default?: boolean;
  }) {
    const response = await this.client.post('/admin/onboarding-email/sequences', payload);
    return response.data;
  }

  async patchOnboardingEmailSequence(
    sequenceId: number,
    payload: Partial<{ name: string; description: string | null; is_active: boolean; is_default: boolean }>,
  ) {
    const response = await this.client.patch(`/admin/onboarding-email/sequences/${sequenceId}`, payload);
    return response.data;
  }

  async deleteOnboardingEmailSequence(sequenceId: number) {
    const response = await this.client.delete(`/admin/onboarding-email/sequences/${sequenceId}`);
    return response.data;
  }

  async createOnboardingEmailStep(
    sequenceId: number,
    payload: {
      delay_after_previous_minutes: number;
      subject: string;
      body_html: string;
      body_plain?: string | null;
      image_urls?: string[];
    },
  ) {
    const response = await this.client.post(`/admin/onboarding-email/sequences/${sequenceId}/steps`, payload);
    return response.data;
  }

  async patchOnboardingEmailStep(
    stepId: number,
    payload: Partial<{
      delay_after_previous_minutes: number;
      subject: string;
      body_html: string;
      body_plain: string | null;
      image_urls: string[];
      sort_order: number;
    }>,
  ) {
    const response = await this.client.patch(`/admin/onboarding-email/steps/${stepId}`, payload);
    return response.data;
  }

  async deleteOnboardingEmailStep(stepId: number) {
    const response = await this.client.delete(`/admin/onboarding-email/steps/${stepId}`);
    return response.data;
  }

  async reorderOnboardingEmailSteps(sequenceId: number, orderedStepIds: number[]) {
    const response = await this.client.put(`/admin/onboarding-email/sequences/${sequenceId}/steps/reorder`, {
      ordered_step_ids: orderedStepIds,
    });
    return response.data;
  }

  async onboardingEmailAiDraft(payload: {
    admin_prompt: string;
    language?: string;
    sequence_id?: number | null;
    step_id?: number | null;
  }) {
    const response = await this.client.post('/admin/onboarding-email/ai/draft-step', payload);
    return response.data;
  }

  async onboardingEmailPreviewStep(
    sequenceId: number,
    stepId: number,
    payload: { sample_display_name: string; sample_email: string },
  ) {
    const response = await this.client.post(
      `/admin/onboarding-email/sequences/${sequenceId}/preview-step/${stepId}`,
      payload,
    );
    return response.data;
  }

  async onboardingEmailTestSend(sequenceId: number, payload: { step_id: number; to_email: string }) {
    const response = await this.client.post(`/admin/onboarding-email/sequences/${sequenceId}/test-send`, payload);
    return response.data;
  }

  async onboardingEmailProcessDue(limit = 50) {
    const response = await this.client.post('/admin/onboarding-email/process-due', {}, { params: { limit } });
    return response.data;
  }
}

export const apiClient = new ApiClient();

