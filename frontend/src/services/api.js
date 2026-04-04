import axios from 'axios';

// Tasks API
export const tasksApi = {
  getAll: (filters = {}) => axios.get('/tasks', { params: filters }),
  getById: (id) => axios.get(`/tasks/${id}`),
  create: (data) => axios.post('/tasks', data),
  update: (id, data) => axios.put(`/tasks/${id}`, data),
  delete: (id) => axios.delete(`/tasks/${id}`),
  updateStatus: (id, status) => axios.patch(`/tasks/${id}/status`, { status }),
  getComments: (taskId) => axios.get(`/tasks/${taskId}/comments`),
  addComment: (taskId, content, authorId = 1) =>
    axios.post(`/tasks/${taskId}/comments`, { content, author_id: authorId }),
};

// Team API
export const teamApi = {
  getAll: () => axios.get('/team'),
  getById: (id) => axios.get(`/team/${id}`),
  create: (data) => axios.post('/team', data),
  update: (id, data) => axios.put(`/team/${id}`, data),
  delete: (id) => axios.delete(`/team/${id}`),
};

// Notes API
export const notesApi = {
  getAll: () => axios.get('/notes'),
  getById: (id) => axios.get(`/notes/${id}`),
  create: (data) => axios.post('/notes', data),
  update: (id, data) => axios.put(`/notes/${id}`, data),
  delete: (id) => axios.delete(`/notes/${id}`),
};

// Knowledge Base API
export const kbApi = {
  getAll: (category) => axios.get('/kb', { params: { category } }),
  getCategories: () => axios.get('/kb/categories'),
  getById: (id) => axios.get(`/kb/${id}`),
  create: (data) => axios.post('/kb', data),
  update: (id, data) => axios.put(`/kb/${id}`, data),
  delete: (id) => axios.delete(`/kb/${id}`),
  search: (query) => axios.get('/kb/search', { params: { q: query } }),
};

// Calendar API
export const calendarApi = {
  getTasks: (start, end) =>
    axios.get('/calendar/tasks', { params: { start, end } }),
  getDayTasks: (date) => axios.get(`/calendar/day/${date}`),
};

// Activity API
export const activityApi = {
  getLog: (limit = 50) => axios.get('/activity', { params: { limit } }),
  getDashboardStats: () => axios.get('/stats/dashboard'),
  getRecentActivity: (limit = 5) =>
    axios.get('/stats/recent-activity', { params: { limit } }),
};

// Agents API
export const agentsApi = {
  trigger: (agentType) => axios.post(`/agents/trigger/${agentType}`),
  getStatus: () => axios.get('/agents/status'),
  getLogs: (agentType, limit = 50) =>
    axios.get('/agents/logs', { params: { agent: agentType, limit } }),
  getLatest: (agentType) => axios.get(`/agents/latest/${agentType}`),
};

// Scheduled Reminders API
export const scheduledApi = {
  getAll: (upcoming = true) => axios.get(`/scheduled?upcoming=${upcoming}`),
  create: (data) => axios.post('/scheduled', data),
  update: (id, data) => axios.put(`/scheduled/${id}`, data),
  delete: (id) => axios.delete(`/scheduled/${id}`),
  sendNow: (id) => axios.post(`/scheduled/${id}/send`),
};

// Auth API
export const authApi = {
  login: (email, password) => axios.post('/login', { email, password }),
  logout: () => axios.post('/logout'),
  verify: () => axios.get('/verify'),
  changePassword: (current_password, new_password) =>
    axios.post('/change-password', { current_password, new_password }),
};

// AI Assistant API
export const aiApi = {
  // Chat
  chat: (message, conversationId = null) => axios.post('/api/ai/chat', { message, conversation_id: conversationId }),
  getConversations: () => axios.get('/api/ai/conversations'),
  getConversationMessages: (conversationId) => axios.get(`/api/ai/conversations/${conversationId}/messages`),

  // System operations
  executeCommand: (command, conversationId = null, timeout = 60) =>
    axios.post('/api/ai/execute', { command, conversation_id: conversationId, timeout }),

  // System metrics
  getSystemMetrics: () => axios.get('/api/ai/system/metrics'),

  // Cron jobs
  listCronJobs: () => axios.get('/api/ai/cron/list'),
  createCronJob: (name, command, schedule, description = '', enabled = true) =>
    axios.post('/api/ai/cron/create', { name, command, schedule, description, enabled }),
  deleteCronJob: (jobId) => axios.delete(`/api/ai/cron/delete/${jobId}`),

  // Logs
  getSystemCommandLogs: (limit = 50) => axios.get(`/api/ai/logs/system?limit=${limit}`),
  getAppLogs: () => axios.get('/api/ai/logs/app'),

  // Database
  query: (query, allowWrite = false) => axios.post('/api/ai/db/query', { query, allow_write: allowWrite }),

  // Files
  readFile: (path) => axios.post('/api/ai/files/read', { path }),
  writeFile: (path, content, mode = 'w') => axios.post('/api/ai/files/write', { path, content, mode }),

  // Processes
  listProcesses: () => axios.get('/api/ai/processes'),
  killProcess: (pid) => axios.post(`/api/ai/processes/${pid}/kill`),
};

// Agent Sessions API (for autonomous agent system)
export const agentApi = {
  listSessions: (status = null, limit = 20, offset = 0) =>
    axios.get('/api/agent/sessions', { params: { status, limit, offset } }),
  getSession: (sessionId) => axios.get(`/api/agent/sessions/${sessionId}`),
  createSession: (goal, templateId = null) =>
    axios.post('/api/agent/sessions', { goal, template_id: templateId }),
  cancelSession: (sessionId) => axios.post(`/api/agent/sessions/${sessionId}/cancel`),
  approveAction: (sessionId, stepId, approved) =>
    axios.post(`/api/agent/sessions/${sessionId}/approve`, { step_id: stepId, approved }),
};
