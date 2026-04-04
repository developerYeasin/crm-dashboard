import { useState, useEffect } from 'react';
import { FiActivity, FiSearch, FiClock, FiFilter, FiTag, FiTrash2, FiEye } from 'react-icons/fi';
import { agentApi } from '../services/api';

const MEMORY_TYPES = ['fact', 'preference', 'skill', 'error', 'success'];
const MEMORY_TYPE_LABELS = {
  fact: 'Fact',
  preference: 'Preference',
  skill: 'Skill',
  error: 'Error',
  success: 'Success'
};

export default function AgentMemories() {
  const [memories, setMemories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [typeFilter, setTypeFilter] = useState('');
  const [selectedMemory, setSelectedMemory] = useState(null);

  const fetchMemories = async () => {
    try {
      setLoading(true);
      const query = searchQuery || undefined;
      const type = typeFilter || undefined;
      const response = await agentApi.getMemories(query, type);
      const memories = Array.isArray(response.data?.memories) ? response.data.memories : [];
      setMemories(memories);
      setError(null);
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to fetch memories');
      setMemories([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMemories();
  }, [searchQuery, typeFilter]); // Reload when filters change

  const getTypeIcon = (type) => {
    const icons = {
      fact: <FiTag className="text-blue-500" />,
      preference: <FiTag className="text-purple-500" />,
      skill: <FiTag className="text-green-500" />,
      error: <FiTag className="text-red-500" />,
      success: <FiTag className="text-yellow-500" />
    };
    return icons[type] || <FiTag />;
  };

  const getTypeBadgeClass = (type) => {
    const classes = {
      fact: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300',
      preference: 'bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-300',
      skill: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300',
      error: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300',
      success: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300'
    };
    return classes[type] || 'bg-gray-100 text-gray-800';
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Agent Memory</h1>
          <p className="text-gray-600 dark:text-gray-400 mt-1">Long-term memories and learned information</p>
        </div>
        <button
          onClick={fetchMemories}
          className="inline-flex items-center gap-2 px-4 py-2 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition"
        >
          <FiClock className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      {/* Filters */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
        <div className="flex flex-col md:flex-row gap-4">
          <div className="flex-1 relative">
            <FiSearch className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
            <input
              type="text"
              placeholder="Search memories..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg dark:bg-gray-700 dark:text-white focus:ring-2 focus:ring-purple-500"
            />
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            <FiFilter className="w-5 h-5 text-gray-400" />
            {MEMORY_TYPES.map(type => (
              <button
                key={type}
                onClick={() => setTypeFilter(typeFilter === type ? '' : type)}
                className={`px-3 py-1.5 rounded-full text-sm transition ${
                  typeFilter === type
                    ? getTypeBadgeClass(type)
                    : 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300 hover:opacity-80'
                }`}
              >
                {MEMORY_TYPE_LABELS[type]}
              </button>
            ))}
          </div>
        </div>
      </div>

      {error && (
        <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 text-yellow-800 dark:text-yellow-300 p-4 rounded-lg">
          <strong>Note:</strong> {error}
        </div>
      )}

      {/* Memories Grid */}
      {loading ? (
        <div className="flex items-center justify-center h-64">
          <FiClock className="w-8 h-8 animate-spin text-primary-500" />
        </div>
      ) : memories.length === 0 ? (
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-12 text-center">
          <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-gray-100 dark:bg-gray-700 flex items-center justify-center">
            <FiActivity className="w-8 h-8 text-gray-400" />
          </div>
          <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">No Memories Found</h3>
          <p className="text-gray-600 dark:text-gray-400">
            Memories are created automatically as the agent learns from successful executions.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {memories.map(memory => (
            <div
              key={memory.id}
              className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5 hover:shadow-lg transition-shadow cursor-pointer"
              onClick={() => setSelectedMemory(memory)}
            >
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-2">
                  {getTypeIcon(memory.memory_type)}
                  <span className={`text-xs px-2 py-0.5 rounded-full ${getTypeBadgeClass(memory.memory_type)}`}>
                    {MEMORY_TYPE_LABELS[memory.memory_type]}
                  </span>
                </div>
                <div className="flex items-center gap-1 text-xs text-gray-500">
                  <FiEye className="w-3 h-3" />
                  {memory.access_count || 0}
                </div>
              </div>

              <p className="text-gray-900 dark:text-white text-sm mb-4 line-clamp-4">
                {memory.content}
              </p>

              <div className="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400">
                <div className="flex items-center gap-1">
                  <FiClock className="w-3 h-3" />
                  Created: {new Date(memory.created_at).toLocaleDateString()}
                </div>
                {memory.importance !== undefined && (
                  <div className="flex items-center gap-1">
                    Importance: {(memory.importance * 100).toFixed(0)}%
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Memory Detail Modal */}
      {selectedMemory && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4" onClick={() => setSelectedMemory(null)}>
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
            <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
              <div>
                <h2 className="text-xl font-bold text-gray-900 dark:text-white">Memory Details</h2>
                <div className="flex items-center gap-2 mt-1">
                  <span className={`text-xs px-2 py-0.5 rounded-full ${getTypeBadgeClass(selectedMemory.memory_type)}`}>
                    {MEMORY_TYPE_LABELS[selectedMemory.memory_type]}
                  </span>
                  {selectedMemory.session_id && (
                    <span className="text-xs text-gray-500">Session #{selectedMemory.session_id}</span>
                  )}
                </div>
              </div>
              <button onClick={() => setSelectedMemory(null)} className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg">
                ✕
              </button>
            </div>
            <div className="p-6 space-y-4">
              <div>
                <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Content</h3>
                <p className="text-gray-900 dark:text-white whitespace-pre-wrap leading-relaxed">
                  {selectedMemory.content}
                </p>
              </div>

              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <h4 className="text-gray-700 dark:text-gray-300 mb-1">Importance</h4>
                  <div className="flex items-center gap-2">
                    <div className="flex-1 bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                      <div
                        className="bg-purple-600 h-2 rounded-full"
                        style={{ width: `${(selectedMemory.importance || 0) * 100}%` }}
                      ></div>
                    </div>
                    <span className="text-gray-900 dark:text-white">
                      {(selectedMemory.importance || 0) * 100}%
                    </span>
                  </div>
                </div>
                <div>
                  <h4 className="text-gray-700 dark:text-gray-300 mb-1">Access Count</h4>
                  <p className="text-gray-900 dark:text-white">{selectedMemory.access_count || 0}</p>
                </div>
                <div>
                  <h4 className="text-gray-700 dark:text-gray-300 mb-1">Created</h4>
                  <p className="text-gray-900 dark:text-white">
                    {new Date(selectedMemory.created_at).toLocaleString()}
                  </p>
                </div>
                <div>
                  <h4 className="text-gray-700 dark:text-gray-300 mb-1">Last Accessed</h4>
                  <p className="text-gray-900 dark:text-white">
                    {selectedMemory.last_accessed
                      ? new Date(selectedMemory.last_accessed).toLocaleString()
                      : 'Never'}
                  </p>
                </div>
              </div>

              <div className="flex justify-end gap-3 pt-4 border-t border-gray-200 dark:border-gray-700">
                <button
                  onClick={() => setSelectedMemory(null)}
                  className="px-4 py-2 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
