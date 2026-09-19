import apiClient from '../api/client'

export const sendCopilotMessage = (message, conversationHistory = null) =>
  apiClient.post('/ai/copilot/chat', {
    message,
    conversation_history: conversationHistory,
  })
