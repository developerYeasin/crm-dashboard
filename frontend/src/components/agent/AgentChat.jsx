import { useState, useRef, useEffect } from 'react';
import { FiSend, FiLoader, FiSquare, FiChevronDown, FiChevronUp, FiClock, FiInfo, FiWifi, FiWifiOff, FiPlay, FiRotateCcw, FiTerminal, FiAlertTriangle, FiCheckCircle, FiXCircle, FiPackage, FiFileText, FiCheckSquare } from 'react-icons/fi';
import useAgentSession from '../../hooks/useAgentSession';
import ApprovalDialog from './ApprovalDialog';

/**
 * AgentChat - Modern interface for interacting with the autonomous agent.
 *
 * Features:
 * - Real-time streaming of thoughts, actions, observations
 * - Visual step timeline with expandable details
 * - Approval workflow for sensitive actions
 * - Responsive design with animations
 */

export default function AgentChat({ sessionId, onBack }) {
  const {
    session,
    steps,
    currentThought,
    pendingApproval,
    isConnected,
    error,
    startAgent,
    approveAction,
    cancelAgent,
    isActive,
    fetchSessions,
    fetchTemplates
  } = useAgentSession({ sessionId });

  const [goal, setGoal] = useState('');
  const [selectedTemplate, setSelectedTemplate] = useState(null);
  const [templates, setTemplates] = useState([]);
  const [expandedSteps, setExpandedSteps] = useState({});
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  // Load templates on mount
  useEffect(() => {
    const loadTemplates = async () => {
      const tmpls = await fetchTemplates();
      if (tmpls) setTemplates(tmpls);
    };
    loadTemplates();
  }, [fetchTemplates]);

  // Auto-scroll to bottom when new content arrives
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [steps, currentThought]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!goal.trim() || isActive) return;

    await startAgent(goal, selectedTemplate);
    setGoal('');
  };

  const toggleStepExpansion = (stepIndex) => {
    setExpandedSteps(prev => ({
      ...prev,
      [stepIndex]: !prev[stepIndex]
    }));
  };

  const formatTime = (dateStr) => {
    if (!dateStr) return '';
    return new Date(dateStr).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  const getActionIcon = (actionName) => {
    const icons = {
      'execute_shell_command': <FiTerminal />,
      'read_file': <FiInfo />,
      'write_file': <FiSend />,
      'list_directory': <FiInfo />,
      'query_database': <FiTerminal />,
      'get_system_metrics': <FiClock />,
      'search_knowledge_base': <FiWifi />,
      'query_orders': <FiPackage />,
      'get_order_details': <FiFileText />,
      'create_task': <FiCheckSquare />,
      'update_task_status': <FiRotateCcw />,
    };
    return icons[actionName] || <FiPlay />;
  };

  const getStatusIcon = (step) => {
    if (step.observation_error) return <FiXCircle className="text-red-500" />;
    if (step.observation) return <FiCheckCircle className="text-green-500" />;
    return <FiLoader className="animate-spin text-purple-500" />;
  };

  const getRiskBadgeClass = (riskLevel) => {
    switch (riskLevel) {
      case 'high': return 'bg-red-100 text-red-800 border-red-300 dark:bg-red-900/30 dark:text-red-300 dark:border-red-800';
      case 'medium': return 'bg-yellow-100 text-yellow-800 border-yellow-300 dark:bg-yellow-900/30 dark:text-yellow-300 dark:border-yellow-800';
      default: return 'bg-green-100 text-green-800 border-green-300 dark:bg-green-900/30 dark:text-green-300 dark:border-green-800';
    }
  };

  // Example prompts for empty state
  const examplePrompts = [
    'List all Python files in the backend directory',
    'Check server disk usage and report',
    'Search knowledge base for "user authentication"',
    'Show me all orders with COD payment',
    'Create a high-priority task: Review Q1 sales report',
    'Get details for order #123',
  ];

  return (
    <div className="flex flex-col h-full bg-gray-50 dark:bg-gray-900">
      {/* Header */}
      <div className="px-6 py-4 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
        <div className="flex items-center gap-3">
          {onBack && (
            <button onClick={onBack} className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors">
              ←
            </button>
          )}
          <div className="flex items-center gap-2">
            <div className={`p-2 rounded-lg ${isConnected ? 'bg-green-100 dark:bg-green-900/30' : 'bg-red-100 dark:bg-red-900/30'}`}>
              {isConnected ? <FiWifi className="w-4 h-4 text-green-600 dark:text-green-400" /> : <FiWifiOff className="w-4 h-4 text-red-600 dark:text-red-400" />}
            </div>
            <div>
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                Autonomous Agent
              </h2>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                {isActive ? (
                  <span className="flex items-center gap-1">
                    <FiLoader className="w-3 h-3 animate-spin" />
                    Running...
                  </span>
                ) : (
                  'Configure a task for the agent'
                )}
              </p>
            </div>
          </div>
        </div>
        {session && (
          <div className="text-sm text-gray-500 dark:text-gray-400">
            Session #{session.id}
          </div>
        )}
      </div>

      {/* Main Content */}
      <div className="flex-1 overflow-y-auto p-6">
        {!session ? (
          // Empty state - configuration
          <div className="max-w-2xl mx-auto">
            <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-8 text-center">
              <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-gradient-to-br from-purple-500 to-pink-600 flex items-center justify-center text-2xl">
                🤖
              </div>
              <h3 className="text-xl font-bold text-gray-900 dark:text-white mb-2">
                Autonomous Agent Framework
              </h3>
              <p className="text-gray-600 dark:text-gray-400 mb-6 max-w-md mx-auto">
                The agent can execute multi-step tasks using tools like shell commands,
                file operations, database queries, and knowledge base search.
              </p>

              {/* Template selector */}
              {templates.length > 0 && (
                <div className="mb-6 text-left">
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Agent Template (optional)
                  </label>
                  <select
                    value={selectedTemplate || ''}
                    onChange={(e) => setSelectedTemplate(e.target.value ? Number(e.target.value) : null)}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg dark:bg-gray-700 dark:text-white focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                  >
                    <option value="">Default (General Purpose)</option>
                    {templates.map(t => (
                      <option key={t.id} value={t.id}>{t.name} - {t.description?.substring(0, 60) || ''}...</option>
                    ))}
                  </select>
                </div>
              )}

              {/* Example prompts */}
              <div className="mb-6 text-left">
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Try an example:
                </label>
                <div className="flex flex-wrap gap-2">
                  {examplePrompts.map(prompt => (
                    <button
                      key={prompt}
                      onClick={() => setGoal(prompt)}
                      className="px-3 py-1.5 bg-gray-100 hover:bg-purple-100 dark:bg-gray-700 dark:hover:bg-purple-900/30 text-gray-800 dark:text-gray-200 rounded-full text-sm transition-colors"
                    >
                      {prompt}
                    </button>
                  ))}
                </div>
              </div>

              {/* Goal input */}
              <form onSubmit={handleSubmit}>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2 text-left">
                  What should the agent do?
                </label>
                <textarea
                  ref={inputRef}
                  value={goal}
                  onChange={(e) => setGoal(e.target.value)}
                  placeholder="Describe your task in detail..."
                  className="w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-xl dark:bg-gray-700 dark:text-white focus:ring-2 focus:ring-purple-500 focus:border-transparent resize-none transition-shadow"
                  rows={3}
                />
                <div className="mt-4 flex justify-end items-center gap-3">
                  {error && (
                    <span className="text-sm text-red-600 dark:text-red-400">{error}</span>
                  )}
                  <button
                    type="submit"
                    disabled={!goal.trim() || isActive}
                    className="flex items-center gap-2 px-6 py-2.5 bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 text-white rounded-xl font-medium transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed shadow-md hover:shadow-lg"
                  >
                    <FiSend className="w-4 h-4" />
                    Start Agent
                  </button>
                </div>
              </form>
            </div>

            {/* Info cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-6">
              <div className="bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
                <div className="text-2xl mb-2">💡</div>
                <h4 className="font-semibold text-gray-900 dark:text-white mb-1">Reasoning Loop</h4>
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  The agent thinks step-by-step and chooses the best tool for each subtask.
                </p>
              </div>
              <div className="bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
                <div className="text-2xl mb-2">🛡️</div>
                <h4 className="font-semibold text-gray-900 dark:text-white mb-1">Human-in-the-Loop</h4>
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  Sensitive operations require your approval before execution.
                </p>
              </div>
              <div className="bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
                <div className="text-2xl mb-2">📊</div>
                <h4 className="font-semibold text-gray-900 dark:text-white mb-1">Full Visibility</h4>
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  Watch the agent's thought process and tool results in real-time.
                </p>
              </div>
            </div>
          </div>
        ) : (
          // Active session
          <div className="max-w-4xl mx-auto space-y-6">
            {/* Session header */}
            <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-semibold text-gray-900 dark:text-white">{session.title}</h3>
                  <div className="flex items-center gap-3 mt-1 text-sm text-gray-500 dark:text-gray-400">
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${session.status === 'running' ? 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300' : 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300'}`}>
                      {session.status}
                    </span>
                    <span>{steps.length} steps</span>
                    {session.created_at && (
                      <span>Started {formatTime(session.created_at)}</span>
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {isActive && (
                    <button
                      onClick={cancelAgent}
                      className="flex items-center gap-1 px-3 py-1.5 bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400 hover:bg-red-200 dark:hover:bg-red-900/50 rounded-lg text-sm font-medium transition"
                      title="Cancel agent"
                    >
                      <FiSquare className="w-3 h-3" />
                      Stop
                    </button>
                  )}
                </div>
              </div>
            </div>

            {/* Current thought */}
            {currentThought && (
              <div className="bg-gradient-to-br from-purple-50 to-pink-50 dark:from-purple-900/20 dark:to-pink-900/20 border border-purple-200 dark:border-purple-800 rounded-xl p-5 animate-pulse">
                <div className="flex items-start gap-3">
                  <div className="p-2 rounded-lg bg-purple-100 dark:bg-purple-900/50 mt-0.5">
                    <FiInfo className="w-5 h-5 text-purple-600 dark:text-purple-400" />
                  </div>
                  <div className="flex-1">
                    <h4 className="text-sm font-medium text-purple-900 dark:text-purple-300 mb-1">Thinking...</h4>
                    <p className="text-gray-800 dark:text-gray-200 leading-relaxed">
                      {currentThought}
                    </p>
                  </div>
                </div>
              </div>
            )}

            {/* Steps timeline */}
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                  Execution Steps
                </h3>
                <span className="text-sm text-gray-500 dark:text-gray-400">
                  {steps.length} total
                </span>
              </div>

              {steps.length === 0 ? (
                <div className="text-center py-12 text-gray-500 dark:text-gray-400 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700">
                  <FiClock className="w-12 h-12 mx-auto mb-3 opacity-50" />
                  <p>No steps yet. The agent is initializing...</p>
                </div>
              ) : (
                <div className="relative">
                  {/* Vertical line */}
                  <div className="absolute left-4 top-2 bottom-2 w-0.5 bg-gray-200 dark:bg-gray-700 -z-10" style={{ left: '30px' }}></div>

                  {steps.map((step, idx) => (
                    <div
                      key={idx}
                      className="relative group"
                    >
                      {/* Step indicator */}
                      <div className="absolute left-0 top-6 w-8 h-8 rounded-full bg-white dark:bg-gray-800 border-2 border-purple-500 flex items-center justify-center z-10">
                        {getStatusIcon(step)}
                      </div>

                      {/* Step card */}
                      <div className="ml-14 mb-4">
                        <div
                          className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden transition-shadow hover:shadow-md"
                        >
                          {/* Card header */}
                          <button
                            onClick={() => toggleStepExpansion(idx)}
                            className="w-full px-4 py-3 flex items-center justify-between hover:bg-gray-50 dark:hover:bg-gray-900/50 transition-colors text-left"
                          >
                            <div className="flex items-center gap-3 flex-1">
                              <span className="text-lg" title={step.action?.tool_name || 'Thinking'}>
                                {step.action?.tool_name ? getActionIcon(step.action.tool_name) : <FiInfo />}
                              </span>
                              <div className="flex flex-col min-w-0">
                                <div className="flex items-center gap-2 flex-wrap">
                                  <span className="font-medium text-gray-900 dark:text-white truncate">
                                    {step.action?.tool_name || 'Thinking'}
                                  </span>
                                  {step.action?.risk_level && (
                                    <span className={`px-2 py-0.5 text-xs font-medium rounded-full border ${getRiskBadgeClass(step.action.risk_level)}`}>
                                      {step.action.risk_level}
                                    </span>
                                  )}
                                </div>
                                <div className="text-xs text-gray-500 dark:text-gray-400 mt-0.5 truncate">
                                  {step.thought.substring(0, 80)}...
                                </div>
                              </div>
                            </div>
                            <div className="text-gray-400 ml-2">
                              {expandedSteps[idx] ? <FiChevronUp /> : <FiChevronDown />}
                            </div>
                          </button>

                          {/* Expanded details */}
                          {expandedSteps[idx] && (
                            <div className="px-4 py-3 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900/50 space-y-4">
                              {/* Thought */}
                              <div>
                                <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Thought</h4>
                                <p className="text-sm text-gray-900 dark:text-white whitespace-pre-wrap leading-relaxed">
                                  {step.thought}
                                </p>
                              </div>

                              {/* Action */}
                              {step.action && (
                                <div>
                                  <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Action</h4>
                                  <div className="bg-gray-900 dark:bg-gray-950 text-gray-100 p-3 rounded-lg font-mono text-xs overflow-x-auto">
                                    <div className="text-purple-400 mb-1 font-bold">
                                      {step.action.tool_name}
                                    </div>
                                    <pre className="text-gray-300 whitespace-pre-wrap">
                                      {JSON.stringify(step.action.arguments, null, 2)}
                                    </pre>
                                  </div>
                                </div>
                              )}

                              {/* Observation */}
                              {step.observation !== null && (
                                <div>
                                  <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Observation</h4>
                                  {step.observation_error ? (
                                    <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-800 dark:text-red-300 p-3 rounded-lg text-sm font-mono whitespace-pre-wrap">
                                      {step.observation_error}
                                    </div>
                                  ) : (
                                    <pre className="text-sm text-gray-900 dark:text-white bg-gray-100 dark:bg-gray-800 p-3 rounded-lg overflow-x-auto whitespace-pre-wrap max-h-60 overflow-y-auto font-mono">
                                      {typeof step.observation === 'string' ? step.observation : JSON.stringify(step.observation, null, 2)}
                                    </pre>
                                  )}
                                </div>
                              )}

                              {/* Execution time */}
                              {step.execution_time_ms && (
                                <div className="text-xs text-gray-500 dark:text-gray-400 flex items-center gap-1">
                                  <FiClock className="w-3 h-3" />
                                  Executed in {step.execution_time_ms}ms
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}

                  {/* Scroll anchor */}
                  <div ref={messagesEndRef} />
                </div>
              )}

              {/* Completion summary */}
              {session.status === 'completed' && steps.length > 0 && (
                <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-xl p-6 text-center">
                  <div className="w-12 h-12 mx-auto mb-3 rounded-full bg-green-100 dark:bg-green-900/50 flex items-center justify-center">
                    <FiCheckCircle className="w-6 h-6 text-green-600 dark:text-green-400" />
                  </div>
                  <h4 className="text-lg font-semibold text-green-800 dark:text-green-300 mb-2">
                    Agent Completed Successfully
                  </h4>
                  <p className="text-green-700 dark:text-green-400 mb-4">
                    {session.final_result?.summary || 'Task completed.'}
                  </p>
                  <button
                    onClick={() => {
                      setSession(null);
                      setSteps([]);
                      setCurrentThought('');
                    }}
                    className="inline-flex items-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg font-medium transition"
                  >
                    <FiRotateCcw className="w-4 h-4" />
                    New Session
                  </button>
                </div>
              )}

              {/* Failure state */}
              {session.status === 'failed' && (
                <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl p-6 text-center">
                  <div className="w-12 h-12 mx-auto mb-3 rounded-full bg-red-100 dark:bg-red-900/50 flex items-center justify-center">
                    <FiXCircle className="w-6 h-6 text-red-600 dark:text-red-400" />
                  </div>
                  <h4 className="text-lg font-semibold text-red-800 dark:text-red-300 mb-2">
                    Agent Failed
                  </h4>
                  <p className="text-red-700 dark:text-red-400 mb-4">
                    {session.final_result?.error || 'An unknown error occurred.'}
                  </p>
                  <button
                    onClick={() => {
                      setSession(null);
                      setSteps([]);
                      setCurrentThought('');
                    }}
                    className="inline-flex items-center gap-2 px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg font-medium transition"
                  >
                    <FiRotateCcw className="w-4 h-4" />
                    Try Again
                  </button>
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Input area */}
      {session && isActive && (
        <div className="px-6 py-4 bg-white dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700">
          <div className="max-w-4xl mx-auto flex items-center gap-3">
            <FiLoader className="w-5 h-5 text-purple-600 animate-spin" />
            <span className="text-gray-700 dark:text-gray-300">
              Agent is working...
            </span>
            <span className="text-sm text-gray-500 dark:text-gray-400 ml-auto">
              Steps: {steps.length}
            </span>
          </div>
        </div>
      )}

      {/* Error display */}
      {error && (
        <div className="fixed bottom-4 right-4 max-w-md bg-red-100 dark:bg-red-900/30 border border-red-300 dark:border-red-800 text-red-800 dark:text-red-300 p-4 rounded-lg shadow-lg z-50">
          <div className="font-medium mb-1">Error</div>
          <div className="text-sm">{error}</div>
        </div>
      )}

      {/* Approval dialog */}
      {pendingApproval && (
        <ApprovalDialog
          approval={pendingApproval}
          onApprove={(comment) => approveAction(pendingApproval.step_id, true, comment)}
          onDeny={(comment) => approveAction(pendingApproval.step_id, false, comment)}
        />
      )}
    </div>
  );
}
