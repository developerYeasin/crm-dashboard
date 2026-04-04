import { useState, useEffect, useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';
import { FiPlus, FiFilter, FiX, FiMessageSquare, FiEdit2, FiTrash2, FiChevronRight, FiUser, FiClock, FiTag, FiInbox } from 'react-icons/fi';
import { tasksApi, teamApi } from '../services/api';
import { formatDate, formatDateTime, isOverdue, getPriorityColor, getStatusColor } from '../utils/date';
import TaskDetail from '../components/TaskDetail';

export default function Tasks() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [tasks, setTasks] = useState([]);
  const [teamMembers, setTeamMembers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // Filters
  const [statusFilter, setStatusFilter] = useState(searchParams.get('status') || 'All');
  const [priorityFilter, setPriorityFilter] = useState(searchParams.get('priority') || 'All');
  const [assigneeFilter, setAssigneeFilter] = useState(searchParams.get('assignee') || 'All');
  const [showFilters, setShowFilters] = useState(false);

  // Task modal
  const [modalOpen, setModalOpen] = useState(searchParams.get('new') === 'true');
  const [editingTask, setEditingTask] = useState(null);
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    status: 'To Do',
    priority: 'Medium',
    assigned_to: '',
    due_date: '',
    tags: '',
  });
  const [submitting, setSubmitting] = useState(false);

  // Task detail panel
  const [detailTaskId, setDetailTaskId] = useState(null);

  useEffect(() => {
    fetchTeam();
    fetchTasks();
  }, [statusFilter, priorityFilter, assigneeFilter]);

  const fetchTeam = async () => {
    try {
      const res = await teamApi.getAll();
      setTeamMembers(Array.isArray(res.data) ? res.data : []);
    } catch (error) {
      console.error('Failed to fetch team:', error);
      setTeamMembers([]);
    }
  };

  const fetchTasks = async () => {
    setLoading(true);
    try {
      const params = {};
      if (statusFilter !== 'All') params.status = statusFilter;
      if (priorityFilter !== 'All') params.priority = priorityFilter;
      if (assigneeFilter !== 'All') params.assigned_to = assigneeFilter;

      const res = await tasksApi.getAll(params);
      setTasks(Array.isArray(res.data) ? res.data : []);
      setError('');
    } catch (error) {
      setError('Failed to load tasks');
      console.error(error);
      setTasks([]);
    } finally {
      setLoading(false);
    }
  };

  const openCreateModal = () => {
    setEditingTask(null);
    setFormData({
      title: '',
      description: '',
      status: 'To Do',
      priority: 'Medium',
      assigned_to: '',
      due_date: '',
      tags: '',
    });
    setModalOpen(true);
    setSearchParams({}); // Clear URL params
  };

  const openEditModal = (task) => {
    setEditingTask(task);
    setFormData({
      title: task.title,
      description: task.description || '',
      status: task.status,
      priority: task.priority,
      assigned_to: task.assigned_to || '',
      due_date: task.due_date ? formatDateInput(task.due_date) : '',
      tags: typeof task.tags === 'string' ? task.tags.replace(/["\[\]]/g, '') : (task.tags || '').join(', '),
    });
    setModalOpen(true);
  };

  const formatDateInput = (dateString) => {
    return dateString ? new Date(dateString).toISOString().split('T')[0] : '';
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    setError('');

    const data = {
      ...formData,
      tags: formData.tags.split(',').map(t => t.trim()).filter(t => t),
    };

    try {
      if (editingTask) {
        await tasksApi.update(editingTask.id, data);
      } else {
        await tasksApi.create(data);
      }
      setModalOpen(false);
      fetchTasks();
    } catch (error) {
      setError(error.response?.data?.error || 'Failed to save task');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (taskId) => {
    if (!window.confirm('Delete this task? This action cannot be undone.')) return;

    try {
      await tasksApi.delete(taskId);
      fetchTasks();
      if (detailTaskId === taskId) setDetailTaskId(null);
    } catch (error) {
      
    }
  };

  const filteredTasks = tasks;

  const uniqueAssignees = Array.from(new Set(tasks.map(t => t.assigned_to).filter(Boolean)));

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Tasks</h1>
        <button onClick={openCreateModal} className="btn-primary flex items-center justify-center">
          <FiPlus className="mr-2" /> New Task
        </button>
      </div>

      {/* Filters */}
      <div className="card">
        <div className="flex flex-wrap items-center gap-3">
          <button
            onClick={() => setShowFilters(!showFilters)}
            className="btn-secondary flex items-center"
          >
            <FiFilter className="mr-2" /> Filters
            {(statusFilter !== 'All' || priorityFilter !== 'All' || assigneeFilter !== 'All') && (
              <span className="ml-2 w-2 h-2 bg-primary-500 rounded-full"></span>
            )}
          </button>

          {statusFilter !== 'All' && (
            <span className="px-3 py-1 bg-primary-100 dark:bg-primary-900/50 text-primary-700 dark:text-primary-300 rounded-full text-sm flex items-center">
              Status: {statusFilter}
              <button onClick={() => setStatusFilter('All')}>
                <FiX className="ml-2" />
              </button>
            </span>
          )}

          {priorityFilter !== 'All' && (
            <span className="px-3 py-1 bg-primary-100 dark:bg-primary-900/50 text-primary-700 dark:text-primary-300 rounded-full text-sm flex items-center">
              Priority: {priorityFilter}
              <button onClick={() => setPriorityFilter('All')}>
                <FiX className="ml-2" />
              </button>
            </span>
          )}

          {assigneeFilter !== 'All' && (
            <span className="px-3 py-1 bg-primary-100 dark:bg-primary-900/50 text-primary-700 dark:text-primary-300 rounded-full text-sm flex items-center">
              Assignee: {teamMembers.find(m => m.id === parseInt(assigneeFilter))?.name || 'Unknown'}
              <button onClick={() => setAssigneeFilter('All')}>
                <FiX className="ml-2" />
              </button>
            </span>
          )}

          <div className="flex-1" />

          <span className="text-sm text-gray-600 dark:text-gray-400">
            {filteredTasks.length} task{filteredTasks.length !== 1 ? 's' : ''}
          </span>
        </div>

        {showFilters && (
          <div className="mt-4 pt-4 border-t border-gray-200 dark:border-dark-700 grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Status</label>
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="select"
              >
                <option value="All">All</option>
                <option value="To Do">To Do</option>
                <option value="In Progress">In Progress</option>
                <option value="Done">Done</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Priority</label>
              <select
                value={priorityFilter}
                onChange={(e) => setPriorityFilter(e.target.value)}
                className="select"
              >
                <option value="All">All</option>
                <option value="Urgent">Urgent</option>
                <option value="High">High</option>
                <option value="Medium">Medium</option>
                <option value="Low">Low</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Assigned To</label>
              <select
                value={assigneeFilter}
                onChange={(e) => setAssigneeFilter(e.target.value)}
                className="select"
              >
                <option value="All">All</option>
                {teamMembers.map(member => (
                  <option key={member.id} value={member.id}>{member.name}</option>
                ))}
              </select>
            </div>
          </div>
        )}
      </div>

      {/* Task List */}
      {loading ? (
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-500"></div>
        </div>
      ) : error ? (
        <div className="card text-center text-red-600 dark:text-red-400">{error}</div>
      ) : filteredTasks.length === 0 ? (
        <div className="card text-center py-12">
          <FiInbox className="w-12 h-12 mx-auto text-gray-400 mb-4" />
          <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">No tasks found</h3>
          <p className="text-gray-600 dark:text-gray-400 mb-4">Get started by creating your first task.</p>
          <button onClick={openCreateModal} className="btn-primary">
            <FiPlus className="inline mr-2" /> Create Task
          </button>
        </div>
      ) : (
        <div className="space-y-3">
          {filteredTasks.map(task => (
            <div
              key={task.id}
              onClick={() => setDetailTaskId(task.id)}
              className={`card cursor-pointer hover:shadow-md transition-shadow group ${
                isOverdue(task.due_date) && task.status !== 'Done' ? 'border-l-4 border-l-red-500' : ''
              }`}
            >
              <div className="flex items-start justify-between">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-2 flex-wrap">
                    <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${getStatusColor(task.status)}`}>
                      {task.status}
                    </span>
                    <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${getPriorityColor(task.priority)}`}>
                      {task.priority}
                    </span>
                  </div>
                  <h3 className="font-semibold text-gray-900 dark:text-white mb-2 group-hover:text-primary-500 transition-colors">
                    {task.title}
                  </h3>
                  {task.description && (
                    <p className="text-sm text-gray-600 dark:text-gray-400 line-clamp-2 mb-3">
                      {task.description}
                    </p>
                  )}
                  <div className="flex items-center gap-4 text-sm text-gray-500 dark:text-gray-400 flex-wrap">
                    {task.assignee && (
                      <div className="flex items-center">
                        <img src={task.assignee.avatar_url} alt="" className="w-5 h-5 rounded-full mr-1" />
                        <span>{task.assignee.name}</span>
                      </div>
                    )}
                    {task.due_date && (
                      <div className={`flex items-center ${isOverdue(task.due_date) && task.status !== 'Done' ? 'text-red-600 dark:text-red-400' : ''}`}>
                        <FiClock className="mr-1" />
                        <span>{formatDate(task.due_date)}</span>
                      </div>
                    )}
                    {task.tags && Array.isArray(JSON.parse(task.tags)) && (
                      <div className="flex items-center flex-wrap gap-1">
                        {JSON.parse(task.tags).map((tag, idx) => (
                          <span key={idx} className="px-1.5 py-0.5 bg-gray-100 dark:bg-dark-800 rounded text-xs">
                            #{tag}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
                <button
                  onClick={(e) => { e.stopPropagation(); openEditModal(task); }}
                  className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-dark-800 opacity-0 group-hover:opacity-100 transition-opacity"
                >
                  <FiEdit2 className="w-4 h-4" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Create/Edit Modal */}
      {modalOpen && (
        <TaskModal
          task={editingTask}
          formData={formData}
          setFormData={setFormData}
          teamMembers={teamMembers}
          submitting={submitting}
          onSubmit={handleSubmit}
          onClose={() => setModalOpen(false)}
          onDelete={editingTask ? () => handleDelete(editingTask.id) : null}
        />
      )}

      {/* Task Detail Sidebar */}
      {detailTaskId && (
        <TaskDetail
          taskId={detailTaskId}
          onClose={() => setDetailTaskId(null)}
          onUpdate={fetchTasks}
        />
      )}
    </div>
  );
}

// Task Modal Component
function TaskModal({ task, formData, setFormData, teamMembers, submitting, onSubmit, onClose, onDelete }) {
  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-dark-700">
          <h2 className="text-xl font-bold text-gray-900 dark:text-white">
            {task ? 'Edit Task' : 'New Task'}
          </h2>
          <button onClick={onClose} className="p-2 hover:bg-gray-100 dark:hover:bg-dark-800 rounded-lg">
            <FiX className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={onSubmit} className="flex-1 overflow-y-auto p-6 space-y-4">
          {error && (
            <div className="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-red-600 dark:text-red-400 text-sm">
              {error}
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Title *
            </label>
            <input
              type="text"
              value={formData.title}
              onChange={(e) => setFormData({ ...formData, title: e.target.value })}
              className="input"
              placeholder="Task title"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Description
            </label>
            <textarea
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              className="textarea"
              rows={4}
              placeholder="Task description (optional)"
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Status
              </label>
              <select
                value={formData.status}
                onChange={(e) => setFormData({ ...formData, status: e.target.value })}
                className="select"
              >
                <option value="To Do">To Do</option>
                <option value="In Progress">In Progress</option>
                <option value="Done">Done</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Priority
              </label>
              <select
                value={formData.priority}
                onChange={(e) => setFormData({ ...formData, priority: e.target.value })}
                className="select"
              >
                <option value="Low">Low</option>
                <option value="Medium">Medium</option>
                <option value="High">High</option>
                <option value="Urgent">Urgent</option>
              </select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Assignee
              </label>
              <select
                value={formData.assigned_to}
                onChange={(e) => setFormData({ ...formData, assigned_to: e.target.value ? parseInt(e.target.value) : '' })}
                className="select"
              >
                <option value="">Unassigned</option>
                {teamMembers.map(member => (
                  <option key={member.id} value={member.id}>
                    {member.name} ({member.role})
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Due Date
              </label>
              <input
                type="date"
                value={formData.due_date}
                onChange={(e) => setFormData({ ...formData, due_date: e.target.value })}
                className="input"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Tags (comma-separated)
            </label>
            <input
              type="text"
              value={formData.tags}
              onChange={(e) => setFormData({ ...formData, tags: e.target.value })}
              className="input"
              placeholder="design, bug, feature"
            />
          </div>

          <div className="flex items-center justify-between pt-4 border-t border-gray-200 dark:border-dark-700">
            {onDelete && (
              <button
                type="button"
                onClick={() => { onDelete(); onClose(); }}
                className="btn-danger"
              >
                <FiTrash2 className="inline mr-2" /> Delete
              </button>
            )}
            <div className="flex gap-3 ml-auto">
              <button type="button" onClick={onClose} className="btn-secondary">
                Cancel
              </button>
              <button type="submit" disabled={submitting} className="btn-primary">
                {submitting ? 'Saving...' : task ? 'Update' : 'Create'}
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
}
