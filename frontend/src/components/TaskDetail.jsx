import { useState, useEffect } from 'react';
import { FiX, FiMessageSquare, FiEdit2, FiSend } from 'react-icons/fi';
import { tasksApi } from '../services/api';
import { formatDate, formatDateTime, getPriorityColor, getStatusColor, isOverdue } from '../utils/date';

export default function TaskDetail({ taskId, onClose, onUpdate }) {
  const [task, setTask] = useState(null);
  const [comment, setComment] = useState('');
  const [submittingComment, setSubmittingComment] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchTask();
  }, [taskId]);

  const fetchTask = async () => {
    try {
      const res = await tasksApi.getById(taskId);
      setTask(res.data);
    } catch (error) {
      console.error('Failed to fetch task:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleAddComment = async (e) => {
    e.preventDefault();
    if (!comment.trim()) return;

    setSubmittingComment(true);
    try {
      await tasksApi.addComment(taskId, comment);
      setComment('');
      fetchTask();
      onUpdate?.();
    } catch (error) {
      alert('Failed to add comment');
    } finally {
      setSubmittingComment(false);
    }
  };

  const getAvatarUrl = (authorId) => {
    // Try to find author in comments' related data or use default
    if (task.assignee?.id === authorId) return task.assignee.avatar_url;
    if (task.assigner?.id === authorId) return task.assigner.avatar_url;
    return `https://api.dicebear.com/7.x/adventurer/svg?seed=User${authorId}`;
  };

  const getAuthorName = (authorId) => {
    // In real app, we'd fetch the name from user data
    // For now, use assignee name if matches, else generic
    if (task.assignee?.id === authorId) return task.assignee.name;
    if (task.assigner?.id === authorId) return task.assigner.name;
    return `User ${authorId}`;
  };

  if (loading) {
    return (
      <div className="fixed inset-0 md:inset-auto md:right-0 md:top-0 md:h-full w-full md:w-96 bg-white dark:bg-dark-900 shadow-2xl z-50 flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-500"></div>
      </div>
    );
  }

  if (!task) {
    return null;
  }

  return (
    <>
      {/* Mobile overlay */}
      <div className="fixed inset-0 bg-black bg-opacity-50 z-40 md:hidden" onClick={onClose} />

      {/* Sidebar */}
      <div className="fixed inset-y-0 right-0 w-full md:w-96 bg-white dark:bg-dark-900 shadow-2xl z-50 flex flex-col transform transition-transform duration-300">
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 dark:border-dark-700">
          <h2 className="font-semibold text-gray-900 dark:text-white">Task Details</h2>
          <button onClick={onClose} className="p-2 hover:bg-gray-100 dark:hover:bg-dark-800 rounded-lg">
            <FiX className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-4 space-y-6">
          <div>
            <span className={`inline-block px-2 py-0.5 text-xs font-medium rounded-full mb-2 ${getStatusColor(task.status)}`}>
              {task.status}
            </span>
            <h1 className="text-xl font-bold text-gray-900 dark:text-white mb-3">{task.title}</h1>

            <div className="flex flex-wrap gap-2 mb-4">
              <span className={`inline-block px-2 py-0.5 text-xs font-medium rounded-full ${getPriorityColor(task.priority)}`}>
                {task.priority} priority
              </span>
            </div>

            {task.description && (
              <div className="prose dark:prose-invert max-w-none mb-6">
                <div className="text-gray-700 dark:text-gray-300 whitespace-pre-wrap">
                  {task.description}
                </div>
              </div>
            )}

            {/* Details */}
            <div className="space-y-3 border-t border-gray-200 dark:border-dark-700 pt-4">
              {task.assignee && (
                <div className="flex items-center text-sm">
                  <span className="text-gray-600 dark:text-gray-400 w-24">Assigned to</span>
                  <div className="flex items-center">
                    <img src={task.assignee.avatar_url} alt="" className="w-6 h-6 rounded-full mr-2" />
                    <span className="text-gray-900 dark:text-white">{task.assignee.name}</span>
                    <span className="ml-2 text-gray-500 dark:text-gray-400">({task.assignee.role})</span>
                  </div>
                </div>
              )}

              {task.assigner && (
                <div className="flex items-center text-sm">
                  <span className="text-gray-600 dark:text-gray-400 w-24">Created by</span>
                  <span className="text-gray-900 dark:text-white">{task.assigner.name}</span>
                </div>
              )}

              {task.due_date && (
                <div className="flex items-center text-sm">
                  <span className="text-gray-600 dark:text-gray-400 w-24">Due date</span>
                  <span className={isOverdue(task.due_date) && task.status !== 'Done' ? 'text-red-600 dark:text-red-400' : 'text-gray-900 dark:text-white'}>
                    {formatDateTime(task.due_date)}
                  </span>
                </div>
              )}

              {task.created_at && (
                <div className="flex items-center text-sm">
                  <span className="text-gray-600 dark:text-gray-400 w-24">Created</span>
                  <span className="text-gray-900 dark:text-white">{formatDateTime(task.created_at)}</span>
                </div>
              )}

              {task.updated_at && (
                <div className="flex items-center text-sm">
                  <span className="text-gray-600 dark:text-gray-400 w-24">Updated</span>
                  <span className="text-gray-900 dark:text-white">{formatDateTime(task.updated_at)}</span>
                </div>
              )}

              {task.tags && (
                <div className="flex items-start text-sm">
                  <span className="text-gray-600 dark:text-gray-400 w-24">Tags</span>
                  <div className="flex flex-wrap gap-1">
                    {(typeof task.tags === 'string' ? JSON.parse(task.tags) : task.tags)?.map(tag => (
                      <span key={tag} className="px-2 py-0.5 bg-gray-100 dark:bg-dark-800 rounded text-xs text-gray-700 dark:text-gray-300">
                        #{tag}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Activity Log / Comments */}
          <div className="border-t border-gray-200 dark:border-dark-700 pt-4">
            <h3 className="font-semibold text-gray-900 dark:text-white mb-4 flex items-center">
              <FiMessageSquare className="mr-2" /> Comments ({task.comments?.length || 0})
            </h3>

            {task.comments && task.comments.length > 0 ? (
              <div className="space-y-4">
                {task.comments.map(comment => (
                  <div key={comment.id} className="flex gap-3">
                    <img
                      src={getAvatarUrl(comment.author)}
                      alt=""
                      className="w-8 h-8 rounded-full flex-shrink-0"
                    />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between mb-1">
                        <span className="font-medium text-gray-900 dark:text-white text-sm">
                          {comment.author_name}
                        </span>
                        <span className="text-xs text-gray-500 dark:text-gray-400">
                          {formatDateTime(comment.created_at)}
                        </span>
                      </div>
                      <p className="text-sm text-gray-700 dark:text-gray-300">{comment.content}</p>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">No comments yet.</p>
            )}

            {/* Add comment form */}
            <form onSubmit={handleAddComment} className="mt-4 flex gap-2">
              <input
                type="text"
                value={comment}
                onChange={(e) => setComment(e.target.value)}
                placeholder="Add a comment..."
                className="input flex-1"
                disabled={submittingComment}
              />
              <button
                type="submit"
                disabled={submittingComment || !comment.trim()}
                className="btn-primary px-3"
              >
                <FiSend />
              </button>
            </form>
          </div>
        </div>
      </div>
    </>
  );
}
