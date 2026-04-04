import { useState, useEffect, useRef, useCallback } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useTheme } from '../contexts/ThemeContext';
import { useSocket } from '../hooks/useSocket';
import { chatApi } from '../services/chat-api';
import { Link } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { FiSend, FiPlus, FiTrash2, FiMessageSquare, FiSearch, FiX, FiChevronRight, FiPaperclip, FiFile, FiXCircle, FiHome, FiFileText, FiCpu, FiZap, FiFilter, FiArrowRight, FiMenu, FiSun, FiMoon } from 'react-icons/fi';

// Agent skill definitions
const AGENT_SKILLS = [
  { id: 'general', name: 'General Assistant', description: 'Help with various tasks', icon: FiMessageSquare, systemPrompt: 'You are a helpful AI assistant.' },
  { id: 'coder', name: 'Code Expert', description: 'Programming, debugging, code review', icon: FiFileText, systemPrompt: 'You are an expert programmer. Help with coding tasks, debugging, code reviews, and technical explanations.' },
  { id: 'researcher', name: 'Researcher', description: 'Research, analysis, writing', icon: FiSearch, systemPrompt: 'You are a skilled researcher. Help with information gathering, analysis, summarization, and detailed research reports.' },
  { id: 'analyst', name: 'Data Analyst', description: 'Data analysis, charts, insights', icon: FiFileText, systemPrompt: 'You are a data analyst. Help with data analysis, creating insights, and interpreting data.' },
  { id: 'creative', name: 'Creative Writer', description: 'Writing, brainstorming, editing', icon: FiFileText, systemPrompt: 'You are a creative writer. Help with writing, editing, brainstorming ideas, and improving text.' },
];

