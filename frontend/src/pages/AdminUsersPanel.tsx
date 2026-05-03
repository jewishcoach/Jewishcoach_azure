import React, { useCallback, useEffect, useState } from 'react';
import { useAuth } from '@clerk/clerk-react';
import { apiClient } from '../services/api';

interface AdminUserRow {
  id: number;
  clerk_id: string;
  email: string | null;
  display_name: string | null;
  gender: string | null;
  current_plan: string;
  is_admin: boolean;
  stripe_customer_id: boolean;
  created_at: string | null;
  conversation_count: number;
  message_count: number;
  user_message_count: number;
  assistant_message_count: number;
  estimated_llm_tokens_approx: number;
  last_activity_at: string | null;
}

interface UsersListResponse {
  total: number;
  skip: number;
  limit: number;
  users: AdminUserRow[];
}

export const AdminUsersPanel: React.FC = () => {
  const { getToken } = useAuth();
  const limit = 50;
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<UsersListResponse | null>(null);
  const [draftSearch, setDraftSearch] = useState('');
  const [submittedSearch, setSubmittedSearch] = useState('');
  const [skip, setSkip] = useState(0);
  const [detailId, setDetailId] = useState<number | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailData, setDetailData] = useState<unknown>(null);

  const fetchUsers = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const token = await getToken();
      if (token) apiClient.setToken(token);
      const res = await apiClient.getAdminUsers(skip, limit, submittedSearch || undefined);
      setData(res as UsersListResponse);
    } catch (e: unknown) {
      console.error(e);
      setError(e instanceof Error ? e.message : 'Failed to load users');
      setData(null);
    } finally {
      setLoading(false);
    }
  }, [getToken, skip, limit, submittedSearch]);

  useEffect(() => {
    fetchUsers();
  }, [fetchUsers]);

  const submitSearch = () => {
    setSkip(0);
    setSubmittedSearch(draftSearch.trim());
  };

  const openDetail = async (userId: number) => {
    setDetailId(userId);
    setDetailLoading(true);
    setDetailData(null);
    try {
      const token = await getToken();
      if (token) apiClient.setToken(token);
      const d = await apiClient.getAdminUserDetail(userId);
      setDetailData(d);
    } catch (e: unknown) {
      setDetailData({ error: e instanceof Error ? e.message : 'Failed' });
    } finally {
      setDetailLoading(false);
    }
  };

  const closeDetail = () => {
    setDetailId(null);
    setDetailData(null);
  };

  return (
    <div className="space-y-6">
      <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 text-sm text-amber-950">
        <strong className="font-semibold">LLM usage column</strong> is a rough estimate: sum of stored message
        characters ÷ 4 (user + assistant). It does not match Azure billing or real tokenizer counts.
      </div>

      <div className="bg-white rounded-lg shadow p-4 flex flex-wrap gap-3 items-end">
        <div className="flex-1 min-w-[200px]">
          <label className="block text-xs text-gray-500 mb-1">Search (email, Clerk id, display name)</label>
          <input
            type="text"
            value={draftSearch}
            onChange={(e) => setDraftSearch(e.target.value)}
            className="w-full border rounded px-3 py-2 text-sm"
            placeholder="Search…"
            onKeyDown={(e) => e.key === 'Enter' && submitSearch()}
          />
        </div>
        <button
          type="button"
          onClick={submitSearch}
          className="px-4 py-2 rounded-lg bg-slate-800 text-white text-sm font-medium hover:bg-slate-700"
        >
          Search
        </button>
      </div>

      {error && (
        <div className="bg-red-50 text-red-800 rounded-lg p-4 text-sm border border-red-200">{error}</div>
      )}

      {loading && !data ? (
        <div className="flex justify-center py-16 text-gray-600">Loading users…</div>
      ) : data ? (
        <>
          <div className="text-sm text-gray-600">
            Showing {data.users.length} of {data.total} users (skip {data.skip})
          </div>
          <div className="bg-white rounded-lg shadow overflow-hidden">
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200 text-sm">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">ID</th>
                    <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Name / Email</th>
                    <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Plan</th>
                    <th className="px-3 py-2 text-right text-xs font-medium text-gray-500 uppercase">Chats</th>
                    <th className="px-3 py-2 text-right text-xs font-medium text-gray-500 uppercase">Msgs</th>
                    <th className="px-3 py-2 text-right text-xs font-medium text-gray-500 uppercase">User / Asst</th>
                    <th className="px-3 py-2 text-right text-xs font-medium text-gray-500 uppercase">~Tokens</th>
                    <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Last activity</th>
                    <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase"></th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {data.users.map((u) => (
                    <tr key={u.id} className="hover:bg-gray-50">
                      <td className="px-3 py-2 font-mono text-xs">{u.id}</td>
                      <td className="px-3 py-2 max-w-[220px]">
                        <div className="font-medium text-gray-900 truncate">{u.display_name || '—'}</div>
                        <div className="text-xs text-gray-500 truncate">{u.email || u.clerk_id}</div>
                      </td>
                      <td className="px-3 py-2">
                        <span className="inline-flex px-2 py-0.5 rounded-full text-xs bg-slate-100 text-slate-800">
                          {u.current_plan}
                        </span>
                        {u.is_admin && (
                          <span className="ml-1 text-xs text-purple-700 font-medium">admin</span>
                        )}
                      </td>
                      <td className="px-3 py-2 text-right tabular-nums">{u.conversation_count}</td>
                      <td className="px-3 py-2 text-right tabular-nums">{u.message_count}</td>
                      <td className="px-3 py-2 text-right tabular-nums text-xs text-gray-600">
                        {u.user_message_count} / {u.assistant_message_count}
                      </td>
                      <td className="px-3 py-2 text-right tabular-nums text-xs">
                        {u.estimated_llm_tokens_approx.toLocaleString()}
                      </td>
                      <td className="px-3 py-2 text-xs text-gray-600 whitespace-nowrap">
                        {u.last_activity_at ? new Date(u.last_activity_at).toLocaleString() : '—'}
                      </td>
                      <td className="px-3 py-2">
                        <button
                          type="button"
                          onClick={() => openDetail(u.id)}
                          className="text-blue-600 hover:text-blue-800 font-medium text-xs"
                        >
                          Details
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="flex justify-between items-center">
            <button
              type="button"
              disabled={skip <= 0}
              onClick={() => setSkip(Math.max(0, skip - limit))}
              className="px-4 py-2 rounded border border-gray-300 text-sm disabled:opacity-40"
            >
              Previous
            </button>
            <button
              type="button"
              disabled={!data || skip + data.users.length >= data.total}
              onClick={() => setSkip(skip + limit)}
              className="px-4 py-2 rounded border border-gray-300 text-sm disabled:opacity-40"
            >
              Next
            </button>
          </div>
        </>
      ) : null}

      {detailId !== null && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/50" role="dialog">
          <div className="bg-white rounded-xl shadow-xl max-w-3xl w-full max-h-[85vh] overflow-hidden flex flex-col">
            <div className="flex justify-between items-center px-4 py-3 border-b">
              <h2 className="text-lg font-semibold">User #{detailId}</h2>
              <button type="button" onClick={closeDetail} className="text-gray-500 hover:text-gray-800 text-xl leading-none px-2">
                ×
              </button>
            </div>
            <div className="p-4 overflow-y-auto text-sm font-mono whitespace-pre-wrap break-words">
              {detailLoading ? 'Loading…' : JSON.stringify(detailData, null, 2)}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
