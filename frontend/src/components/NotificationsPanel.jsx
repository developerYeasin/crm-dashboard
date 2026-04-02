import { useState, useEffect } from 'react';
import { FiClock, FiAlertTriangle, FiX } from 'react-icons/fi';
import { activityApi } from '../services/api';

export default function NotificationsPanel({ onClose }) {
  const [notifications, setNotifications] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchNotifications();
  }, []);

  const fetchNotifications = async () => {
    try {
      const [statsRes, recentRes] = await Promise.all([
        activityApi.getDashboardStats(),
        activityApi.getRecentActivity(10),
      ]);

      const stats = statsRes.data;
      const recent = recentRes.data;

      const notifs = [];

      if (stats.overdue > 0) {
        notifs.push({
          type: 'overdue',
          title: `${stats.overdue} overdue task${stats.overdue > 1 ? 's' : ''}`,
          description: 'Tasks past their due date need attention',
          priority: 'high',
        });
      }

      if (stats.in_progress > 0) {
        notifs.push({
          type: 'in_progress',
          title: `${stats.in_progress} task${stats.in_progress > 1 ? 's' : ''} in progress`,
          description: 'Keep an eye on work in progress',
          priority: 'medium',
        });
      }

      // Recent activity as notifications
      recent.forEach((activity) => {
        if (activity.action === 'create_task') {
          const details = typeof activity.details === 'string' ? JSON.parse(activity.details) : activity.details;
          notifs.push({
            type: 'activity',
            title: 'New task created',
            description: details?.task_title || 'A new task was added',
            time: activity.timestamp,
            priority: 'low',
          });
        }
      });

      setNotifications(notifs);
    } catch (error) {
      console.error('Failed to fetch notifications:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      className="absolute right-0 top-full mt-2 w-80 bg-white dark:bg-dark-900 rounded-xl shadow-2xl border border-gray-200 dark:border-dark-700 z-50 overflow-hidden"
      onClick={(e) => e.stopPropagation()}
    >
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 dark:border-dark-700">
        <h3 className="font-semibold text-gray-900 dark:text-white">Notifications</h3>
        <button onClick={onClose} className="p-1 hover:bg-gray-100 dark:hover:bg-dark-800 rounded">
          <FiX className="w-4 h-4" />
        </button>
      </div>

      <div className="max-h-96 overflow-y-auto">
        {loading ? (
          <div className="p-4 text-center text-gray-500 dark:text-gray-400">Loading...</div>
        ) : notifications.length === 0 ? (
          <div className="p-4 text-center text-gray-500 dark:text-gray-400">No notifications</div>
        ) : (
          <div className="p-2">
            {notifications.map((notif, index) => (
              <div
                key={index}
                className={`p-3 rounded-lg mb-2 ${
                  notif.priority === 'high'
                    ? 'bg-red-50 dark:bg-red-900/20 border-l-2 border-red-500'
                    : notif.priority === 'medium'
                    ? 'bg-yellow-50 dark:bg-yellow-900/20 border-l-2 border-yellow-500'
                    : 'bg-blue-50 dark:bg-blue-900/20 border-l-2 border-blue-500'
                }`}
              >
                <div className="flex items-start">
                  <div
                    className={`p-1.5 rounded-full mr-3 ${
                      notif.priority === 'high'
                        ? 'bg-red-100 dark:bg-red-900/50 text-red-600 dark:text-red-400'
                        : notif.priority === 'medium'
                        ? 'bg-yellow-100 dark:bg-yellow-900/50 text-yellow-600 dark:text-yellow-400'
                        : 'bg-blue-100 dark:bg-blue-900/50 text-blue-600 dark:text-blue-400'
                    }`}
                  >
                    {notif.priority === 'high' ? (
                      <FiAlertTriangle className="w-4 h-4" />
                    ) : (
                      <FiClock className="w-4 h-4" />
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <h4 className="text-sm font-medium text-gray-900 dark:text-white">
                      {notif.title}
                    </h4>
                    <p className="text-xs text-gray-600 dark:text-gray-400 mt-0.5">
                      {notif.description}
                    </p>
                    {notif.time && (
                      <p className="text-xs text-gray-500 dark:text-gray-500 mt-1">
                        {new Date(notif.time).toLocaleString()}
                      </p>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