export default function MaxAIAgent() {
  const { user, token, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const socket = useSocket();

  // Debug: Log immediately on component definition
  // Debug: Log initialization
  useEffect(() => {
    }, [user, token, socket]);

  // UI State
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [error, setError] = useState(null);

  // Agent State
  const [selectedSkill, setSelectedSkill] = useState(AGENT_SKILLS[0]);
  const [conversations, setConversations] = useState([]);
  const [currentConv, setCurrentConv] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [loading, setLoading] = useState(true);
  const [attachedFiles, setAttachedFiles] = useState([]); // { file, type, name }

  const messagesEndRef = useRef(null);
  const textInputRef = useRef(null);
  const sidebarRef = useRef(null);
  const fileInputRef = useRef(null);

  // Ref to track latest currentConv without needing to re-subscribe
  const currentConvRef = useRef(currentConv);
  useEffect(() => {
    currentConvRef.current = currentConv;
  }, [currentConv]);

  // Load conversations on mount
  useEffect(() => {
    if (token) {
      loadConversations();
    } else {
      setLoading(false);
    }
  }, [token]);

  // Socket listeners (subscribe only once, use ref for currentConv)
  useEffect(() => {
    console.log('[WS Effect] Setting up stable socket listeners');
    const handleNewMessage = (message) => {
      const msg = message.message || message.data || message;
      console.log('[WS] new_message event received:', msg);
      const convId = msg.conversation_id || message.conversation_id;
      const currentConv = currentConvRef.current; // use ref for latest value
      console.log('[WS] convId:', convId, 'currentConv?.id:', currentConv?.id, 'messages length (from state):', messages.length);

      // Clear sending state when assistant responds or final chunk
      if (msg.role === 'assistant' || msg.is_final) {
        console.log('[WS] Clearing sending/pending (assistant or final)');
        setSending(false);
        // setPendingResponse(false); // commented out if not used
      }

      // Only add if for current conversation
      if (currentConv && convId && convId !== currentConv.id) {
        console.log('[WS] Message for different conversation, ignoring');
        return;
      }

      setMessages(prev => {
        const exists = msg.id && prev.some(m => m.id === msg.id);
        if (exists) {
          console.log('[WS] Duplicate message ID, skipping:', msg.id);
          return prev;
        }

        // Check if this is a confirmed user message from server (has numeric ID)
        const isConfirmedUserMessage = msg.role === 'user' && msg.id && typeof msg.id === 'number';

        // If this is a confirmed user message, remove temp user messages with matching content
        let filtered = prev;
        if (isConfirmedUserMessage) {
          filtered = prev.filter(m => {
            const id = m.id;
            const isTemp = typeof id === 'string' && id.startsWith('temp-');
            if (isTemp && m.role === 'user') {
              console.log('[WS] Removing temp user message:', m.id);
              return false;
            }
            return true;
          });
        }

        const messageToAdd = msg.id ? msg : { ...msg, id: `server-${Date.now()}-${Math.random()}` };
        console.log('[WS] Adding message to state:', { role: messageToAdd.role, id: messageToAdd.id, contentPreview: (messageToAdd.content || '').substring(0, 80), is_final: msg.is_final });
        return [...filtered, messageToAdd];
      });

      // Update conversation preview
      if (convId) {
        setConversations(prev => prev.map(conv =>
          conv.id === convId
            ? { ...conv, last_message: msg.content, updated_at: msg.created_at || Date.now() }
            : conv
        ).sort((a, b) => new Date(b.updated_at) - new Date(a.updated_at)));
      }
    };

    const handleComplete = () => {
      console.log('[WS] ai_response_complete event received - setting sending=false');
      setSending(false);
    };

    console.log('[WS] Subscribing to socket events (stable)');
    socket.subscribe('new_message', handleNewMessage);
    socket.subscribe('ai_response_complete', handleComplete);

    return () => {
      socket.unsubscribe('new_message', handleNewMessage);
      socket.unsubscribe('ai_response_complete', handleComplete);
      console.log('[WS] Unsubscribed socket events');
    };
  }, [socket]); // only re-run if socket object changes (rare)

  // Reconnection handling: rejoin and reload messages to sync any missed ones
  useEffect(() => {
    const handleConnect = async () => {
      console.log('[WS] socket connected event. currentConv:', currentConv?.id, 'socket isAuthenticated:', socket.getSocket()?.isAuthenticated);
      if (currentConv) {
        // Rejoin the conversation room
        console.log('[WS] Attempting to rejoin conversation', currentConv.id);
        socket.joinConversation(currentConv.id);
        // Reload messages from server to fill any gaps
        try {
          const [convRes, msgsRes] = await Promise.all([
            chatApi.getConversation(currentConv.id),
            chatApi.getConversationMessages(currentConv.id)
          ]);
          console.log('[WS] Reloaded messages from server, count:', msgsRes.data.length);
          setCurrentConv(convRes.data);
          setMessages(msgsRes.data);
          setSending(false); // Ensure sending state is cleared after reload
        } catch (err) {
          console.error('[WS] Failed to reload messages:', err);
          setError(err.response?.data?.error || 'Failed to reload messages after reconnect');
        }
      }
    };

    socket.subscribe('connect', handleConnect);
    return () => {
      socket.unsubscribe('connect', handleConnect);
    };
  }, [socket, currentConv, chatApi]);

  // Auto-scroll
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, sending]);

  // Log messages state changes
  useEffect(() => {
    console.log('[Render] messages state changed. Count:', messages.length, 'Last few:', messages.slice(-2).map(m => ({id: m.id, role: m.role, contentPreview: (m.content || '').substring(0, 40)})));
  }, [messages]);

  const loadConversations = async () => {
    try {
      setError(null);
      const res = await chatApi.getConversations();
      // Ensure we have an array
      const conversations = Array.isArray(res.data) ? res.data : [];
      setConversations(conversations);
      if (conversations.length > 0 && !currentConv) {
        await loadMessages(conversations[0].id);
      } else if (conversations.length === 0) {
        // Create a new conversation automatically
        await createConversation('New Agent Chat');
      }
    } catch (err) {
      console.error('[MaxAIAgent] Error loading conversations:', err);
      setError(err.response?.data?.error || 'Failed to load conversations');
      setConversations([]);
    } finally {
      setLoading(false);
    }
  };

  const loadMessages = async (convId) => {
    try {
      const [convRes, msgsRes] = await Promise.all([
        chatApi.getConversation(convId),
        chatApi.getConversationMessages(convId)
      ]);
      setCurrentConv(convRes.data);
      setMessages(msgsRes.data);
      // Join the conversation room to receive real-time updates
      socket.joinConversation(convId);
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to load messages');
    }
  };

  const createConversation = async (title) => {
    try {
      const res = await chatApi.createConversation(title);
      setConversations(prev => [res.data, ...prev]);
      setCurrentConv(res.data);
      socket.joinConversation(res.data.id);
      setMessages([]);
      setSidebarOpen(true);
      setMobileMenuOpen(false);
      return res.data;
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to create conversation');
      throw err;
    }
  };

  const deleteConversation = async (id, e) => {
    e?.stopPropagation();
    if (!confirm('Delete this conversation?')) return;

    try {
      await chatApi.deleteConversation(id);
      setConversations(prev => prev.filter(c => c.id !== id));
      if (currentConv?.id === id) {
        setCurrentConv(null);
        setMessages([]);
      }
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to delete conversation');
    }
  };

  const handleFileAttach = (e) => {
    const files = Array.from(e.target.files);
    const newFiles = files.map(file => ({
      file,
      type: file.type.startsWith('image/') ? 'image' : 'pdf',
      name: file.name,
      url: URL.createObjectURL(file)
    }));
    setAttachedFiles(prev => [...prev, ...newFiles]);
  };

  const removeAttachedFile = (index) => {
    setAttachedFiles(prev => prev.filter((_, i) => i !== index));
  };

  const sendMessage = async () => {
    console.log('[Send] sendMessage called. input:', input.trim(), 'sending:', sending, 'currentConv:', currentConv?.id);
    if ((!input.trim() && attachedFiles.length === 0) || sending || !currentConv) {
      console.log('[Send] Aborting - invalid state');
      return;
    }

    const messageContent = input.trim();
    console.log('[Send] Sending message to conversation', currentConv.id, ':', messageContent);

    // Build message with attachments if any
    const messageData = {
      content: messageContent,
      attachments: attachedFiles.map(f => ({
        name: f.name,
        type: f.type,
        url: f.url
      }))
    };

    const tempMessage = {
      id: `temp-${Date.now()}`,
      role: 'user',
      content: messageContent + (attachedFiles.length > 0 ? `\n[Attached: ${attachedFiles.map(f => f.name).join(', ')}]` : ''),
      created_at: new Date().toISOString(),
    };

    // Optimistic update
    setMessages(prev => [...prev, tempMessage]);
    setInput('');
    setAttachedFiles([]);
    setSending(true);
    setError(null);

    try {
      await socket.sendMessage(currentConv.id, messageContent);
      console.log('[Send] Message sent successfully via socket');
      } catch (err) {
      console.error('[Send] Error:', err);
      setMessages(prev => prev.filter(m => m.id !== tempMessage.id));
      setError(err.response?.data?.error || 'Failed to send message');
      setSending(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const filteredConversations = (Array.isArray(conversations) ? conversations : []).filter(conv =>
    conv.title?.toLowerCase().includes(searchQuery.toLowerCase()) ||
    conv.last_message?.toLowerCase().includes(searchQuery.toLowerCase())
  );

  if (loading) {
    return (
      <div className="flex h-full bg-gray-50 dark:bg-dark-900">
        <aside className="w-80 bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700">
          <div className="h-full flex flex-col">
            <div className="p-4 border-b border-gray-200 dark:border-gray-700">
              <div className="flex items-center gap-2">
                <Link to="/" className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700">
                  <FiHome className="w-5 h-5 text-gray-600 dark:text-gray-300" />
                </Link>
                <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-purple-500 to-pink-600 flex items-center justify-center">
                  <FiCpu className="text-white w-4 h-4" />
                </div>
                <span className="font-bold text-lg text-gray-900 dark:text-white">Max AI Agent</span>
              </div>
            </div>
          </div>
        </aside>
        <div className="flex-1 flex items-center justify-center bg-gray-50 dark:bg-dark-900">
          <div className="text-center">
            <div className="w-16 h-16 border-4 border-purple-500 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
            <p className="text-gray-600 dark:text-gray-400">Loading agent...</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-screen bg-gray-50 dark:bg-dark-900">
      {/* Error Banner */}
      {error && (
        <div className="fixed top-4 left-1/2 transform -translate-x-1/2 z-50 bg-red-100 dark:bg-red-900/30 border border-red-300 dark:border-red-800 text-red-800 dark:text-red-300 px-4 py-3 rounded-lg shadow-lg max-w-md">
          <div className="flex items-center gap-2">
            <FiXCircle className="w-5 h-5 flex-shrink-0" />
            <p className="text-sm">{error}</p>
            <button onClick={() => setError(null)} className="ml-auto hover:bg-red-200 dark:hover:bg-red-800 rounded p-1">
              <FiX className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {/* Sidebar - Agent Skills & Conversations */}
      <aside
        ref={sidebarRef}
        className={`fixed inset-y-0 left-0 z-50 w-80 bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 transform transition-transform duration-300 ease-in-out overflow-hidden
          ${mobileMenuOpen ? 'translate-x-0' : '-translate-x-full'}
          ${sidebarOpen ? 'lg:translate-x-0' : 'lg:-translate-x-full'}
          ${sidebarOpen ? 'lg:w-80' : 'lg:w-0'}
          ${sidebarOpen ? 'lg:border-r' : 'lg:border-r-0'}
          lg:relative`}
      >
        <div className="h-full flex flex-col">
          {/* Header */}
          <div className="p-4 border-b border-gray-200 dark:border-gray-700">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <Link to="/" className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors">
                  <FiHome className="w-5 h-5 text-gray-600 dark:text-gray-300" />
                </Link>
                <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-purple-500 to-pink-600 flex items-center justify-center">
                  <FiCpu className="text-white w-4 h-4" />
                </div>
                <span className="font-bold text-lg text-gray-900 dark:text-white">Agent</span>
              </div>
              <button onClick={() => setMobileMenuOpen(false)} className="lg:hidden p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700">
                <FiX className="w-5 h-5" />
              </button>
            </div>

            {/* Skill Selector */}
            <div className="mb-3">
              <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">Agent Skill</label>
              <select
                value={selectedSkill.id}
                onChange={(e) => setSelectedSkill(AGENT_SKILLS.find(s => s.id === e.target.value) || AGENT_SKILLS[0])}
                className="w-full px-3 py-2 bg-gray-100 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-purple-500"
              >
                {AGENT_SKILLS.map(skill => (
                  <option key={skill.id} value={skill.id}>{skill.name}</option>
                ))}
              </select>
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">{selectedSkill.description}</p>
            </div>

            {/* Search */}
            <div className="relative">
              <FiSearch className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
              <input
                type="text"
                placeholder="Search conversations..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-10 pr-4 py-2 bg-gray-100 dark:bg-gray-700 border border-transparent focus:border-purple-500 rounded-lg text-sm text-gray-900 dark:text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-purple-500/50"
              />
            </div>
          </div>

          {/* Conversation List */}
          <div className="flex-1 overflow-y-auto px-2">
            {filteredConversations.length === 0 ? (
              <div className="p-6 text-center">
                <FiMessageSquare className="w-12 h-12 mx-auto text-gray-300 dark:text-gray-600 mb-3" />
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  {searchQuery ? 'No conversations found' : 'No conversations yet'}
                </p>
              </div>
            ) : (
              <div className="space-y-1 pb-2">
                {filteredConversations.map(conv => (
                  <div
                    key={conv.id}
                    onClick={() => {
                      setCurrentConv(conv);
                      loadMessages(conv.id);
                      setMobileMenuOpen(false);
                    }}
                    className={`p-3 rounded-xl cursor-pointer transition-all duration-200 group ${
                      currentConv?.id === conv.id
                        ? 'bg-purple-50 dark:bg-purple-900/30 border-l-3 border-purple-500'
                        : 'hover:bg-gray-100 dark:hover:bg-gray-700/50 border-l-3 border-transparent'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex-1 min-w-0">
                        <h3 className="font-semibold text-gray-900 dark:text-white text-sm truncate">
                          {conv.title || 'Agent Chat'}
                        </h3>
                        {conv.last_message && (
                          <p className="text-xs text-gray-500 dark:text-gray-400 mt-1 line-clamp-2">
                            {conv.last_message}
                          </p>
                        )}
                      </div>
                      <button
                        onClick={(e) => deleteConversation(conv.id, e)}
                        className="p-1.5 rounded-lg hover:bg-red-100 dark:hover:bg-red-900/30 text-gray-400 hover:text-red-500 opacity-0 group-hover:opacity-100 transition-all"
                        title="Delete conversation"
                      >
                        <FiTrash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="p-3 border-t border-gray-200 dark:border-gray-700">
            <div className="flex items-center gap-2 text-xs">
              {socket.isConnected && socket.isAuthenticated ? (
                <>
                  <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></div>
                  <span className="text-green-600 dark:text-green-400 font-medium">Connected</span>
                </>
              ) : (
                <>
                  <div className="w-2 h-2 rounded-full bg-red-500"></div>
                  <span className="text-red-600 dark:text-red-400 font-medium">Offline</span>
                </>
              )}
            </div>
          </div>
        </div>
      </aside>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col min-w-0 bg-white dark:bg-gray-900 border-l border-gray-200 dark:border-gray-700">
        {/* Header */}
        <header className="sticky top-0 z-20 bg-white/95 dark:bg-gray-900/95 backdrop-blur-md border-b border-gray-200 dark:border-gray-700 px-4 lg:px-6 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="lg:hidden p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800"
            >
              <FiMenu className="w-5 h-5 text-gray-600 dark:text-gray-300" />
            </button>
            <button
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="hidden lg:flex p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-600 dark:text-gray-300"
              title={sidebarOpen ? 'Hide conversations' : 'Show conversations'}
            >
              {sidebarOpen ? <FiChevronRight className="w-5 h-5" /> : <FiMenu className="w-5 h-5" />}
            </button>
            <div>
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white truncate max-w-[200px] lg:max-w-md">
                {selectedSkill.name}
              </h2>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                {currentConv ? `${messages.length} messages` : 'Start a conversation'}
              </p>
            </div>
            {/* Theme Toggle */}
            <button
              onClick={toggleTheme}
              className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors ml-2"
              title={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
            >
              {theme === 'dark' ? (
                <FiSun className="w-5 h-5 text-yellow-500" />
              ) : (
                <FiMoon className="w-5 h-5 text-gray-600" />
              )}
            </button>
          </div>
        </header>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-4 lg:px-6 py-6">
          {!currentConv ? (
            <div className="h-full flex flex-col items-center justify-center text-center px-4">
              <div className="w-24 h-24 rounded-2xl bg-gradient-to-br from-purple-500 to-pink-600 flex items-center justify-center mb-6 shadow-lg shadow-purple-500/25">
                <FiCpu className="text-white w-12 h-12" />
              </div>
              <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
                {selectedSkill.name}
              </h2>
              <p className="text-gray-600 dark:text-gray-400 mb-8 max-w-md">
                {selectedSkill.description}
                Ask any question or give a task to the agent.
              </p>
              <div className="flex flex-wrap gap-2 justify-center max-w-lg">
                {AGENT_SKILLS.map(skill => (
                  <button
                    key={skill.id}
                    onClick={() => setSelectedSkill(skill)}
                    className={`px-4 py-2 rounded-full text-sm transition-colors ${
                      selectedSkill.id === skill.id
                        ? 'bg-purple-100 dark:bg-purple-900/30 border-2 border-purple-500 text-purple-700 dark:text-purple-300'
                        : 'bg-gray-100 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 hover:border-purple-500 text-gray-700 dark:text-gray-300'
                    }`}
                  >
                    {skill.name}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="max-w-4xl mx-auto space-y-6">
              {messages.map((msg, idx) => (
                <div
                  key={msg.id || idx}
                  className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  <div className={`max-w-[85%] md:max-w-[75%] rounded-2xl px-4 py-3 ${
                    msg.role === 'user'
                      ? 'bg-purple-500 text-white'
                      : 'bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-white'
                  }`}>
                    <div className="markdown-content">
                      <ReactMarkdown
                        remarkPlugins={[remarkGfm]}
                        components={{
                          // Paragraphs
                          p: ({node, ...props}) => <p className="mb-2 last:mb-0" {...props} />,
                          // Lists
                          ul: ({node, ...props}) => <ul className="list-disc pl-5 mb-2 space-y-1" {...props} />,
                          ol: ({node, ...props}) => <ol className="list-decimal pl-5 mb-2 space-y-1" {...props} />,
                          li: ({node, ...props}) => <li className="ml-1" {...props} />,
                          // Headings
                          h1: ({node, ...props}) => <h1 className="text-xl font-bold mb-2 mt-4 first:mt-0" {...props} />,
                          h2: ({node, ...props}) => <h2 className="text-lg font-bold mb-2 mt-3 first:mt-0" {...props} />,
                          h3: ({node, ...props}) => <h3 className="text-base font-bold mb-2 mt-2 first:mt-0" {...props} />,
                          h4: ({node, ...props}) => <h4 className="text-sm font-bold mb-2 mt-2 first:mt-0" {...props} />,
                          // Text formatting
                          strong: ({node, ...props}) => <strong className="font-semibold" {...props} />,
                          em: ({node, ...props}) => <em className="italic" {...props} />,
                          // Code
                          code: ({node, inline, ...props}) =>
                            inline
                              ? <code className="px-1 py-0.5 bg-gray-200 dark:bg-gray-700 rounded text-sm font-mono" {...props} />
                              : <code className="block p-3 bg-gray-200 dark:bg-gray-700 rounded-lg text-sm font-mono overflow-x-auto my-2" {...props} />,
                          pre: ({node, ...props}) => <pre className="p-3 bg-gray-200 dark:bg-gray-700 rounded-lg overflow-x-auto my-2" {...props} />,
                          // Tables
                          table: ({node, ...props}) => <table className="min-w-full border-collapse border border-gray-300 dark:border-gray-600 my-2" {...props} />,
                          thead: ({node, ...props}) => <thead className="bg-gray-100 dark:bg-gray-700" {...props} />,
                          th: ({node, ...props}) => <th className="border border-gray-300 dark:border-gray-600 px-3 py-2 text-left font-semibold text-xs uppercase tracking-wide" {...props} />,
                          td: ({node, ...props}) => <td className="border border-gray-300 dark:border-gray-600 px-3 py-2" {...props} />,
                          // Blockquotes
                          blockquote: ({node, ...props}) => <blockquote className="border-l-4 border-purple-500 pl-4 italic my-2 text-gray-600 dark:text-gray-400" {...props} />,
                          // Links
                          a: ({node, ...props}) => <a className="text-purple-600 dark:text-purple-400 hover:underline" {...props} />,
                          // Horizontal rule
                          hr: ({node, ...props}) => <hr className="my-4 border-gray-300 dark:border-gray-600" {...props} />,
                        }}
                      >
                        {msg.content}
                      </ReactMarkdown>
                    </div>
                    <p className={`text-xs mt-2 ${msg.role === 'user' ? 'text-purple-200' : 'text-gray-400'}`}>
                      {msg.created_at ? new Date(msg.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : ''}
                    </p>
                  </div>
                </div>
              ))}
              {sending && (
                <div className="flex justify-start">
                  <div className="bg-gray-100 dark:bg-gray-800 rounded-2xl px-4 py-3">
                    <div className="flex items-center gap-2">
                      <div className="w-2 h-2 bg-purple-500 rounded-full animate-bounce"></div>
                      <div className="w-2 h-2 bg-purple-500 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                      <div className="w-2 h-2 bg-purple-500 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                    </div>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* Input Area */}
        {currentConv && (
          <div className="border-t border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 px-4 py-4">
            <div className="max-w-4xl mx-auto">
              {/* Attached files preview */}
              {attachedFiles.length > 0 && (
                <div className="flex flex-wrap gap-2 mb-3">
                  {attachedFiles.map((file, idx) => (
                    <div key={idx} className="flex items-center gap-2 bg-gray-100 dark:bg-gray-800 rounded-lg px-3 py-1.5">
                      <FiFile className="w-4 h-4 text-purple-500" />
                      <span className="text-sm text-gray-700 dark:text-gray-300 truncate max-w-xs">{file.name}</span>
                      <button onClick={() => removeAttachedFile(idx)} className="hover:text-red-500">
                        <FiX className="w-4 h-4" />
                      </button>
                    </div>
                  ))}
                </div>
              )}

              <div className="flex gap-2">
                <input
                  type="file"
                  ref={fileInputRef}
                  onChange={handleFileAttach}
                  accept="image/*,.pdf"
                  multiple
                  className="hidden"
                />
                <button
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  className="p-3 rounded-xl border border-gray-300 dark:border-gray-600 hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-600 dark:text-gray-300 transition-colors"
                  title="Attach image or PDF"
                >
                  <FiPaperclip className="w-5 h-5" />
                </button>
                <div className="flex-1 relative">
                  <textarea
                    ref={textInputRef}
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={handleKeyDown}
                    placeholder="Message the agent... (Enter to send, Shift+Enter for newline)"
                    rows={1}
                    className="w-full px-4 py-3 bg-gray-100 dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-xl text-gray-900 dark:text-white placeholder-gray-500 focus:ring-2 focus:ring-purple-500 focus:border-transparent outline-none resize-none overflow-hidden transition-shadow"
                    style={{ minHeight: '48px' }}
                    disabled={sending}
                  />
                </div>
                <button
                  onClick={sendMessage}
                  disabled={!input.trim() && attachedFiles.length === 0 || sending}
                  className="px-6 py-3 bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 disabled:from-gray-300 disabled:to-gray-300 text-white rounded-xl font-medium transition-all duration-200 shadow-sm disabled:cursor-not-allowed"
                >
                  <FiSend className="w-5 h-5" />
                </button>
              </div>
              <p className="text-xs text-gray-400 dark:text-gray-500 text-center mt-2">
                Press <kbd className="px-1.5 py-0.5 bg-gray-100 dark:bg-gray-800 rounded text-xs font-medium">Enter</kbd> to send, <kbd className="px-1.5 py-0.5 bg-gray-100 dark:bg-gray-800 rounded text-xs font-medium">Shift+Enter</kbd> for newline
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Mobile overlay */}
      {mobileMenuOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-40 lg:hidden"
          onClick={() => setMobileMenuOpen(false)}
        />
      )}
    </div>
  );
}
