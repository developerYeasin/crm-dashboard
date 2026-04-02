import { useState, useEffect } from 'react';
import { FiClock, FiPlus,FiSend, FiTrash2, FiEdit2, FiX, FiMail, FiMessageSquare, FiBell } from 'react-icons/fi';
import { tasksApi, scheduledApi } from '../services/api';

export default function Scheduled() {
  const [reminders, setReminders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [editingReminder, setEditingReminder] = useState(null);
  const [formData, setFormData] = useState({
    task_id: '',
    reminder_type: 'email',
    scheduled_for: '',
    message: '',
  });
  const [tasks, setTasks] = useState([]);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [sendingId, setSendingId] = useState(null);

  useEffect(() => {
    fetchReminders();
    fetchTasks();
  }, []);

  const fetchReminders = async () => {
    setLoading(true);
    try {
      const res = await scheduledApi.getAll(true);
      setReminders(res.data);
    } catch (error) {
      console.error('Failed to fetch reminders:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchTasks = async () => {
    try {
      const res = await tasksApi.getAll();
      setTasks(res.data);
    } catch (error) {
      console.error('Failed to fetch tasks:', error);
    }
  };

  const openCreateModal = () => {
    setEditingReminder(null);
    setFormData({ task_id: '', reminder_type: 'email', scheduled_for: '', message: '' });
    setError('');
    setModalOpen(true);
  };

  const openEditModal = (reminder) => {
    setEditingReminder(reminder);
    setFormData({
      task_id: reminder.task_id || '',
      reminder_type: reminder.reminder_type,
      scheduled_for: reminder.scheduled_for.split('T')[0], // Just date part
      message: reminder.message || '',
    });
    setError('');
    setModalOpen(true);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    setError('');

    const data = {
      ...formData,
      scheduled_for: `${formData.scheduled_for}T00:00:00`, // Add time
    };

    try {
      if (editingReminder) {
        await scheduledApi.update(editingReminder.id, data);
      } else {
        await scheduledApi.create(data);
      }
      setModalOpen(false);
      fetchReminders();
    } catch (error) {
      setError(error.response?.data?.error || 'Failed to save reminder');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (reminderId) => {
    if (!window.confirm('Delete this reminder?')) return;

    try {
      await scheduledApi.delete(reminderId);
      fetchReminders();
    } catch (error) {
      alert('Failed to delete reminder');
    }
  };

  const handleSendNow = async (reminderId) => {
    setSendingId(reminderId);
    try {
      await scheduledApi.sendNow(reminderId);
      alert('Reminder sent!');
      fetchReminders();
    } catch (error) {
      alert('Failed to send reminder: ' + (error.response?.data?.error || error.message));
    } finally {
      setSendingId(null);
    }
  };

  const getReminderIcon = (type) => {
    switch (type) {
      case 'email':
        return <FiMail className="w-4 h-4" />;
      case 'slack':
        return <FiMessageSquare className="w-4 h-4" />;
      case 'in-app':
        return <FiBell className="w-4 h-4" />;
      default:
        return <FiBell className="w-4 h-4" />;
    }
  };

  const getReminderColor = (type) => {
    switch (type) {
      case 'email':
        return 'bg-blue-100 text-blue-600 dark:bg-blue-900/50 dark:text-blue-400';
      case 'slack':
        return 'bg-purple-100 text-purple-600 dark:bg-purple-900/50 dark:text-purple-400';
      case 'in-app':
        return 'bg-green-100 text-green-600 dark:bg-green-900/50 dark:text-green-400';
      default:
        return 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400';
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-500"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Scheduled Reminders</h1>
        <button onClick={openCreateModal} className="btn-primary flex items-center">
          <FiPlus className="mr-2" /> New Reminder
        </button>
      </div>

      {reminders.length === 0 ? (
        <div className="card text-center py-12">
          <FiClock className="w-12 h-12 mx-auto text-gray-400 mb-4" />
          <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">No upcoming reminders</h3>
          <p className="text-gray-600 dark:text-gray-400 mb-4">Schedule notifications for your tasks</p>
          <button onClick={openCreateModal} className="btn-primary">
            Create Reminder
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {reminders.map(reminder => (
            <div key={reminder.id} className="card">
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center">
                  <div className={`p-2 rounded-lg ${getReminderColor(reminder.reminder_type)}`}>
                    {getReminderIcon(reminder.reminder_type)}
                  </div>
                  <div className="ml-3">
                    <h4 className="font-medium text-gray-900 dark:text-white">{reminder.reminder_type}</h4>
                    <p className="text-sm text-gray-600 dark:text-gray-400">
                      {new Date(reminder.scheduled_for).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
                    </p>
                  </div>
                </div>
                <span className={`px-2 py-1 text-xs rounded-full ${reminder.sent ? 'bg-green-100 text-green-700 dark:bg-green-900/50 dark:text-green-300' : 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/50 dark:text-yellow-300'}`}>
                  {reminder.sent ? 'Sent' : 'Pending'}
                </span>
              </div>

              {reminder.task_id && (
                <div className="mb-3">
                  <span className="text-sm text-gray-600 dark:text-gray-400">Task: </span>
                  <span className="text-sm text-gray-900 dark:text-white">
                    {tasks.find(t => t.id === reminder.task_id)?.title || reminder.task_id}
                  </span>
                </div>
              )}

              {reminder.message && (
                <p className="text-sm text-gray-700 dark:text-gray-300 mb-4">{reminder.message}</p>
              )}

              <div className="flex items-center justify-between pt-3 border-t border-gray-200 dark:border-dark-700">
                <span className="text-xs text-gray-500 dark:text-gray-400">
                  Created: {new Date(reminder.created_at).toLocaleDateString()}
                </span>
                <div className="flex gap-2">
                  {!reminder.sent && (
                    <button
                      onClick={() => handleSendNow(reminder.id)}
                      disabled={sendingId === reminder.id}
                      className="p-1.5 hover:bg-gray-100 dark:hover:bg-dark-800 rounded text-sm flex items-center text-primary-500"
                      title="Send now"
                    >
                      <FiSend className="w-4 h-4" />
                    </button>
                  )}
                  <button
                    onClick={() => openEditModal(reminder)}
                    className="p-1.5 hover:bg-gray-100 dark:hover:bg-dark-800 rounded"
                    title="Edit"
                  >
                    <FiEdit2 className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => handleDelete(reminder.id)}
                    className="p-1.5 hover:bg-gray-100 dark:hover:bg-dark-800 rounded text-red-500"
                    title="Delete"
                  >
                    <FiTrash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Create/Edit Modal */}
      {modalOpen && (
        <div className="modal-backdrop" onClick={() => setModalOpen(false)}>
          <div className="modal-content max-w-md" onClick={(e) => e.stopPropagation()}>
            <div className="px-6 py-4 border-b border-gray-200 dark:border-dark-700 flex items-center justify-between">
              <h2 className="text-xl font-bold text-gray-900 dark:text-white">
                {editingReminder ? 'Edit Reminder' : 'New Reminder'}
              </h2>
              <button onClick={() => setModalOpen(false)} className="p-2 hover:bg-gray-100 dark:hover:bg-dark-800 rounded-lg">
                <FiX className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleSubmit} className="p-6 space-y-4">
              {error && (
                <div className="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-red-600 dark:text-red-400 text-sm">
                  {error}
                </div>
              )}

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Reminder Type
                </label>
                <select
                  value={formData.reminder_type}
                  onChange={(e) => setFormData({ ...formData, reminder_type: e.target.value })}
                  className="select"
                >
                  <option value="email">Email</option>
                  <option value="slack">Slack</option>
                  <option value="in-app">In-App</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Task (optional)
                </label>
                <select
                  value={formData.task_id}
                  onChange={(e) => setFormData({ ...formData, task_id: e.target.value ? parseInt(e.target.value) : '' })}
                  className="select"
                >
                  <option value="">None (general reminder)</option>
                  {tasks.map(task => (
                    <option key={task.id} value={task.id}>{task.title}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Schedule Date *
                </label>
                <input
                  type="date"
                  value={formData.scheduled_for}
                  onChange={(e) => setFormData({ ...formData, scheduled_for: e.target.value })}
                  className="input"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Message (optional)
                </label>
                <textarea
                  value={formData.message}
                  onChange={(e) => setFormData({ ...formData, message: e.target.value })}
                  className="textarea"
                  rows={3}
                  placeholder="Reminder message..."
                />
              </div>

              <div className="flex justify-end gap-3 pt-4 border-t border-gray-200 dark:border-dark-700">
                <button
                  type="button"
                  onClick={() => setModalOpen(false)}
                  className="btn-secondary"
                >
                  Cancel
                </button>
                <button type="submit" disabled={submitting || !formData.scheduled_for} className="btn-primary">
                  {submitting ? 'Saving...' : editingReminder ? 'Update' : 'Create'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
