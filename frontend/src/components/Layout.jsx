import { useState, useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { FiHome, FiCheckSquare, FiUsers, FiCalendar, FiFileText, FiBook, FiClock, FiLogOut, FiMenu, FiX, FiBell, FiSun, FiMoon, FiSearch, FiMessageSquare } from 'react-icons/fi';
import { useAuth } from '../contexts/AuthContext';
import { useTheme } from '../contexts/ThemeContext';
import NotificationsPanel from './NotificationsPanel';

const navigation = [
  { name: 'Dashboard', href: '/', icon: FiHome },
  { name: 'Tasks', href: '/tasks', icon: FiCheckSquare },
  { name: 'Team', href: '/team', icon: FiUsers },
  { name: 'Calendar', href: '/calendar', icon: FiCalendar },
  { name: 'Notes', href: '/notes', icon: FiFileText },
  { name: 'Knowledge Base', href: '/knowledge', icon: FiBook },
  { name: 'Scheduled', href: '/scheduled', icon: FiClock },
  { name: 'AI Assistant', href: '/ai-assistant', icon: FiMessageSquare },
];

export default function Layout({ children }) {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [notificationsOpen, setNotificationsOpen] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);
  const location = useLocation();
  const { logout } = useAuth();
  const { theme, toggleTheme } = useTheme();

  // Global keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e) => {
      // Only if not in an input
      if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.isContentEditable) {
        return;
      }

      if (e.key === '/') {
        e.preventDefault();
        if (document.activeElement === document.body) {
          setSearchOpen(true);
        }
      }

      if (e.key === 'n' || e.key === 'N') {
        e.preventDefault();
        if (document.activeElement === document.body) {
          // Navigate to tasks and open new task modal
          window.location.href = '/tasks?new=true';
        }
      }

      if (e.key === 'Escape') {
        setSearchOpen(false);
        setNotificationsOpen(false);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  // Handle search query from URL params
  useEffect(() => {
    const params = new URLSearchParams(location.search);
    const search = params.get('search');
    if (search) {
      // Could implement global search here
    }
  }, [location]);

  return (
    <div className="min-h-screen bg-gray-100 dark:bg-dark-800 transition-colors duration-300">
      {/* Mobile sidebar overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black bg-opacity-50 z-40 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`fixed top-0 left-0 z-50 h-full w-64 transform bg-white dark:bg-dark-900 border-r border-gray-200 dark:border-dark-700 transition-transform duration-300 ease-in-out lg:translate-x-0 ${
          sidebarOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <div className="flex flex-col h-full">
          {/* Logo */}
          <div className="flex items-center justify-between px-6 py-5 border-b border-gray-200 dark:border-dark-700">
            <Link to="/" className="text-xl font-bold text-primary-500">
              CRM Dashboard
            </Link>
            <button
              className="lg:hidden p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-dark-800"
              onClick={() => setSidebarOpen(false)}
            >
              <FiX className="w-5 h-5" />
            </button>
          </div>

          {/* Navigation */}
          <nav className="flex-1 px-4 py-6 space-y-1 overflow-y-auto">
            {navigation.map((item) => {
              const isActive = location.pathname === item.href;
              const Icon = item.icon;
              return (
                <Link
                  key={item.name}
                  to={item.href}
                  className={`flex items-center px-3 py-2.5 rounded-lg transition-all duration-200 ${
                    isActive
                      ? 'bg-primary-50 dark:bg-primary-900/30 text-primary-600 dark:text-primary-400'
                      : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-dark-800 hover:text-gray-900 dark:hover:text-white'
                  }`}
                  onClick={() => setSidebarOpen(false)}
                >
                  <Icon className="w-5 h-5 mr-3" />
                  <span className="font-medium">{item.name}</span>
                </Link>
              );
            })}
          </nav>

          {/* Footer */}
          <div className="px-4 py-4 border-t border-gray-200 dark:border-dark-700 space-y-2">
            <div className="flex items-center justify-between px-3">
              <span className="text-sm text-gray-600 dark:text-gray-400">Theme</span>
              <button
                onClick={toggleTheme}
                className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-dark-800 transition-colors"
                title={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
              >
                {theme === 'dark' ? <FiSun className="w-4 h-4" /> : <FiMoon className="w-4 h-4" />}
              </button>
            </div>
            <button
              onClick={logout}
              className="w-full flex items-center px-3 py-2.5 text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors"
            >
              <FiLogOut className="w-5 h-5 mr-3" />
              <span className="font-medium">Logout</span>
            </button>
          </div>
        </div>
      </aside>

      {/* Main content */}
      <div className="lg:pl-64">
        {/* Top bar */}
        <header className="sticky top-0 z-30 bg-white dark:bg-dark-900 border-b border-gray-200 dark:border-dark-700">
          <div className="flex items-center justify-between px-4 py-3">
            <button
              className="lg:hidden p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-dark-800"
              onClick={() => setSidebarOpen(true)}
            >
              <FiMenu className="w-6 h-6" />
            </button>

            {/* Global search trigger */}
            <div className="flex-1 max-w-xl mx-4">
              <button
                onClick={() => setSearchOpen(!searchOpen)}
                className="w-full flex items-center px-3 py-2 bg-gray-100 dark:bg-dark-800 rounded-lg hover:bg-gray-200 dark:hover:bg-dark-700 transition-colors text-left text-gray-500 dark:text-gray-400"
              >
                <FiSearch className="w-4 h-4 mr-2" />
                <span className="text-sm">Search (press /)...</span>
                <kbd className="ml-auto text-xs bg-gray-200 dark:bg-dark-700 px-2 py-0.5 rounded text-gray-500">/</kbd>
              </button>

              {/* Search modal */}
              {searchOpen && (
                <div className="absolute top-full left-0 right-0 mt-2 mx-4 bg-white dark:bg-dark-900 border border-gray-200 dark:border-dark-700 rounded-lg shadow-xl z-50">
                  <div className="p-4">
                    <GlobalSearch onClose={() => setSearchOpen(false)} />
                  </div>
                </div>
              )}
            </div>

            {/* Notifications */}
            <div className="relative">
              <button
                onClick={() => setNotificationsOpen(!notificationsOpen)}
                className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-dark-800 transition-colors relative"
              >
                <FiBell className="w-5 h-5" />
                <span className="absolute top-1 right-1 w-2 h-2 bg-red-500 rounded-full"></span>
              </button>

              {notificationsOpen && (
                <NotificationsPanel onClose={() => setNotificationsOpen(false)} />
              )}
            </div>
          </div>
        </header>

        {/* Page content */}
        <main className="p-4 lg:p-6">{children}</main>
      </div>
    </div>
  );
}

// Global search component
function GlobalSearch({ onClose }) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState({ tasks: [], kb: [] });
  const [loading, setLoading] = useState(false);

  const search = async (q) => {
    if (!q.trim()) {
      setResults({ tasks: [], kb: [] });
      return;
    }

    setLoading(true);
    try {
      // Search tasks
      const tasksRes = await tasksApi.getAll({ search: q });
      // Search KB
      const kbRes = await kbApi.search(q);

      setResults({
        tasks: tasksRes.data || [],
        kb: kbRes.data || []
      });
    } catch (error) {
      console.error('Search error:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (e) => {
    const q = e.target.value;
    setQuery(q);
    search(q);
  };

  return (
    <div className="bg-white dark:bg-dark-900" onClick={(e) => e.stopPropagation()}>
      <div className="relative">
        <FiSearch className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
        <input
          type="text"
          value={query}
          onChange={handleChange}
          onKeyDown={(e) => {
            if (e.key === 'Escape') {
              onClose();
            }
          }}
          placeholder="Search tasks, notes, team..."
          className="w-full pl-10 pr-4 py-2 bg-gray-100 dark:bg-dark-800 border border-gray-200 dark:border-dark-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 dark:text-white"
          autoFocus
        />
      </div>

      {/* Results */}
      {(results.tasks.length > 0 || results.kb.length > 0 || loading) && (
        <div className="mt-4 max-h-96 overflow-y-auto">
          {loading && (
            <div className="text-center py-4 text-gray-500 dark:text-gray-400">Searching...</div>
          )}

          {results.tasks.length > 0 && (
            <div className="mb-4">
              <h4 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-2">
                Tasks ({results.tasks.length})
              </h4>
              <div className="space-y-1">
                {results.tasks.slice(0, 5).map((task) => (
                  <Link
                    key={task.id}
                    to={`/tasks/${task.id}`}
                    onClick={onClose}
                    className="block px-3 py-2 rounded-lg hover:bg-gray-100 dark:hover:bg-dark-800 transition-colors"
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-medium">{task.title}</span>
                      <span className={`px-2 py-0.5 text-xs rounded-full ${
                        task.priority === 'Urgent' ? 'bg-red-100 text-red-700 dark:bg-red-900/50 dark:text-red-300' :
                        task.priority === 'High' ? 'bg-orange-100 text-orange-700 dark:bg-orange-900/50 dark:text-orange-300' :
                        task.priority === 'Medium' ? 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/50 dark:text-yellow-300' :
                        'bg-green-100 text-green-700 dark:bg-green-900/50 dark:text-green-300'
                      }`}>
                        {task.priority}
                      </span>
                    </div>
                    <div className="text-xs text-gray-500 dark:text-gray-400">
                      {task.status} • {new Date(task.due_date).toLocaleDateString()}
                    </div>
                  </Link>
                ))}
              </div>
            </div>
          )}

          {results.kb.length > 0 && (
            <div>
              <h4 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-2">
                Knowledge Base ({results.kb.length})
              </h4>
              <div className="space-y-1">
                {results.kb.slice(0, 3).map((entry) => (
                  <Link
                    key={entry.id}
                    to="/knowledge"
                    onClick={onClose}
                    className="block px-3 py-2 rounded-lg hover:bg-gray-100 dark:hover:bg-dark-800 transition-colors"
                  >
                    <div className="font-medium">{entry.title}</div>
                    <div className="text-xs text-gray-500 dark:text-gray-400">{entry.category}</div>
                  </Link>
                ))}
              </div>
            </div>
          )}

          {!loading && results.tasks.length === 0 && results.kb.length === 0 && (
            <div className="text-center py-4 text-gray-500 dark:text-gray-400">No results found</div>
          )}
        </div>
      )}
    </div>
  );
}
