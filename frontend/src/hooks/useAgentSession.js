import { useState, useCallback, useEffect, useRef, useMemo } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { agentApi } from '../services/api';
import { io } from 'socket.io-client';

/**
 * Custom hook for managing autonomous agent sessions.
 *
 * Features:
 * - Create and manage agent sessions
 * - Real-time streaming of agent thoughts, actions, observations via WebSocket
 * - Human-in-the-loop approval workflow
 * - Session history and persistence
 *
 * @param {Object} options
 * @param {number} [options.sessionId] - Optional existing session ID to resume
 * @returns {Object} Agent session state and actions
 */
export function useAgentSession(options = {}) {
  const { sessionId: initialSessionId } = options;
  const { token } = useAuth();

  // Session state
  const [session, setSession] = useState(null);
  const [steps, setSteps] = useState([]);
  const [currentThought, setCurrentThought] = useState('');
  const [pendingApproval, setPendingApproval] = useState(null);
  const [isConnected, setIsConnected] = useState(false);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [error, setError] = useState(null);

  // Refs for Socket.IO and pending data
  const socketRef = useRef(null);
  const sessionIdRef = useRef(initialSessionId);

  // Initialize Socket.IO connection
  const connectSocket = useCallback(() => {
    if (!token) {
      setError('No authentication token');
      return;
    }

    // Close existing connection
    if (socketRef.current) {
      socketRef.current.disconnect();
    }

    // Use current origin (Vite dev server proxies /socket.io to backend on port 8087)
    const socket = io(import.meta.env.VITE_WS_URL || window.location.origin, {
      transports: ['websocket', 'polling'],
      reconnection: true,
      reconnectionAttempts: 5,
      reconnectionDelay: 1000,
      path: '/socket.io'
    });

    socket.on('connect', () => {
      // Authenticate immediately after connection
      socket.emit('authenticate', { token });
    });

    socket.on('authenticated', (data) => {
      setIsConnected(true);
      setIsAuthenticated(true);
      setError(null);
    });

    socket.on('error', (data) => {
      console.error('Socket error:', data);
      if (data.message === 'Invalid token' || data.message === 'Authentication required') {
        setIsAuthenticated(false);
        setError('Authentication failed');
      }
    });

    socket.on('agent_started', (data) => {
      // Fetch session details when agent starts
      agentApi.getSession(data.session_id).then(res => {
        setSession(res.data.session);
        setSteps(res.data.steps || []);
      }).catch(err => {
        console.error('Failed to fetch session:', err);
        setError('Failed to load session');
      });
    });

    socket.on('agent_thinking', (data) => {
      setCurrentThought(data.thought);
    });

    socket.on('agent_action', (data) => {
      const newStep = {
        step: data.step,
        thought: data.thought,
        action: data.action,
        observation: null,
        observation_error: null
      };
      setSteps(prev => [...prev, newStep]);
      setCurrentThought('');
    });

    socket.on('agent_observation', (data) => {
      setSteps(prev => {
        const updated = [...prev];
        const lastIdx = updated.length - 1;
        if (lastIdx >= 0) {
          updated[lastIdx] = {
            ...updated[lastIdx],
            observation: data.observation,
            observation_error: data.error || null,
            success: data.success
          };
        }
        return updated;
      });
    });

    socket.on('awaiting_approval', (data) => {
      setPendingApproval({
        step_id: data.step_id,
        tool_call_id: data.tool_call_id,
        tool_name: data.tool_name,
        arguments: data.arguments,
        risk_level: data.risk_level,
        message: data.message
      });
    });

    socket.on('agent_completed', (data) => {
      setSession(prev => {
        if (!prev) return prev;
        return {
          ...prev,
          status: 'completed',
          final_result: data.final_result || data.result
        };
      });
      setIsConnected(false);
    });

    socket.on('agent_failed', (data) => {
      setSession(prev => {
        if (!prev) return prev;
        return {
          ...prev,
          status: 'failed',
          error: data.error || data.message
        };
      });
      setError(data.error || data.message);
      setIsConnected(false);
    });

    socket.on('agent_cancelled', (data) => {
      setSession(prev => {
        if (!prev) return prev;
        return {
          ...prev,
          status: 'cancelled'
        };
      });
      setIsConnected(false);
    });

    socket.on('agent_error', (data) => {
      console.error('Agent error:', data);
      setError(data.message || 'Agent error');
    });

    socket.on('disconnect', (reason) => {
      setIsConnected(false);
    });

    socket.on('error', (err) => {
      console.error('Socket.IO error:', err);
      setError('Connection error');
    });

    socketRef.current = socket;
    return socket;
  }, [token]);

  // Start a new agent session
  const startAgent = useCallback(async (goal, templateId = null) => {
    if (!goal?.trim()) {
      setError('Goal is required');
      return;
    }

    try {
      setError(null);
      setPendingApproval(null);
      setSteps([]);
      setCurrentThought('');

      // Create session via REST API
      const response = await agentApi.createSession(goal.trim(), templateId);
      const { session_id } = response.data;
      sessionIdRef.current = session_id;

      // Ensure socket is connected and authenticated
      if (!socketRef.current || !socketRef.current.connected) {
        connectSocket();
        // Wait for authentication
        await new Promise((resolve, reject) => {
          const maxWait = 10000; // 10 second timeout
          const startTime = Date.now();

          const checkAuth = () => {
            if (isAuthenticated) {
              resolve();
            } else if (Date.now() - startTime > maxWait) {
              reject(new Error('Authentication timeout'));
            } else {
              // Check again in 100ms
              setTimeout(checkAuth, 100);
            }
          };
          checkAuth();
        });
      }

      // Send start command via Socket.IO
      socketRef.current?.emit('start_agent', {
        session_id: session_id,
        goal: goal.trim(),
        template_id: templateId
      });

    } catch (err) {
      console.error('Failed to start agent:', err);
      setError(err.response?.data?.error || 'Failed to start agent');
    }
  }, [connectSocket, isAuthenticated]);

  // Approve or deny a pending action
  const approveAction = useCallback(async (stepId, approved, comment = '') => {
    if (!session) {
      setError('No active session');
      return;
    }

    try {
      await agentApi.approveAction(session.id, approved, comment);

      // Clear pending approval locally
      setPendingApproval(null);

      // Also send via socket to wake up agent immediately (optional)
      socketRef.current?.emit('approve_action', {
        session_id: session.id,
        step_id: stepId,
        approved: approved,
        comment: comment
      });

      // The agent will resume via polling/approval check
    } catch (err) {
      console.error('Failed to approve action:', err);
      setError(err.response?.data?.error || 'Failed to approve action');
    }
  }, [session]);

  // Cancel the running agent
  const cancelAgent = useCallback(async () => {
    if (!session) {
      setError('No active session');
      return;
    }

    try {
      await agentApi.cancelSession(session.id);
      setPendingApproval(null);

      // Send cancel via socket
      socketRef.current?.emit('cancel_agent', {
        session_id: session.id
      });

      // Agent will send agent_cancelled event
    } catch (err) {
      console.error('Failed to cancel agent:', err);
      setError(err.response?.data?.error || 'Failed to cancel agent');
    }
  }, [session]);

  // Load an existing session
  const loadSession = useCallback(async (sessionId) => {
    try {
      setError(null);
      const response = await agentApi.getSession(sessionId);
      const { session: sess, steps: stps, pending_approvals } = response.data;

      setSession(sess);
      setSteps(stps || []);

      if (pending_approvals?.length > 0) {
        setPendingApproval(pending_approvals[0]);
      }

      // Connect socket to receive live updates
      if (sess.status === 'running' || sess.status === 'awaiting_approval') {
        sessionIdRef.current = sessionId;
        if (!socketRef.current || !socketRef.current.connected) {
          connectSocket();
        }
      }
    } catch (err) {
      console.error('Failed to load session:', err);
      setError(err.response?.data?.error || 'Failed to load session');
    }
  }, [connectSocket]);

  // Fetch list of sessions
  const fetchSessions = useCallback(async (status = null, limit = 50) => {
    try {
      const params = new URLSearchParams({ limit: limit.toString() });
      if (status) params.append('status', status);

      const response = await agentApi.listSessions(status, limit);
      return response.data;
    } catch (err) {
      console.error('Failed to fetch sessions:', err);
      setError(err.response?.data?.error || 'Failed to fetch sessions');
      return null;
    }
  }, []);

  // Fetch available templates
  const fetchTemplates = useCallback(async () => {
    try {
      const response = await agentApi.getTemplates();
      return response.data.templates;
    } catch (err) {
      console.error('Failed to fetch templates:', err);
      setError(err.response?.data?.error || 'Failed to fetch templates');
      return null;
    }
  }, []);

  // Disconnect on unmount
  useEffect(() => {
    return () => {
      if (socketRef.current) {
        socketRef.current.disconnect();
        socketRef.current = null;
      }
    };
  }, []);

  // Handle token changes - reconnect if token becomes available
  useEffect(() => {
    if (token && !socketRef.current) {
      connectSocket();
    } else if (!token && socketRef.current) {
      socketRef.current.disconnect();
      socketRef.current = null;
      setIsConnected(false);
    }
  }, [token, connectSocket]);

  // Auto-load initial session if provided
  useEffect(() => {
    if (initialSessionId) {
      loadSession(initialSessionId);
    }
  }, [initialSessionId, loadSession]);

  // Memoize return value
  const value = useMemo(() => ({
    // State
    session,
    steps,
    currentThought,
    pendingApproval,
    isConnected,
    isAuthenticated,
    error,

    // Actions
    startAgent,
    approveAction,
    cancelAgent,
    loadSession,
    fetchSessions,
    fetchTemplates,

    // Connection details
    isActive: session && ['running', 'awaiting_approval'].includes(session.status),
    socket: socketRef.current
  }), [
    session, steps, currentThought, pendingApproval, isConnected, isAuthenticated, error,
    startAgent, approveAction, cancelAgent, loadSession, fetchSessions, fetchTemplates
  ]);

  return value;
}

export default useAgentSession;
