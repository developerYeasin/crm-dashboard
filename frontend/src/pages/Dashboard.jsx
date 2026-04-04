import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { FiPlus, FiArrowRight, FiClock, FiCheckCircle, FiAlertTriangle, FiInbox } from 'react-icons/fi';
import { activityApi, tasksApi } from '../services/api';
import { formatRelativeTime } from '../utils/date';

export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const [recentActivity, setRecentActivity] = useState([]);
  const [quickTaskTitle, setQuickTaskTitle] = useState('');
  const [quickTaskLoading, setQuickTaskLoading] = useState(false);
  const [quickTaskError, setQuickTaskError] = useState('');

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [statsRes, activityRes] = await Promise.all([
        activityApi.getDashboardStats(),
        activityApi.getRecentActivity(5),
      ]);
      // Only set data if response was successful
      setStats(statsRes.data && typeof statsRes.data === 'object' && !statsRes.data.error ? statsRes.data : null);
      setRecentActivity(activityRes.data && Array.isArray(activityRes.data) ? activityRes.data : []);
    } catch (error) {
      console.error('Failed to fetch dashboard data:', error);
      setStats(null);
      setRecentActivity([]);
    }
  };

  const handleQuickAddTask = async (e) => {
    e.preventDefault();
    if (!quickTaskTitle.trim()) return;

    setQuickTaskLoading(true);
    setQuickTaskError('');

    try {
      await tasksApi.create({
        title: quickTaskTitle,
        status: 'To Do',
        priority: 'Medium',
      });
      setQuickTaskTitle('');
      fetchData(); // Refresh stats
    } catch (error) {
      setQuickTaskError(error.response?.data?.error || 'Failed to create task');
    } finally {
      setQuickTaskLoading(false);
    }
  };

  const StatCard = ({ icon: Icon, label, value, color, href }) => (
    <Link
      to={href}
      className={`card flex items-center p-4 hover:shadow-lg transition-shadow group ${color}`}
    >
      <div className={`p-3 rounded-xl ${color.replace('text-', 'bg-').replace('-600', '-100 dark:bg-')}`}>
        <Icon className="w-6 h-6" />
      </div>
      <div className="ml-4">
        <p className="text-sm text-gray-600 dark:text-gray-400">{label}</p>
        <p className="text-2xl font-bold text-gray-900 dark:text-white">{value}</p>
      </div>
      <FiArrowRight className="ml-auto w-5 h-5 text-gray-400 group-hover:text-primary-500 transition-colors" />
    </Link>
  );

  const getActivityIcon = (action) => {
    switch (action) {
      case 'create_task':
        return <FiPlus className="w-4 h-4 text-green-600" />;
      case 'update_task':
        return <FiClock className="w-4 h-4 text-blue-600" />;
      case 'delete_task':
        return <FiAlertTriangle className="w-4 h-4 text-red-600" />;
      default:
        return <FiClock className="w-4 h-4 text-gray-400" />;
    }
  };

  if (!stats) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-500"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Dashboard</h1>
        <p className="text-gray-600 dark:text-gray-400">{new Date().toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}</p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          icon={FiInbox}
          label="Total Tasks"
          value={stats.total}
          color="text-blue-600"
          href="/tasks"
        />
        <StatCard
          icon={FiClock}
          label="In Progress"
          value={stats.in_progress}
          color="text-yellow-600"
          href="/tasks?status=In%20Progress"
        />
        <StatCard
          icon={FiAlertTriangle}
          label="Overdue"
          value={stats.overdue}
          color="text-red-600"
          href="/tasks?status=To%20Do"
        />
        <StatCard
          icon={FiCheckCircle}
          label="Completed This Week"
          value={stats.completed_this_week}
          color="text-green-600"
          href="/tasks?status=Done"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Quick Add Task */}
        <div className="card">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Quick Add Task</h2>
          <form onSubmit={handleQuickAddTask} className="space-y-4">
            <div>
              <input
                type="text"
                value={quickTaskTitle}
                onChange={(e) => setQuickTaskTitle(e.target.value)}
                placeholder="What needs to be done?"
                className="input"
                disabled={quickTaskLoading}
              />
            </div>
            <button
              type="submit"
              disabled={quickTaskLoading || !quickTaskTitle.trim()}
              className="btn-primary w-full"
            >
              {quickTaskLoading ? 'Adding...' : 'Add Task'}
            </button>
            {quickTaskError && (
              <p className="text-sm text-red-600 dark:text-red-400">{quickTaskError}</p>
            )}
            <p className="text-xs text-gray-500 dark:text-gray-400 text-center">
              Press <kbd className="px-1 py-0.5 bg-gray-100 dark:bg-dark-800 rounded text-xs">N</kbd> from anywhere
            </p>
          </form>
        </div>

        {/* Recent Activity */}
        <div className="card lg:col-span-2">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Recent Activity</h2>
            <Link to="/activity" className="text-sm text-primary-500 hover:text-primary-600 flex items-center">
              View all <FiArrowRight className="ml-1 w-4 h-4" />
            </Link>
          </div>

          {recentActivity.length === 0 ? (
            <div className="text-center py-8 text-gray-500 dark:text-gray-400">
              No recent activity
            </div>
          ) : (
            <div className="space-y-4">
              {recentActivity.map((activity, idx) => {
                const details = typeof activity.details === 'string'
                  ? JSON.parse(activity.details)
                  : activity.details;

                return (
                  <div key={idx} className="flex items-start">
                    <div className="mt-1">{getActivityIcon(activity.action)}</div>
                    <div className="ml-3 flex-1">
                      <p className="text-sm text-gray-800 dark:text-gray-200">
                        {activity.action === 'create_task' && (
                          <>Created task <span className="font-medium">{details?.task_title || 'Untitled'}</span></>
                        )}
                        {activity.action === 'update_task' && (
                          <>Updated task <span className="font-medium">{details?.task_title || 'Untitled'}</span></>
                        )}
                        {activity.action === 'delete_task' && (
                          <>Deleted task <span className="font-medium">{details?.task_title || 'Untitled'}</span></>
                        )}
                        {!['create_task', 'update_task', 'delete_task'].includes(activity.action) && (
                          <>Activity: {activity.action}</>
                        )}
                      </p>
                      <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                        {formatRelativeTime(activity.timestamp)}
                      </p>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* Upcoming Tasks Section */}
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Upcoming Tasks</h2>
          <Link to="/calendar" className="text-sm text-primary-500 hover:text-primary-600 flex items-center">
            View calendar <FiArrowRight className="ml-1 w-4 h-4" />
          </Link>
        </div>
        <p className="text-gray-600 dark:text-gray-400 text-sm">Task list for upcoming days coming soon.</p>
      </div>
    </div>
  );
}
