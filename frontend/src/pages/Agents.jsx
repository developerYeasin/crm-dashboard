import { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { agentsApi } from '../services/api';

const agentNames = {
  qa: 'QA Agent',
  backend: 'Backend Dev Agent',
  frontend: 'Frontend Dev Agent'
};

const agentDescriptions = {
  qa: 'Performs frontend linting, build checks, and API health tests.',
  backend: 'Reviews backend code, finds security/performance issues, applies safe fixes.',
  frontend: 'Reviews React components, checks accessibility, and improves UI/UX.'
};

export default function Agents() {
  const { isAuthenticated } = useAuth();
  const [status, setStatus] = useState(null);
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [triggering, setTriggering] = useState({});
  const [error, setError] = useState(null);

  const fetchStatus = async () => {
    try {
      const res = await agentsApi.getStatus();
      // Ensure we have an object (not an error)
      setStatus(res.data && typeof res.data === 'object' && !res.data.error ? res.data : null);
      setError(null);
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to fetch agent status');
    } finally {
      setLoading(false);
    }
  };

  const fetchLogs = async () => {
    try {
      const res = await agentsApi.getLogs(null, 20);
      // Ensure we have an array
      setLogs(Array.isArray(res.data) ? res.data : []);
    } catch (err) {
      console.error('Failed to fetch logs:', err);
      setLogs([]);
    }
  };

  useEffect(() => {
    if (isAuthenticated) {
      fetchStatus();
      fetchLogs();
      // Poll every 10 seconds
      const interval = setInterval(fetchStatus, 10000);
      return () => clearInterval(interval);
    }
  }, [isAuthenticated]);

  const triggerAgent = async (agentType) => {
    if (triggering[agentType]) return;

    setTriggering((prev) => ({ ...prev, [agentType]: true }));
    try {
      await agentsApi.trigger(agentType);
      setTimeout(fetchStatus, 2000);
      setTimeout(fetchLogs, 3000);
    } catch (err) {
      
    } finally {
      setTriggering((prev) => ({ ...prev, [agentType]: false }));
    }
  };

  const formatTimestamp = (timestamp) => {
    if (!timestamp) return 'Never';
    try {
      return new Date(timestamp).toLocaleString();
    } catch {
      return timestamp;
    }
  };

  const getStatusIcon = (agent) => {
    if (agent.is_running) {
      return <span className="text-yellow-500 animate-pulse">🔄 Running</span>;
    }
    const lastResult = agent.last_result;
    if (!lastResult) {
      return <span className="text-gray-500">• Never run</span>;
    }
    return lastResult.success ?
      <span className="text-green-500">✅ Success</span> :
      <span className="text-red-500">❌ Failed</span>;
  };

  if (!isAuthenticated) {
    return null;
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-500"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-100 dark:bg-red-900 border border-red-400 text-red-700 dark:text-red-200 p-4 rounded">
        <h3 className="font-bold">Error loading agents</h3>
        <p>{error}</p>
        <button onClick={fetchStatus} className="mt-2 px-4 py-2 bg-red-500 text-white rounded hover:bg-red-600">
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">AI Agents</h1>
        <p className="text-gray-600 dark:text-gray-400 mt-1">
          Monitor and control automated development agents
        </p>
      </div>

      {/* Agent Status Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {Object.entries(agentNames).map(([key, name]) => {
          const agentStatus = status?.[key] || { is_running: false, last_run: null, last_result: null };
          return (
            <div key={key} className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-6 shadow">
              <div className="flex items-start justify-between">
                <div>
                  <h3 className="text-lg font-semibold text-gray-900 dark:text-white">{name}</h3>
                  <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                    {agentDescriptions[key]}
                  </p>
                </div>
                <div className="text-2xl">🤖</div>
              </div>

              <div className="mt-4 space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-500 dark:text-gray-400">Status:</span>
                  <span>{getStatusIcon(agentStatus)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500 dark:text-gray-400">Last run:</span>
                  <span className="text-gray-900 dark:text-white">{formatTimestamp(agentStatus.last_run)}</span>
                </div>
                {agentStatus.last_result && (
                  <div className="flex justify-between">
                    <span className="text-gray-500 dark:text-gray-400">Duration:</span>
                    <span className="text-gray-900 dark:text-white">
                      {agentStatus.last_result.duration ?
                        `${(agentStatus.last_result.duration / 60).toFixed(1)}m` :
                        'N/A'}
                    </span>
                  </div>
                )}
              </div>

              <button
                onClick={() => triggerAgent(key)}
                disabled={triggering[key] || agentStatus.is_running}
                className="mt-4 w-full py-2 px-4 bg-primary-600 text-white rounded hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition"
              >
                {triggering[key] ? 'Starting...' : agentStatus.is_running ? 'Running...' : 'Run Now'}
              </button>
            </div>
          );
        })}
      </div>

      {/* Recent Activity Logs */}
      <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden shadow">
        <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Recent Agent Activity</h2>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Log of all agent runs and results
          </p>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50 dark:bg-gray-900">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  Time
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  Agent
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  Action
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  Details
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
              {logs.length === 0 ? (
                <tr>
                  <td colSpan="4" className="px-6 py-8 text-center text-gray-500 dark:text-gray-400">
                    No agent activity yet. Agents run on schedule or can be triggered manually.
                  </td>
                </tr>
              ) : (
                logs.map((log) => {
                  const actionParts = log.action.split(':', 2);
                  const agent = actionParts[0]?.trim() || 'Unknown';
                  const action = actionParts[1]?.trim() || log.action;

                  return (
                    <tr key={log.id} className="hover:bg-gray-50 dark:hover:bg-gray-900/50">
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-gray-100">
                        {formatTimestamp(log.timestamp)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm">
                        <span className={`px-2 py-1 rounded text-xs font-medium ${
                          agent.includes('QA') ? 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-300' :
                          agent.includes('Backend') ? 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300' :
                          agent.includes('Frontend') ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300' :
                          'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300'
                        }`}>
                          {agent}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-900 dark:text-gray-100">{action}</td>
                      <td className="px-6 py-4 text-sm text-gray-500 dark:text-gray-400 max-w-md truncate">
                        {log.details || '-'}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
