import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { FiClock, FiPlay, FiCheckCircle, FiXCircle, FiPause, FiSearch, FiFilter, FiRefreshCw, FiEye } from 'react-icons/fi';
import { agentApi } from '../services/api';

const STATUS_COLORS = {
  running: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300',
  completed: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300',
  failed: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300',
  awaiting_approval: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300',
};

export default function AgentSessions() {
  const [sessions, setSessions] = useState([]);
  const [filteredSessions, setFilteredSessions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const limit = 20;

  const fetchSessions = async (pageNum = 1, status = null) => {
    try {
      setLoading(true);
      const params = { limit, offset: (pageNum - 1) * limit };
      if (status) params.status = status;

      const response = await agentApi.listSessions(status, limit);
      // Ensure we have arrays and numbers
      setSessions(Array.isArray(response.data.sessions) ? response.data.sessions : []);
      setTotal(typeof response.data.total === 'number' ? response.data.total : 0);
      setPage(pageNum);
      setError(null);
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to fetch sessions');
      setSessions([]);
      setTotal(0);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSessions(1, statusFilter || null);
  }, [statusFilter]);

  // Filter by search query
  useEffect(() => {
    const safeSessions = Array.isArray(sessions) ? sessions : [];
    if (!searchQuery.trim()) {
      setFilteredSessions(safeSessions);
    } else {
      const query = searchQuery.toLowerCase();
      const filtered = safeSessions.filter(s =>
        s.title?.toLowerCase().includes(query) ||
        s.id?.toString().includes(query)
      );
      setFilteredSessions(filtered);
    }
  }, [searchQuery, sessions]);

  const getStatusIcon = (status) => {
    switch (status) {
      case 'running':
        return <FiPlay className="w-4 h-4" />;
      case 'completed':
        return <FiCheckCircle className="w-4 h-4" />;
      case 'failed':
        return <FiXCircle className="w-4 h-4" />;
      case 'awaiting_approval':
        return <FiPause className="w-4 h-4" />;
      default:
        return <FiClock className="w-4 h-4" />;
    }
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return '-';
    const date = new Date(dateStr);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  const truncate = (str, len) => {
    if (!str) return '-';
    return str.length > len ? str.substring(0, len) + '...' : str;
  };

  if (loading && sessions.length === 0) {
    return (
      <div className="flex items-center justify-center h-64">
        <FiRefreshCw className="w-8 h-8 animate-spin text-primary-500" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Agent Sessions</h1>
          <p className="text-gray-600 dark:text-gray-400 mt-1">View and manage autonomous agent execution history</p>
        </div>
        <Link
          to="/ai-assistant"
          className="inline-flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 text-white rounded-lg font-medium transition"
        >
          <FiPlay className="w-4 h-4" />
          New Session
        </Link>
      </div>

      {/* Filters */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
        <div className="flex flex-col md:flex-row gap-4">
          {/* Search */}
          <div className="flex-1 relative">
            <FiSearch className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
            <input
              type="text"
              placeholder="Search sessions..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg dark:bg-gray-700 dark:text-white focus:ring-2 focus:ring-purple-500 focus:border-transparent"
            />
          </div>

          {/* Status Filter */}
          <div className="flex items-center gap-2">
            <FiFilter className="w-5 h-5 text-gray-400" />
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg dark:bg-gray-700 dark:text-white focus:ring-2 focus:ring-purple-500"
            >
              <option value="">All Status</option>
              <option value="running">Running</option>
              <option value="completed">Completed</option>
              <option value="failed">Failed</option>
              <option value="awaiting_approval">Awaiting Approval</option>
            </select>
          </div>
        </div>
      </div>

      {/* Sessions List */}
      {error && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-800 dark:text-red-300 p-4 rounded-lg">
          {error}
        </div>
      )}

      {filteredSessions.length === 0 ? (
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-12 text-center">
          <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-gray-100 dark:bg-gray-700 flex items-center justify-center">
            <FiClock className="w-8 h-8 text-gray-400" />
          </div>
          <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">No Sessions Found</h3>
          <p className="text-gray-600 dark:text-gray-400 mb-6">
            {sessions.length === 0
              ? "You haven't created any agent sessions yet."
              : 'No sessions match your current filters.'}
          </p>
          <Link
            to="/ai-assistant"
            className="inline-flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 text-white rounded-lg font-medium transition"
          >
            <FiPlay className="w-4 h-4" />
            Start Your First Session
          </Link>
        </div>
      ) : (
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
          <table className="w-full">
            <thead className="bg-gray-50 dark:bg-gray-900/50 border-b border-gray-200 dark:border-gray-700">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Status</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Title</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Steps</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Created</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Duration</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
              {filteredSessions.map((session) => {
                const duration = session.completed_at && session.created_at
                  ? Math.round((new Date(session.completed_at) - new Date(session.created_at)) / 1000)
                  : null;

                return (
                  <tr key={session.id} className="hover:bg-gray-50 dark:hover:bg-gray-900/30 transition">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center gap-2">
                        <span className={`p-1.5 rounded-full ${STATUS_COLORS[session.status] || 'bg-gray-100'}`}>
                          {getStatusIcon(session.status)}
                        </span>
                        <span className={`text-sm font-medium ${STATUS_COLORS[session.status] || 'text-gray-600'}`}>
                          {session.status.replace('_', ' ')}
                        </span>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="max-w-md">
                        <div className="text-sm font-medium text-gray-900 dark:text-white">
                          {truncate(session.title, 60)}
                        </div>
                        <div className="text-xs text-gray-500 dark:text-gray-400">
                          ID: #{session.id}
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className="text-sm text-gray-700 dark:text-gray-300">
                        {session.step_count || 0} steps
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm text-gray-700 dark:text-gray-300">
                        {formatDate(session.created_at)}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className="text-sm text-gray-700 dark:text-gray-300">
                        {duration ? `${Math.floor(duration / 60)}m ${duration % 60}s` : '-'}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right">
                      <Link
                        to={`/ai-assistant?session=${session.id}`}
                        className="inline-flex items-center gap-1 px-3 py-1.5 text-sm bg-purple-100 hover:bg-purple-200 dark:bg-purple-900/30 dark:hover:bg-purple-800/50 text-purple-700 dark:text-purple-300 rounded-lg transition"
                      >
                        <FiEye className="w-3 h-3" />
                        View
                      </Link>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Summary Stats */}
      {sessions.length > 0 && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
            <div className="text-sm text-gray-600 dark:text-gray-400">Total Sessions</div>
            <div className="text-2xl font-bold text-gray-900 dark:text-white">{total}</div>
          </div>
          <div className="bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
            <div className="text-sm text-gray-600 dark:text-gray-400">Completed</div>
            <div className="text-2xl font-bold text-green-600 dark:text-green-400">
              {sessions.filter(s => s.status === 'completed').length}
            </div>
          </div>
          <div className="bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
            <div className="text-sm text-gray-600 dark:text-gray-400">Failed</div>
            <div className="text-2xl font-bold text-red-600 dark:text-red-400">
              {sessions.filter(s => s.status === 'failed').length}
            </div>
          </div>
          <div className="bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
            <div className="text-sm text-gray-600 dark:text-gray-400">Avg Steps</div>
            <div className="text-2xl font-bold text-gray-900 dark:text-white">
              {sessions.length > 0
                ? Math.round(sessions.reduce((acc, s) => acc + (s.step_count || 0), 0) / sessions.length)
                : 0}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
