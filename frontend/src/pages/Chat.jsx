import { useState, useEffect, useRef } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { FiSend, FiPlus, FiTrash2, FiMessageSquare, FiClock } from 'react-icons/fi';
import { chatApi } from '../services/chat-api';

export default function Chat() {
  const { user } = useAuth();
  const [conversations, setConversations] = useState([]);
  const [currentConv, setCurrentConv] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    fetchConversations();
  }, []);

  useEffect(() => {
    if (currentConv) {
      fetchMessages(currentConv.id);
    }
  }, [currentConv]);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const fetchConversations = async () => {
    setLoading(true);
    try {
      const res = await chatApi.getConversations();
      setConversations(res.data);
      if (res.data.length > 0 && !currentConv) {
        setCurrentConv(res.data[0]);
      } else if (res.data.length === 0) {
        // Create first conversation automatically
        await createConversation('New Chat');
      }
    } catch (error) {
      console.error('Failed to fetch conversations:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchMessages = async (convId) => {
    try {
      const res = await chatApi.getConversation(convId);
      // Map backend field 'timestamp' to 'created_at' for frontend compatibility
      const messages = (res.data.messages || []).map(msg => ({
        ...msg,
        created_at: msg.timestamp || msg.created_at
      }));
      setMessages(messages);
    } catch (error) {
      console.error('Failed to fetch messages:', error);
      setMessages([]);
    }
  };

  const createConversation = async (title) => {
    try {
      const res = await chatApi.createConversation(title);
      setConversations(prev => [res.data, ...prev]);
      setCurrentConv(res.data);
      return res.data;
    } catch (error) {
      console.error('Failed to create conversation:', error);
    }
  };

  const sendMessage = async (e) => {
    e.preventDefault();
    if (!input.trim() || !currentConv || sending) return;

    const userMessage = input.trim();
    setInput('');
    setSending(true);

    // Optimistically add user message to UI
    const tempUserMsg = {
      id: Date.now(),
      conversation_id: currentConv.id,
      role: 'user',
      content: userMessage,
      created_at: new Date().toISOString()
    };
    setMessages(prev => [...prev, tempUserMsg]);

    try {
      const res = await chatApi.sendMessage(currentConv.id, { message: userMessage });
      // Replace temp message with real one and add assistant response
      setMessages(prev => [
        ...prev.filter(m => m.id !== tempUserMsg.id),
        { ...tempUserMsg, id: res.data.id || Date.now() },
        {
          id: res.data.message_id,
          conversation_id: currentConv.id,
          role: 'assistant',
          content: res.data.response,
          created_at: new Date().toISOString()
        }
      ]);
    } catch (error) {
      console.error('Failed to send message:', error);
      alert('Failed to send message. Please try again.');
    } finally {
      setSending(false);
    }
  };

  const deleteConversation = async (convId, e) => {
    e.stopPropagation();
    if (!window.confirm('Delete this conversation?')) return;

    try {
      await chatApi.deleteConversation(convId);
      setConversations(prev => prev.filter(c => c.id !== convId));
      if (currentConv?.id === convId) {
        setCurrentConv(null);
        setMessages([]);
        if (conversations.length > 1) {
          const nextConv = conversations.find(c => c.id !== convId);
          if (nextConv) setCurrentConv(nextConv);
        }
      }
    } catch (error) {
      alert('Failed to delete conversation');
    }
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const formatTime = (dateStr) => {
    const date = new Date(dateStr);
    return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
  };

  const renderMessageContent = (content) => {
    // Simple markdown-like rendering
    return content.split('\n').map((line, i) => {
      if (line.startsWith('```')) return null; // Skip code block delimiters for simplicity
      return (
        <p key={i} className="mb-2 last:mb-0 whitespace-pre-wrap">
          {line}
        </p>
      );
    });
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-500"></div>
      </div>
    );
  }

  return (
    <div className="flex h-[calc(100vh-theme(spacing.24))] gap-4">
      {/* Sidebar - Conversations List */}
      <div className="w-80 flex flex-col bg-white dark:bg-dark-900 rounded-xl shadow-sm border border-gray-200 dark:border-dark-700 overflow-hidden">
        <div className="p-4 border-b border-gray-200 dark:border-dark-700 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Chat History</h2>
          <button
            onClick={() => createConversation('New Chat')}
            className="p-2 text-primary-500 hover:bg-primary-50 dark:hover:bg-primary-900/30 rounded-lg transition-colors"
            title="New Chat"
          >
            <FiPlus className="w-5 h-5" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto">
          {conversations.length === 0 ? (
            <div className="p-4 text-center text-gray-500 dark:text-gray-400">
              <FiMessageSquare className="w-8 h-8 mx-auto mb-2 opacity-50" />
              <p className="text-sm">No conversations yet</p>
            </div>
          ) : (
            <div className="divide-y divide-gray-200 dark:divide-dark-700">
              {conversations.map(conv => (
                <div
                  key={conv.id}
                  onClick={() => setCurrentConv(conv)}
                  className={`p-4 cursor-pointer transition-colors ${
                    currentConv?.id === conv.id
                      ? 'bg-primary-50 dark:bg-primary-900/20 border-l-4 border-primary-500'
                      : 'hover:bg-gray-50 dark:hover:bg-dark-800 border-l-4 border-transparent'
                  }`}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1 min-w-0">
                      <h3 className="font-medium text-gray-900 dark:text-white truncate">
                        {conv.title || 'New Chat'}
                      </h3>
                      <p className="text-xs text-gray-500 dark:text-gray-400 mt-1 flex items-center">
                        <FiClock className="w-3 h-3 mr-1" />
                        {new Date(conv.updated_at).toLocaleDateString()}
                      </p>
                      <p className="text-xs text-gray-400 dark:text-gray-500 mt-0.5">
                        {conv.message_count} messages
                      </p>
                    </div>
                    <button
                      onClick={(e) => deleteConversation(conv.id, e)}
                      className="p-1 text-gray-400 hover:text-red-500 transition-colors"
                      title="Delete conversation"
                    >
                      <FiTrash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col bg-white dark:bg-dark-900 rounded-xl shadow-sm border border-gray-200 dark:border-dark-700 overflow-hidden">
        {currentConv ? (
          <>
            {/* Header */}
            <div className="p-4 border-b border-gray-200 dark:border-dark-700">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                {currentConv.title || 'Chat'}
              </h2>
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
              {messages.map((msg) => (
                <div
                  key={msg.id}
                  className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  <div
                    className={`max-w-[70%] rounded-2xl px-4 py-3 ${
                      msg.role === 'user'
                        ? 'bg-primary-500 text-white rounded-br-md'
                        : 'bg-gray-100 dark:bg-dark-800 text-gray-900 dark:text-white rounded-bl-md'
                    }`}
                  >
                    {msg.role === 'assistant' && (
                      <div className="flex items-center gap-2 mb-2">
                        <div className="w-6 h-6 rounded-full bg-primary-500 flex items-center justify-center text-white text-xs font-bold">
                          AI
                        </div>
                        <span className="text-xs font-medium text-gray-600 dark:text-gray-300">Claude</span>
                      </div>
                    )}
                    <div className="text-sm">{renderMessageContent(msg.content)}</div>
                    <div className={`text-xs mt-2 ${msg.role === 'user' ? 'text-primary-100' : 'text-gray-400 dark:text-gray-500'}`}>
                      {formatTime(msg.created_at)}
                    </div>
                  </div>
                </div>
              ))}
              {sending && (
                <div className="flex justify-start">
                  <div className="bg-gray-100 dark:bg-dark-800 rounded-2xl rounded-bl-md px-4 py-3">
                    <div className="flex items-center gap-2">
                      <div className="w-6 h-6 rounded-full bg-primary-500 flex items-center justify-center text-white text-xs font-bold">
                        AI
                      </div>
                      <div className="flex gap-1">
                        <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></span>
                        <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce delay-100"></span>
                        <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce delay-200"></span>
                      </div>
                    </div>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>

            {/* Input */}
            <div className="p-4 border-t border-gray-200 dark:border-dark-700">
              <form onSubmit={sendMessage} className="flex gap-2">
                <input
                  type="text"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  placeholder="Type your message... (e.g., 'Create a high priority task for Mike')"
                  className="flex-1 input"
                  disabled={sending}
                />
                <button
                  type="submit"
                  disabled={!input.trim() || sending}
                  className="btn-primary px-4 flex items-center gap-2"
                >
                  <FiSend className="w-4 h-4" />
                  Send
                </button>
              </form>
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-2">
                Claude can help you create tasks, manage team members, and answer questions about your CRM data.
              </p>
            </div>
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center">
              <FiMessageSquare className="w-16 h-16 text-gray-300 dark:text-gray-600 mx-auto mb-4" />
              <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">No Conversation Selected</h3>
              <p className="text-gray-500 dark:text-gray-400 mb-4">Select a conversation from the sidebar or start a new one.</p>
              <button onClick={() => createConversation('New Chat')} className="btn-primary">
                Start New Chat
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
