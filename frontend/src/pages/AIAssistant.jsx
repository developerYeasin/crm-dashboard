import { useState, useEffect, useRef } from 'react'
import { aiApi } from '../services/api'
import { useAuth } from '../contexts/AuthContext'
import {
  ChatBubbleLeftRightIcon,
  CommandLineIcon,
  ClockIcon,
  CogIcon,
  SparklesIcon
} from '@heroicons/react/24/outline'

function AIAssistant() {
  const { user } = useAuth()
  const [conversations, setConversations] = useState([])
  const [selectedConversation, setSelectedConversation] = useState(null)
  const [messages, setMessages] = useState([])
  const [inputMessage, setInputMessage] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [activeTab, setActiveTab] = useState('chat') // chat, cron, logs, metrics
  const [cronJobs, setCronJobs] = useState([])
  const [commandHistory, setCommandHistory] = useState([])
  const [systemMetrics, setSystemMetrics] = useState(null)
  const [showCommandModal, setShowCommandModal] = useState(false)
  const [execCommand, setExecCommand] = useState('')
  const [commandOutput, setCommandOutput] = useState('')
  const [newCronForm, setNewCronForm] = useState({ name: '', command: '', schedule: '* * * * *' })

  const messagesEndRef = useRef(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  useEffect(() => {
    loadConversations()
    loadCronJobs()
    loadCommandHistory()
    loadSystemMetrics()
  }, [])

  const loadConversations = async () => {
    try {
      const res = await aiApi.getConversations()
      setConversations(Array.isArray(res.data) ? res.data : [])
    } catch (error) {
      console.error('Failed to load conversations:', error)
      setConversations([])
    }
  }

  const loadCronJobs = async () => {
    try {
      const res = await aiApi.listCronJobs()
      setCronJobs(Array.isArray(res.data) ? res.data : [])
    } catch (error) {
      console.error('Failed to load cron jobs:', error)
      setCronJobs([])
    }
  }

  const loadCommandHistory = async () => {
    try {
      const res = await aiApi.getSystemCommandLogs(20)
      setCommandHistory(Array.isArray(res.data) ? res.data : [])
    } catch (error) {
      console.error('Failed to load command history:', error)
      setCommandHistory([])
    }
  }

  const loadSystemMetrics = async () => {
    try {
      const res = await aiApi.getSystemMetrics()
      setSystemMetrics(res.data && typeof res.data === 'object' && !res.data.error ? res.data : null)
    } catch (error) {
      console.error('Failed to load system metrics:', error)
      setSystemMetrics(null)
    }
  }

  const loadConversationMessages = async (convId) => {
    try {
      const res = await aiApi.getConversationMessages(convId)
      setMessages(Array.isArray(res.data) ? res.data : [])
      setSelectedConversation(convId)
    } catch (error) {
      console.error('Failed to load messages:', error)
      setMessages([])
    }
  }

  const sendMessage = async () => {
    if (!inputMessage.trim()) return

    setIsLoading(true)
    try {
      const res = await aiApi.chat(inputMessage, selectedConversation)
      const { conversation_id, response } = res.data

      // If new conversation, reload conversations list
      if (!selectedConversation) {
        setSelectedConversation(conversation_id)
        loadConversations()
      }

      // Reload messages
      await loadConversationMessages(conversation_id)
      setInputMessage('')
    } catch (error) {
      console.error('Failed to send message:', error)
      } finally {
      setIsLoading(false)
    }
  }

  const executeManualCommand = async () => {
    if (!execCommand.trim()) return

    try {
      const res = await aiApi.executeCommand(execCommand, selectedConversation)
      setCommandOutput(`Exit code: ${res.data.exit_code}\n\nSTDOUT:\n${res.data.stdout}\n\nSTDERR:\n${res.data.stderr}`)
      loadCommandHistory()
    } catch (error) {
      setCommandOutput(`Error: ${error.response?.data?.error || error.message}`)
    }
  }

  const createCronJob = async (e) => {
    e.preventDefault()
    try {
      await aiApi.createCronJob(
        newCronForm.name,
        newCronForm.command,
        newCronForm.schedule,
        newCronForm.description
      )
      setNewCronForm({ name: '', command: '', schedule: '* * * * *' })
      loadCronJobs()
      } catch (error) {
      }
  }

  const deleteCronJob = async (jobId) => {
    if (!confirm('Delete this cron job?')) return
    try {
      await aiApi.deleteCronJob(jobId)
      loadCronJobs()
    } catch (error) {
      }
  }

  const renderChatTab = () => (
    <div className="flex h-full">
      {/* Conversations sidebar */}
      <div className="w-64 border-r border-gray-700 bg-gray-900 p-4 overflow-y-auto">
        <button
          onClick={() => {
            setSelectedConversation(null)
            setMessages([])
          }}
          className="w-full mb-4 px-4 py-2 bg-primary-600 hover:bg-primary-700 rounded-lg text-sm font-medium"
        >
          New Chat
        </button>

        <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">
          Conversations
        </h3>

        {conversations.length === 0 ? (
          <p className="text-gray-500 text-sm">No conversations yet</p>
        ) : (
          <div className="space-y-1">
            {conversations.map(conv => (
              <button
                key={conv.id}
                onClick={() => loadConversationMessages(conv.id)}
                className={`w-full text-left px-3 py-2 rounded-lg text-sm truncate ${
                  selectedConversation === conv.id
                    ? 'bg-primary-900 text-primary-300'
                    : 'hover:bg-gray-800 text-gray-300'
                }`}
              >
                {conv.title || `Chat ${conv.id}`}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Chat area */}
      <div className="flex-1 flex flex-col bg-gray-950">
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {messages.length === 0 ? (
            <div className="text-center text-gray-500 mt-20">
              <ChatBubbleLeftRightIcon className="mx-auto h-12 w-12 mb-4 opacity-50" />
              <p className="text-lg">AI Assistant Ready</p>
              <p className="text-sm mt-2 max-w-md mx-auto">
                I can help you manage your CRM, execute system commands, create cron jobs,
                analyze logs, and answer questions about your orders and system.
              </p>
            </div>
          ) : (
            messages.map(msg => (
              <div
                key={msg.id}
                className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`max-w-3xl px-4 py-3 rounded-lg ${
                    msg.role === 'user'
                      ? 'bg-primary-600 text-white'
                      : 'bg-gray-800 text-gray-100'
                  }`}
                >
                  <p className="whitespace-pre-wrap">{msg.content}</p>

                  {msg.action_taken && (
                    <div className="mt-2 pt-2 border-t border-gray-600 text-xs text-gray-400">
                      <span className="font-semibold">Action:</span> {msg.action_taken}
                    </div>
                  )}

                  {msg.command_executed && (
                    <div className="mt-1">
                      <pre className="text-xs bg-gray-900 p-2 rounded overflow-x-auto max-h-48">
                        <code>{msg.command_output || msg.command_executed}</code>
                      </pre>
                    </div>
                  )}
                </div>
              </div>
            ))
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input area */}
        <div className="p-4 border-t border-gray-700 bg-gray-900">
          <div className="flex gap-2">
            <input
              type="text"
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && !isLoading && sendMessage()}
              placeholder="Ask me to do anything... query database, run commands, create cron jobs, check logs..."
              className="flex-1 px-4 py-3 bg-gray-800 border border-gray-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 text-white placeholder-gray-500"
              disabled={isLoading}
            />
            <button
              onClick={sendMessage}
              disabled={isLoading || !inputMessage.trim()}
              className="px-6 py-3 bg-primary-600 hover:bg-primary-700 disabled:bg-gray-700 disabled:cursor-not-allowed rounded-lg font-medium flex items-center"
            >
              {isLoading ? (
                <div className="animate-spin h-5 w-5 border-b-2 border-white rounded-full"></div>
              ) : (
                'Send'
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  )

  const renderCronTab = () => (
    <div className="p-6">
      <h2 className="text-2xl font-bold text-white mb-6">Cron Job Manager</h2>

      {/* Create new cron job */}
      <div className="bg-gray-900 border border-gray-700 rounded-lg p-6 mb-6">
        <h3 className="text-lg font-medium text-white mb-4">Create New Cron Job</h3>
        <form onSubmit={createCronJob} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">Name</label>
              <input
                type="text"
                value={newCronForm.name}
                onChange={(e) => setNewCronForm({ ...newCronForm, name: e.target.value })}
                className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:ring-2 focus:ring-primary-500 focus:outline-none"
                placeholder="Daily backup"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">Schedule (cron)</label>
              <input
                type="text"
                value={newCronForm.schedule}
                onChange={(e) => setNewCronForm({ ...newCronForm, schedule: e.target.value })}
                className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:ring-2 focus:ring-primary-500 focus:outline-none"
                placeholder="0 2 * * *"
                required
              />
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">Command</label>
            <input
              type="text"
              value={newCronForm.command}
              onChange={(e) => setNewCronForm({ ...newCronForm, command: e.target.value })}
              className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:ring-2 focus:ring-primary-500 focus:outline-none"
              placeholder="python /root/order-tracker/backend/backup.py"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">Description</label>
            <input
              type="text"
              value={newCronForm.description}
              onChange={(e) => setNewCronForm({ ...newCronForm, description: e.target.value })}
              className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:ring-2 focus:ring-primary-500 focus:outline-none"
              placeholder="Backup database daily at 2 AM"
            />
          </div>
          <button
            type="submit"
            className="px-4 py-2 bg-primary-600 hover:bg-primary-700 rounded-lg font-medium"
          >
            Create Cron Job
          </button>
        </form>
      </div>

      {/* Cron jobs list */}
      <div className="bg-gray-900 border border-gray-700 rounded-lg overflow-hidden">
        <table className="min-w-full">
          <thead className="bg-gray-800">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase">Name</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase">Schedule</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase">Command</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase">Created By</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase">Status</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-700">
            {cronJobs.map(job => (
              <tr key={job.id}>
                <td className="px-4 py-3 text-sm text-white">
                  <div>{job.name}</div>
                  <div className="text-xs text-gray-500">{job.description}</div>
                </td>
                <td className="px-4 py-3 text-sm font-mono text-green-400">{job.schedule}</td>
                <td className="px-4 py-3 text-sm font-mono text-gray-300 max-w-md truncate">{job.command}</td>
                <td className="px-4 py-3 text-sm text-gray-400">{job.created_by}</td>
                <td className="px-4 py-3 text-sm">
                  <span className={`px-2 py-1 rounded text-xs font-medium ${job.enabled ? 'bg-green-900 text-green-300' : 'bg-gray-700 text-gray-400'}`}>
                    {job.enabled ? 'Enabled' : 'Disabled'}
                  </span>
                </td>
                <td className="px-4 py-3 text-sm">
                  <button
                    onClick={() => deleteCronJob(job.id)}
                    className="text-red-400 hover:text-red-300 text-sm"
                  >
                    Delete
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        {cronJobs.length === 0 && (
          <div className="text-center py-8 text-gray-500">No cron jobs created yet</div>
        )}
      </div>
    </div>
  )

  const renderLogsTab = () => (
    <div className="p-6">
      <h2 className="text-2xl font-bold text-white mb-6">System Command Logs</h2>

      <div className="space-y-3">
        {commandHistory.length === 0 ? (
          <div className="text-gray-500 text-center py-8">No commands executed yet</div>
        ) : (
          commandHistory.map(log => (
            <div key={log.id} className="bg-gray-900 border border-gray-700 rounded-lg p-4">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <span className={`px-2 py-1 rounded text-xs font-medium ${log.status === 'success' ? 'bg-green-900 text-green-300' : 'bg-red-900 text-red-300'}`}>
                    {log.status.toUpperCase()}
                  </span>
                  <span className="text-gray-400">Exit code: {log.exit_code}</span>
                  <span className="text-gray-500 text-sm">({log.execution_time?.toFixed(2)}s)</span>
                </div>
                <div className="text-gray-500 text-sm">{new Date(log.executed_at).toLocaleString()}</div>
              </div>

              <div className="font-mono text-sm text-primary-300 mb-2">
                {log.command}
              </div>

              {log.output && (
                <pre className="text-xs bg-gray-950 p-3 rounded border border-gray-800 overflow-x-auto max-h-64">
                  <code>{log.output}</code>
                </pre>
              )}

              <div className="text-gray-500 text-xs mt-2">
                Executed by: {log.executed_by}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )

  const renderMetricsTab = () => {
    if (!systemMetrics) {
      return <div className="p-6 text-gray-500">Loading metrics...</div>
    }

    return (
      <div className="p-6">
        <h2 className="text-2xl font-bold text-white mb-6">System Metrics</h2>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {/* CPU */}
          <div className="bg-gray-900 border border-gray-700 rounded-lg p-4">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-lg font-medium text-white">CPU</h3>
              <CogIcon className="h-6 w-6 text-blue-400" />
            </div>
            <div className="space-y-2">
              <div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-400">Usage</span>
                  <span className="text-white">{systemMetrics.cpu.percent}%</span>
                </div>
                <div className="w-full bg-gray-700 rounded-full h-2">
                  <div
                    className="bg-blue-500 h-2 rounded-full"
                    style={{ width: `${systemMetrics.cpu.percent}%` }}
                  ></div>
                </div>
              </div>
              <div className="text-sm text-gray-400">
                Cores: {systemMetrics.cpu.count}
              </div>
              {systemMetrics.cpu.freq && (
                <div className="text-sm text-gray-400">
                  Frequency: {(systemMetrics.cpu.freq.current / 1000).toFixed(2)} GHz
                </div>
              )}
            </div>
          </div>

          {/* Memory */}
          <div className="bg-gray-900 border border-gray-700 rounded-lg p-4">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-lg font-medium text-white">Memory</h3>
              <div className="h-6 w-6 text-green-400">RAM</div>
            </div>
            <div className="space-y-2">
              <div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-400">Used</span>
                  <span className="text-white">{systemMetrics.memory.percent}%</span>
                </div>
                <div className="w-full bg-gray-700 rounded-full h-2">
                  <div
                    className="bg-green-500 h-2 rounded-full"
                    style={{ width: `${systemMetrics.memory.percent}%` }}
                  ></div>
                </div>
              </div>
              <div className="text-sm text-gray-400">
                {systemMetrics.memory.used_gb.toFixed(1)} GB / {systemMetrics.memory.total_gb.toFixed(1)} GB
              </div>
              <div className="text-sm text-gray-400">
                Available: {systemMetrics.memory.available_gb.toFixed(1)} GB
              </div>
            </div>
          </div>

          {/* Disk */}
          <div className="bg-gray-900 border border-gray-700 rounded-lg p-4">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-lg font-medium text-white">Disk</h3>
              <div className="h-6 w-6 text-yellow-400">HDD</div>
            </div>
            <div className="space-y-2">
              <div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-400">Used</span>
                  <span className="text-white">{systemMetrics.disk.percent}%</span>
                </div>
                <div className="w-full bg-gray-700 rounded-full h-2">
                  <div
                    className="bg-yellow-500 h-2 rounded-full"
                    style={{ width: `${systemMetrics.disk.percent}%` }}
                  ></div>
                </div>
              </div>
              <div className="text-sm text-gray-400">
                {systemMetrics.disk.used_gb.toFixed(1)} GB / {systemMetrics.disk.total_gb.toFixed(1)} GB
              </div>
              <div className="text-sm text-gray-400">
                Free: {systemMetrics.disk.free_gb.toFixed(1)} GB
              </div>
            </div>
          </div>

          {/* Process Count */}
          <div className="bg-gray-900 border border-gray-700 rounded-lg p-4">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-lg font-medium text-white">Processes</h3>
              <ClockIcon className="h-6 w-6 text-purple-400" />
            </div>
            <div className="text-4xl font-bold text-white">{systemMetrics.processes?.count || systemMetrics.processes || 0}</div>
            <div className="text-sm text-gray-400 mt-1">Running processes</div>

            <div className="mt-4 space-y-1">
              <h4 className="text-xs font-semibold text-gray-400 uppercase">Top by Memory</h4>
              {Array.isArray(systemMetrics.processes?.top_memory) && systemMetrics.processes.top_memory.map((p, idx) => (
                <div key={idx} className="text-xs flex justify-between text-gray-300">
                  <span>{p.name}</span>
                  <span>{(p.memory_mb / 1024).toFixed(1)} GB</span>
                </div>
              ))}
            </div>
          </div>

          {/* Network */}
          <div className="bg-gray-900 border border-gray-700 rounded-lg p-4 col-span-1 md:col-span-2 lg:col-span-1">
            <h3 className="text-lg font-medium text-white mb-3">Network I/O</h3>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <div className="text-sm text-gray-400">Bytes Sent</div>
                <div className="text-white">{(systemMetrics.network.io_counters.bytes_sent / (1024**2)).toFixed(2)} MB</div>
              </div>
              <div>
                <div className="text-sm text-gray-400">Bytes Received</div>
                <div className="text-white">{(systemMetrics.network.io_counters.bytes_recv / (1024**2)).toFixed(2)} MB</div>
              </div>
            </div>
          </div>
        </div>

        {/* Manual Command Execution */}
        <div className="mt-8 bg-gray-900 border border-gray-700 rounded-lg p-6">
          <h3 className="text-lg font-medium text-white mb-4 flex items-center gap-2">
            <CommandLineIcon className="h-5 w-5" />
            Manual Command Execution
          </h3>
          <p className="text-gray-400 text-sm mb-4">
            Execute shell commands on the server. Use with caution - some commands are blocked for safety.
          </p>

          <div className="flex gap-2">
            <input
              type="text"
              value={execCommand}
              onChange={(e) => setExecCommand(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && execCommand && executeManualCommand()}
              placeholder="Enter command (e.g., ls -la, df -h, tail -f app.log)"
              className="flex-1 px-4 py-3 bg-gray-800 border border-gray-700 rounded-lg text-white placeholder-gray-500 font-mono text-sm"
            />
            <button
              onClick={executeManualCommand}
              disabled={!execCommand.trim()}
              className="px-6 py-3 bg-green-600 hover:bg-green-700 disabled:bg-gray-700 disabled:cursor-not-allowed rounded-lg font-medium"
            >
              Execute
            </button>
          </div>

          {commandOutput && (
            <div className="mt-4">
              <h4 className="text-sm font-medium text-gray-300 mb-2">Output:</h4>
              <pre className="bg-gray-950 border border-gray-800 p-4 rounded-lg text-sm text-gray-300 overflow-x-auto max-h-96 whitespace-pre-wrap">
                {commandOutput}
              </pre>
            </div>
          )}
        </div>
      </div>
    )
  }

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="bg-gray-900 border-b border-gray-700 p-4">
        <h1 className="text-2xl font-bold text-white flex items-center gap-2">
          <ChatBubbleLeftRightIcon className="h-8 w-8 text-primary-500" />
          AI Assistant
        </h1>
      </div>

      {/* Tabs */}
      <div className="bg-gray-900 border-b border-gray-700 flex">
        {[
          { id: 'chat', label: 'Chat', icon: ChatBubbleLeftRightIcon },
          { id: 'cron', label: 'Cron Jobs', icon: ClockIcon },
          { id: 'logs', label: 'Command Logs', icon: CommandLineIcon },
          { id: 'metrics', label: 'System Metrics', icon: CogIcon },
        ].map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
              activeTab === tab.id
                ? 'border-primary-500 text-primary-400'
                : 'border-transparent text-gray-400 hover:text-gray-200'
            }`}
          >
            <tab.icon className="h-5 w-5" />
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="flex-1 overflow-hidden">
        {activeTab === 'chat' && renderChatTab()}
        {activeTab === 'cron' && renderCronTab()}
        {activeTab === 'logs' && renderLogsTab()}
        {activeTab === 'metrics' && renderMetricsTab()}
      </div>
    </div>
  )
}

export default AIAssistant
