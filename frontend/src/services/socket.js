import { io } from 'socket.io-client';

class SocketService {
  constructor() {
    this.socket = null;
    this.isConnected = false;
    this.isAuthenticated = false;
    this.user = null;
    this.conversationRooms = new Set();
    this.listeners = {};
    this.pendingJoins = new Set(); // Queue for join requests before auth
  }

  connect(token) {
    if (this.socket) {
      this.disconnect();
    }

    const socketOptions = {
      transports: ['websocket', 'polling'],
      reconnection: true,
      reconnectionAttempts: 5,
      reconnectionDelay: 1000,
      reconnectionDelayMax: 5000,
      pingTimeout: 120000,  // 120 seconds - must match backend
      pingInterval: 25000,  // 25 seconds - must match backend
    };

    // Use environment variable for WebSocket URL, fallback to same origin
    const wsUrl = import.meta.env.VITE_WS_URL || window.location.origin;

    this.socket = io(wsUrl, {
      ...socketOptions,
      path: '/socket.io'
    });

    this.socket.on('connect', () => {
      this.isConnected = true;
      this._emit('connect', this.socket.id);

      // Authenticate immediately after connection
      if (token) {
        this.socket.emit('authenticate', { token });
      }
    });

    this.socket.on('authenticated', (data) => {
      this.isAuthenticated = true;
      this.user = data.user;
      // Process any pending join requests
      if (this.pendingJoins.size > 0) {
        this.pendingJoins.forEach(convId => {
          this.socket.emit('join_conversation', { conversation_id: convId });
          this.conversationRooms.add(convId);
        });
        this.pendingJoins.clear();
      }
      this._emit('authenticated', data);
    });

    this.socket.on('error', (error) => {
      console.error('Socket error received:', error);
      this._emit('error', error);
    });

    this.socket.on('error', (error) => {
      console.error('Socket error:', error);
      this._emit('error', error);
    });

    this.socket.on('disconnect', (reason) => {
      console.log('[SocketService] DISCONNECTED:', reason);
      this.isConnected = false;
      this.isAuthenticated = false;
      this._emit('disconnect', reason);
    });

    // Monitor ALL events
    this.socket.onAny((event, ...args) => {
      console.log('[SocketService] ANY EVENT:', event, args);
    });

    // Chat events
    this.socket.on('conversation_joined', (data) => {
      this.conversationRooms.add(data.conversation_id);
      this._emit('conversation_joined', data);
    });

    this.socket.on('conversation_updated', (data) => {
      this._emit('conversation_updated', data);
    });

    this.socket.on('new_message', (message) => {
      console.log('[SocketService] new_message received:', message);
      this._emit('new_message', message);
    });

    this.socket.on('ai_response_chunk', (data) => {
      console.log('[SocketService] ai_response_chunk received:', data);
      this._emit('ai_response_chunk', data);
    });

    this.socket.on('ai_response_complete', (data) => {
      console.log('[SocketService] ai_response_complete received:', data);
      this._emit('ai_response_complete', data);
    });

    this.socket.on('user_typing', (data) => {
      this._emit('user_typing', data);
    });

    this.socket.on('user_stopped_typing', (data) => {
      this._emit('user_stopped_typing', data);
    });

    this.socket.on('connected', (data) => {
      this._emit('connected', data);
    });
  }

  disconnect() {
    if (this.socket) {
      this.socket.disconnect();
      this.socket = null;
    }
    this.isConnected = false;
    this.isAuthenticated = false;
    this.conversationRooms.clear();
    this.pendingJoins.clear();
  }

  // Room management
  joinConversation(conversationId) {
    if (!conversationId) return;

    if (this.socket && this.isAuthenticated) {
      this.socket.emit('join_conversation', { conversation_id: conversationId });
      this.conversationRooms.add(conversationId);
    } else if (this.socket) {
      // Not authenticated yet - queue for after auth
      this.pendingJoins.add(conversationId);
    }
    // If no socket, ignore (will be handled on next connect)
  }

  leaveConversation(conversationId) {
    if (this.socket) {
      this.socket.emit('leave_conversation', { conversation_id: conversationId });
      this.conversationRooms.delete(conversationId);
    }
  }

  // Messaging
  sendMessage(conversationId, message, images = []) {
    if (this.socket && this.isAuthenticated) {
      this.socket.emit('send_message', {
        conversation_id: conversationId,
        message: message,
        images: images
      });
    } else {
      }
  }

  // Typing indicators
  startTyping(conversationId) {
    if (this.socket && this.isAuthenticated) {
      this.socket.emit('typing_start', { conversation_id: conversationId });
    }
  }

  stopTyping(conversationId) {
    if (this.socket && this.isAuthenticated) {
      this.socket.emit('typing_stop', { conversation_id: conversationId });
    }
  }

  // Event subscription
  on(event, callback) {
    if (!this.listeners[event]) {
      this.listeners[event] = [];
    }
    this.listeners[event].push(callback);
  }

  off(event, callback) {
    if (this.listeners[event]) {
      this.listeners[event] = this.listeners[event].filter(cb => cb !== callback);
    }
  }

  _emit(event, data) {
    if (this.listeners[event]) {
      this.listeners[event].forEach(callback => callback(data));
    }
  }

  // State
  getConnectionState() {
    return {
      isConnected: this.isConnected,
      isAuthenticated: this.isAuthenticated,
      user: this.user,
      rooms: Array.from(this.conversationRooms)
    };
  }
}

// Export singleton instance
const socketService = new SocketService();
export default socketService;
