import { useState, useEffect } from 'react';
import { FiUser, FiMail, FiFilter, FiX } from 'react-icons/fi';
import { teamApi, tasksApi } from '../services/api';
import { useAuth } from '../contexts/AuthContext';

export default function Team() {
  const { user } = useAuth();
  const isAdmin = user?.role === 'Administrator';

  const [members, setMembers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedMember, setSelectedMember] = useState(null);
  const [memberTasks, setMemberTasks] = useState([]);
  const [tasksLoading, setTasksLoading] = useState(false);
  const [filterOpen, setFilterOpen] = useState(false);
  const [roleFilter, setRoleFilter] = useState('All');

  const [showMemberModal, setShowMemberModal] = useState(false);
  const [editingMember, setEditingMember] = useState(null);
  const [formData, setFormData] = useState({
    name: '',
    role: '',
    email: '',
    avatar_url: '',
    password: '',
    confirm_password: '',
  });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  useEffect(() => {
    fetchTeam();
  }, []);

  const fetchTeam = async () => {
    setLoading(true);
    try {
      const res = await teamApi.getAll();
      setMembers(Array.isArray(res.data) ? res.data : []);
    } catch (error) {
      console.error('Failed to fetch team:', error);
      setMembers([]);
    } finally {
      setLoading(false);
    }
  };

  const fetchMemberTasks = async (memberId) => {
    setTasksLoading(true);
    try {
      const res = await tasksApi.getAll({ assigned_to: memberId });
      setMemberTasks(Array.isArray(res.data) ? res.data : []);
    } catch (error) {
      console.error('Failed to fetch tasks:', error);
      setMemberTasks([]);
    } finally {
      setTasksLoading(false);
    }
  };

  const handleSelectMember = (member) => {
    setSelectedMember(member);
    fetchMemberTasks(member.id);
  };

  const openCreateModal = () => {
    setEditingMember(null);
    setFormData({ name: '', role: 'Team Member', email: '', avatar_url: '', password: '', confirm_password: '' });
    setError('');
    setSuccess('');
    setShowMemberModal(true);
  };

  const openEditModal = (member) => {
    setEditingMember(member);
    setFormData({
      name: member.name,
      role: member.role,
      email: member.email,
      avatar_url: member.avatar_url || '',
      password: '',
      confirm_password: '',
    });
    setError('');
    setSuccess('');
    setShowMemberModal(true);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    setError('');
    setSuccess('');

    // Validate passwords match for new users or when password is being changed
    if (formData.password && formData.password !== formData.confirm_password) {
      setError('Passwords do not match');
      setSubmitting(false);
      return;
    }

    // Require password for new users
    if (!editingMember && !formData.password) {
      setError('Password is required for new users');
      setSubmitting(false);
      return;
    }

    try {
      const payload = { ...formData };
      // Remove confirm_password before sending
      delete payload.confirm_password;
      // If editing and no password change, remove password field
      if (editingMember && !payload.password) {
        delete payload.password;
      }

      if (editingMember) {
        await teamApi.update(editingMember.id, payload);
        setSuccess('Member updated');
      } else {
        await teamApi.create(payload);
        setSuccess('Member added');
      }
      setShowMemberModal(false);
      fetchTeam();
    } catch (error) {
      setError(error.response?.data?.error || 'Failed to save member');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (memberId) => {
    if (!window.confirm('Delete this team member? Their assigned tasks will become unassigned.')) return;

    try {
      await teamApi.delete(memberId);
      if (selectedMember?.id === memberId) setSelectedMember(null);
      fetchTeam();
    } catch (error) {
      
    }
  };

  const filteredMembers = roleFilter === 'All' ? members : members.filter(m => m.role === roleFilter);
  const uniqueRoles = Array.from(new Set(members.map(m => m.role)));

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
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Team</h1>
        {isAdmin && (
          <button onClick={openCreateModal} className="btn-primary">
            Add Member
          </button>
        )}
      </div>

      <div className="card">
        <div className="flex items-center gap-3 mb-4">
          <button
            onClick={() => setFilterOpen(!filterOpen)}
            className="btn-secondary flex items-center"
          >
            <FiFilter className="mr-2" /> Filter by Role
          </button>
          {roleFilter !== 'All' && (
            <span className="px-3 py-1 bg-primary-100 dark:bg-primary-900/50 text-primary-700 dark:text-primary-300 rounded-full text-sm">
              {roleFilter}
              <button onClick={() => setRoleFilter('All')} className="ml-2">
                <FiX className="inline" />
              </button>
            </span>
          )}
          <span className="ml-auto text-sm text-gray-600 dark:text-gray-400">
            {filteredMembers.length} members
          </span>
        </div>

        {filterOpen && (
          <div className="mb-4 p-4 bg-gray-50 dark:bg-dark-800 rounded-lg">
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Role</label>
            <select
              value={roleFilter}
              onChange={(e) => setRoleFilter(e.target.value)}
              className="select"
            >
              <option value="All">All Roles</option>
              {uniqueRoles.map(role => (
                <option key={role} value={role}>{role}</option>
              ))}
            </select>
          </div>
        )}

        {/* Team grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {filteredMembers.map(member => (
            <div
              key={member.id}
              onClick={() => handleSelectMember(member)}
              className={`p-4 rounded-xl border-2 cursor-pointer transition-all ${
                selectedMember?.id === member.id
                  ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/20'
                  : 'border-transparent bg-gray-50 dark:bg-dark-800 hover:bg-gray-100 dark:hover:bg-dark-700'
              }`}
            >
              <img
                src={member.avatar_url || `https://api.dicebear.com/7.x/adventurer/svg?seed=${member.name}`}
                alt={member.name}
                className="w-20 h-20 rounded-full mx-auto mb-3"
              />
              <h3 className="font-semibold text-gray-900 dark:text-white text-center">{member.name}</h3>
              <p className="text-sm text-primary-600 dark:text-primary-400 text-center mb-2">{member.role}</p>
              <div className="flex items-center justify-center text-xs text-gray-500 dark:text-gray-400">
                <FiUser className="mr-1" />
                <span>Click to view tasks</span>
              </div>

              {/* Action buttons - only admins can edit/delete */}
              {isAdmin && (
                <div className="flex justify-center gap-2 mt-3">
                  <button
                    onClick={(e) => { e.stopPropagation(); openEditModal(member); }}
                    className="text-sm text-primary-500 hover:text-primary-600"
                  >
                    Edit
                  </button>
                  <button
                    onClick={(e) => { e.stopPropagation(); handleDelete(member.id); }}
                    className="text-sm text-red-500 hover:text-red-600"
                  >
                    Delete
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Selected member tasks */}
      {selectedMember && (
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center">
              <img
                src={selectedMember.avatar_url || `https://api.dicebear.com/7.x/adventurer/svg?seed=${selectedMember.name}`}
                alt=""
                className="w-10 h-10 rounded-full mr-3"
              />
              <div>
                <h2 className="font-semibold text-gray-900 dark:text-white">{selectedMember.name}'s Tasks</h2>
                <p className="text-sm text-gray-600 dark:text-gray-400">{selectedMember.role}</p>
              </div>
            </div>
            <button
              onClick={() => setSelectedMember(null)}
              className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
            >
              Clear selection
            </button>
          </div>

          {tasksLoading ? (
            <div className="flex justify-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-500"></div>
            </div>
          ) : memberTasks.length === 0 ? (
            <p className="text-center text-gray-600 dark:text-gray-400 py-8">No tasks assigned to this team member.</p>
          ) : (
            <div className="space-y-3">
              {memberTasks.map(task => (
                <div key={task.id} className="p-3 bg-gray-50 dark:bg-dark-800 rounded-lg">
                  <div className="flex items-start justify-between">
                    <div>
                      <h4 className="font-medium text-gray-900 dark:text-white">{task.title}</h4>
                      <div className="flex items-center gap-2 mt-1">
                        <span className={`px-2 py-0.5 text-xs rounded-full ${
                          task.status === 'Done' ? 'bg-green-100 text-green-700 dark:bg-green-900/50 dark:text-green-300' :
                          task.status === 'In Progress' ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/50 dark:text-blue-300' :
                          'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300'
                        }`}>
                          {task.status}
                        </span>
                        <span className={`px-2 py-0.5 text-xs rounded-full ${
                          task.priority === 'Urgent' ? 'bg-red-100 text-red-700 dark:bg-red-900/50 dark:text-red-300' :
                          task.priority === 'High' ? 'bg-orange-100 text-orange-700 dark:bg-orange-900/50 dark:text-orange-300' :
                          task.priority === 'Medium' ? 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/50 dark:text-yellow-300' :
                          'bg-green-100 text-green-700 dark:bg-green-900/50 dark:text-green-300'
                        }`}>
                          {task.priority}
                        </span>
                      </div>
                    </div>
                    {task.due_date && (
                      <span className={`text-sm ${new Date(task.due_date) < new Date() && task.status !== 'Done' ? 'text-red-600 dark:text-red-400' : 'text-gray-500 dark:text-gray-400'}`}>
                        {new Date(task.due_date).toLocaleDateString()}
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Add/Edit Member Modal */}
      {showMemberModal && (
        <div className="modal-backdrop" onClick={() => setShowMemberModal(false)}>
          <div className="modal-content max-w-md" onClick={(e) => e.stopPropagation()}>
            <div className="px-6 py-4 border-b border-gray-200 dark:border-dark-700">
              <h2 className="text-xl font-bold text-gray-900 dark:text-white">
                {editingMember ? 'Edit Member' : 'Add Team Member'}
              </h2>
            </div>

            <form onSubmit={handleSubmit} className="p-6 space-y-4">
              {error && (
                <div className="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-red-600 dark:text-red-400 text-sm">
                  {error}
                </div>
              )}
              {success && (
                <div className="p-3 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg text-green-600 dark:text-green-400 text-sm">
                  {success}
                </div>
              )}

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Name *</label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  className="input"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Email *</label>
                <input
                  type="email"
                  value={formData.email}
                  onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                  className="input"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Role</label>
                <input
                  type="text"
                  value={formData.role}
                  onChange={(e) => setFormData({ ...formData, role: e.target.value })}
                  className="input"
                  placeholder="e.g., Developer, Designer, Manager"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Avatar URL (optional)
                </label>
                <input
                  type="url"
                  value={formData.avatar_url}
                  onChange={(e) => setFormData({ ...formData, avatar_url: e.target.value })}
                  className="input"
                  placeholder="https://..."
                />
                <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                  Leave empty to auto-generate avatar
                </p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Password {!editingMember && '*'}
                </label>
                <input
                  type="password"
                  value={formData.password}
                  onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                  className="input"
                  placeholder={editingMember ? "Leave blank to keep current" : "Enter password"}
                  required={!editingMember}
                  minLength={6}
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Confirm Password {!editingMember && '*'}
                </label>
                <input
                  type="password"
                  value={formData.confirm_password}
                  onChange={(e) => setFormData({ ...formData, confirm_password: e.target.value })}
                  className="input"
                  required={!editingMember}
                  placeholder="Confirm password"
                />
                {formData.password !== formData.confirm_password && formData.confirm_password && (
                  <p className="mt-1 text-sm text-red-500">Passwords do not match</p>
                )}
              </div>

              <div className="flex justify-end gap-3 pt-4 border-t border-gray-200 dark:border-dark-700">
                <button
                  type="button"
                  onClick={() => setShowMemberModal(false)}
                  className="btn-secondary"
                >
                  Cancel
                </button>
                <button type="submit" disabled={submitting} className="btn-primary">
                  {submitting ? 'Saving...' : editingMember ? 'Update' : 'Add'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
