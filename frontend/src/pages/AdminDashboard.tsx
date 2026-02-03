import React, { useEffect, useState } from 'react';
import { apiClient } from '../services/api';
import { useAuth } from '@clerk/clerk-react';

interface Flag {
  id: number;
  conversation_id: number;
  conversation_title: string;
  message_id: number;
  message_content: string;
  stage: string;
  issue_type: string;
  reasoning: string;
  severity: string;
  is_resolved: boolean;
  created_at: string;
}

interface Stats {
  total_flags: number;
  unresolved_flags: number;
  by_severity: {
    High: number;
    Medium: number;
    Low: number;
  };
  by_issue_type: {
    Hallucination: number;
    Advice: number;
    'Logic Error': number;
    Methodology: number;
  };
  by_stage: Record<string, number>;
  resolution_rate: number;
}

export const AdminDashboard: React.FC = () => {
  const { getToken } = useAuth();
  const [flags, setFlags] = useState<Flag[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<{
    resolved?: boolean;
    severity?: string;
    issueType?: string;
  }>({});

  useEffect(() => {
    loadData();
  }, [filter]);

  const loadData = async () => {
    try {
      const token = await getToken();
      if (token) {
        apiClient.setToken(token);
      }

      const [flagsData, statsData] = await Promise.all([
        apiClient.getAdminFlags(filter.resolved, filter.severity, filter.issueType),
        apiClient.getAdminStats()
      ]);

      setFlags(flagsData.flags);
      setStats(statsData);
      setLoading(false);
    } catch (error) {
      console.error('Failed to load admin data:', error);
      setLoading(false);
    }
  };

  const handleResolve = async (flagId: number) => {
    try {
      const token = await getToken();
      if (token) {
        apiClient.setToken(token);
      }

      await apiClient.resolveFlag(flagId);
      loadData(); // Refresh data
    } catch (error) {
      console.error('Failed to resolve flag:', error);
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'High':
        return 'bg-red-100 text-red-800 border-red-300';
      case 'Medium':
        return 'bg-yellow-100 text-yellow-800 border-yellow-300';
      case 'Low':
        return 'bg-blue-100 text-blue-800 border-blue-300';
      default:
        return 'bg-gray-100 text-gray-800 border-gray-300';
    }
  };

  const getIssueTypeIcon = (issueType: string) => {
    switch (issueType) {
      case 'Hallucination':
        return '🔮';
      case 'Advice':
        return '💡';
      case 'Logic Error':
        return '⚠️';
      case 'Methodology':
        return '📋';
      default:
        return '❓';
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading admin dashboard...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">Admin Dashboard</h1>
          <p className="text-gray-600 mt-2">Quality Audit & System Monitoring</p>
        </div>

        {/* Stats Cards */}
        {stats && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
            <div className="bg-white rounded-lg shadow p-6">
              <div className="text-sm text-gray-600">Total Flags</div>
              <div className="text-3xl font-bold text-gray-900 mt-2">{stats.total_flags}</div>
            </div>
            <div className="bg-white rounded-lg shadow p-6">
              <div className="text-sm text-gray-600">Unresolved</div>
              <div className="text-3xl font-bold text-red-600 mt-2">{stats.unresolved_flags}</div>
            </div>
            <div className="bg-white rounded-lg shadow p-6">
              <div className="text-sm text-gray-600">Resolution Rate</div>
              <div className="text-3xl font-bold text-green-600 mt-2">{stats.resolution_rate}%</div>
            </div>
            <div className="bg-white rounded-lg shadow p-6">
              <div className="text-sm text-gray-600">High Severity</div>
              <div className="text-3xl font-bold text-red-600 mt-2">{stats.by_severity.High}</div>
            </div>
          </div>
        )}

        {/* Breakdown Charts */}
        {stats && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
            {/* By Severity */}
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="text-lg font-semibold mb-4">By Severity</h3>
              <div className="space-y-3">
                <div>
                  <div className="flex justify-between mb-1">
                    <span className="text-sm text-gray-600">High</span>
                    <span className="text-sm font-semibold text-red-600">{stats.by_severity.High}</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className="bg-red-600 h-2 rounded-full"
                      style={{ width: `${(stats.by_severity.High / stats.total_flags) * 100}%` }}
                    ></div>
                  </div>
                </div>
                <div>
                  <div className="flex justify-between mb-1">
                    <span className="text-sm text-gray-600">Medium</span>
                    <span className="text-sm font-semibold text-yellow-600">{stats.by_severity.Medium}</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className="bg-yellow-600 h-2 rounded-full"
                      style={{ width: `${(stats.by_severity.Medium / stats.total_flags) * 100}%` }}
                    ></div>
                  </div>
                </div>
                <div>
                  <div className="flex justify-between mb-1">
                    <span className="text-sm text-gray-600">Low</span>
                    <span className="text-sm font-semibold text-blue-600">{stats.by_severity.Low}</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className="bg-blue-600 h-2 rounded-full"
                      style={{ width: `${(stats.by_severity.Low / stats.total_flags) * 100}%` }}
                    ></div>
                  </div>
                </div>
              </div>
            </div>

            {/* By Issue Type */}
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="text-lg font-semibold mb-4">By Issue Type</h3>
              <div className="space-y-2">
                {Object.entries(stats.by_issue_type).map(([type, count]) => (
                  <div key={type} className="flex justify-between items-center">
                    <span className="text-sm text-gray-600">{getIssueTypeIcon(type)} {type}</span>
                    <span className="text-sm font-semibold text-gray-900">{count}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Filters */}
        <div className="bg-white rounded-lg shadow p-4 mb-6">
          <div className="flex flex-wrap gap-4">
            <div>
              <label className="text-sm text-gray-600 mr-2">Status:</label>
              <select
                className="border rounded px-3 py-1"
                value={filter.resolved === undefined ? 'all' : filter.resolved ? 'resolved' : 'unresolved'}
                onChange={(e) => {
                  const value = e.target.value;
                  setFilter({
                    ...filter,
                    resolved: value === 'all' ? undefined : value === 'resolved'
                  });
                }}
              >
                <option value="all">All</option>
                <option value="unresolved">Unresolved</option>
                <option value="resolved">Resolved</option>
              </select>
            </div>
            <div>
              <label className="text-sm text-gray-600 mr-2">Severity:</label>
              <select
                className="border rounded px-3 py-1"
                value={filter.severity || 'all'}
                onChange={(e) => {
                  const value = e.target.value;
                  setFilter({ ...filter, severity: value === 'all' ? undefined : value });
                }}
              >
                <option value="all">All</option>
                <option value="High">High</option>
                <option value="Medium">Medium</option>
                <option value="Low">Low</option>
              </select>
            </div>
            <div>
              <label className="text-sm text-gray-600 mr-2">Issue Type:</label>
              <select
                className="border rounded px-3 py-1"
                value={filter.issueType || 'all'}
                onChange={(e) => {
                  const value = e.target.value;
                  setFilter({ ...filter, issueType: value === 'all' ? undefined : value });
                }}
              >
                <option value="all">All</option>
                <option value="Hallucination">Hallucination</option>
                <option value="Advice">Advice</option>
                <option value="Logic Error">Logic Error</option>
                <option value="Methodology">Methodology</option>
              </select>
            </div>
          </div>
        </div>

        {/* Flags Table */}
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">ID</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Stage</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Issue</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Severity</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Reasoning</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Date</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Action</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {flags.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="px-6 py-12 text-center text-gray-500">
                      No flags found. The coach is performing well! 🎉
                    </td>
                  </tr>
                ) : (
                  flags.map((flag) => (
                    <tr key={flag.id} className={flag.is_resolved ? 'bg-gray-50 opacity-60' : ''}>
                      <td className="px-6 py-4 text-sm text-gray-900">{flag.id}</td>
                      <td className="px-6 py-4 text-sm text-gray-900">{flag.stage}</td>
                      <td className="px-6 py-4 text-sm">
                        <span className="inline-flex items-center">
                          {getIssueTypeIcon(flag.issue_type)} <span className="ml-2">{flag.issue_type}</span>
                        </span>
                      </td>
                      <td className="px-6 py-4 text-sm">
                        <span className={`px-2 py-1 rounded border ${getSeverityColor(flag.severity)}`}>
                          {flag.severity}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-600 max-w-md truncate">{flag.reasoning}</td>
                      <td className="px-6 py-4 text-sm text-gray-600">
                        {new Date(flag.created_at).toLocaleDateString()}
                      </td>
                      <td className="px-6 py-4 text-sm">
                        {flag.is_resolved ? (
                          <span className="text-green-600">✓ Resolved</span>
                        ) : (
                          <button
                            onClick={() => handleResolve(flag.id)}
                            className="text-blue-600 hover:text-blue-800 font-medium"
                          >
                            Resolve
                          </button>
                        )}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
};




