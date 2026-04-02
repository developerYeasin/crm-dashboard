import axios from 'axios';

const API_PREFIX = '/api/ai';

export const chatApi = {
  // Conversations
  getConversations: () => axios.get(`${API_PREFIX}/conversations`),

  createConversation: (title) =>
    axios.post(`${API_PREFIX}/conversations`, { title }),

  getConversation: (id) => axios.get(`${API_PREFIX}/conversations/${id}`),

  deleteConversation: (id) => axios.delete(`${API_PREFIX}/conversations/${id}`),

  // Messages
  sendMessage: (conversationId, message) =>
    axios.post(`${API_PREFIX}/chat`, {
      ...message,
      conversation_id: conversationId
    }),
};
