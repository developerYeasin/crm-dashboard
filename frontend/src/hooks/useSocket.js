import { useState, useEffect, useCallback, useRef } from 'react';
import { useAuth } from '../contexts/AuthContext';
import socketService from '../services/socket';

export function useSocket() {
  const { user, token } = useAuth();
  const [isConnected, setIsConnected] = useState(false);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [connectionState, setConnectionState] = useState('disconnected'); // connected, disconnected, error
  const eventListenersRef = useRef({});

  // Update state when socket service changes
  useEffect(() => {
    const updateState = () => {
      const state = socketService.getConnectionState();
      setIsConnected(state.isConnected);
      setIsAuthenticated(state.isAuthenticated);
      setConnectionState(state.isConnected ? (state.isAuthenticated ? 'connected' : 'authenticating') : 'disconnected');
    };

    // Initial state
    updateState();

    // Listen to socket service events
    const handleConnect = () => {
      updateState();
    };

    const handleDisconnect = () => {
      updateState();
      setConnectionState('disconnected');
    };

    const handleAuthenticated = () => {
      updateState();
    };

    const handleError = () => {
      setConnectionState('error');
    };

    socketService.on('connect', handleConnect);
    socketService.on('disconnect', handleDisconnect);
    socketService.on('authenticated', handleAuthenticated);
    socketService.on('error', handleError);

    return () => {
      socketService.off('connect', handleConnect);
      socketService.off('disconnect', handleDisconnect);
      socketService.off('authenticated', handleAuthenticated);
      socketService.off('error', handleError);
    };
  }, []);

  // Connect when authenticated
  useEffect(() => {
    if (token) {
      socketService.connect(token);
    } else {
      socketService.disconnect();
    }

    return () => {
      if (!token) {
        socketService.disconnect();
      }
    };
  }, [token]);

  // Subscribe to socket events
  const subscribe = useCallback((event, callback) => {
    console.log('[useSocket] Subscribing to event:', event, 'callback:', callback.name || 'anonymous');
    socketService.on(event, callback);
    // Track for cleanup
    if (!eventListenersRef.current[event]) {
      eventListenersRef.current[event] = [];
    }
    eventListenersRef.current[event].push(callback);
  }, []);

  const unsubscribe = useCallback((event, callback) => {
    socketService.off(event, callback);
    if (eventListenersRef.current[event]) {
      eventListenersRef.current[event] = eventListenersRef.current[event].filter(cb => cb !== callback);
    }
  }, []);

  // Chat actions
  const joinConversation = useCallback((conversationId) => {
    socketService.joinConversation(conversationId);
  }, []);

  const leaveConversation = useCallback((conversationId) => {
    socketService.leaveConversation(conversationId);
  }, []);

  const sendMessage = useCallback((conversationId, message, images = []) => {
    socketService.sendMessage(conversationId, message, images);
  }, []);

  const startTyping = useCallback((conversationId) => {
    socketService.startTyping(conversationId);
  }, []);

  const stopTyping = useCallback((conversationId) => {
    socketService.stopTyping(conversationId);
  }, []);

  // Disconnect on unmount if we own the connection
  useEffect(() => {
    return () => {
      // Only disconnect if we're the last user? For now, keep connection alive
      // socketService.disconnect();
    };
  }, []);

  return {
    isConnected,
    isAuthenticated,
    connectionState,
    subscribe,
    unsubscribe,
    joinConversation,
    leaveConversation,
    sendMessage,
    startTyping,
    stopTyping,
    getSocket: () => socketService
  };
}
