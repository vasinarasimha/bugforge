import { useState, useRef, useEffect } from 'react'
import { sendCopilotMessage } from '../../services/copilotService'

const SUGGESTED_PROMPTS = [
  'How many open critical issues do we have?',
  'Show me a summary of all projects',
  'Search for issues related to login',
  'What are the analytics trends for the last 30 days?',
]

export default function CopilotDrawer() {
  const [isOpen, setIsOpen] = useState(false)
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const messagesEndRef = useRef(null)
  const inputRef = useRef(null)

  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  }, [messages])

  useEffect(() => {
    if (isOpen && inputRef.current) {
      inputRef.current.focus()
    }
  }, [isOpen])

  const buildConversationHistory = () => {
    return messages.map((m) => ({
      role: m.role,
      content: m.content,
    }))
  }

  const handleSend = async (text) => {
    const msg = (text || input).trim()
    if (!msg || isLoading) return

    const userMessage = { role: 'user', content: msg, timestamp: Date.now() }
    setMessages((prev) => [...prev, userMessage])
    setInput('')
    setIsLoading(true)

    try {
      const history = buildConversationHistory()
      const { data } = await sendCopilotMessage(msg, history)
      const assistantMessage = {
        role: 'assistant',
        content: data.reply,
        tools_used: data.tools_used || [],
        timestamp: Date.now(),
      }
      setMessages((prev) => [...prev, assistantMessage])
    } catch (err) {
      const errorMsg =
        err.response?.data?.detail || 'Failed to reach the AI Copilot. Please try again.'
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: errorMsg, isError: true, timestamp: Date.now() },
      ])
    } finally {
      setIsLoading(false)
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleClear = () => {
    setMessages([])
  }

  const renderMarkdown = (text) => {
    if (!text) return ''
    // Basic markdown: bold, italic, code blocks, inline code, lists
    let html = text
      .replace(/```([\s\S]*?)```/g, '<pre class="copilot-code-block">$1</pre>')
      .replace(/`([^`]+)`/g, '<code class="copilot-inline-code">$1</code>')
      .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.+?)\*/g, '<em>$1</em>')
      .replace(/^[-•]\s+(.+)$/gm, '<li>$1</li>')
      .replace(/^(\d+)\.\s+(.+)$/gm, '<li>$2</li>')
      .replace(/\n/g, '<br/>')

    // Wrap consecutive <li> tags in <ul>
    html = html.replace(/((?:<li>.*?<\/li>(?:<br\/>)?)+)/g, '<ul class="copilot-list">$1</ul>')
    return html
  }

  return (
    <>
      {/* Floating trigger button */}
      <button
        className={`copilot-fab ${isOpen ? 'copilot-fab--open' : ''}`}
        onClick={() => setIsOpen(!isOpen)}
        aria-label={isOpen ? 'Close AI Copilot' : 'Open AI Copilot'}
        title="AI Copilot"
      >
        {isOpen ? (
          <i className="bi bi-x-lg" />
        ) : (
          <i className="bi bi-stars" />
        )}
      </button>

      {/* Drawer panel */}
      {isOpen && (
        <div className="copilot-drawer" role="dialog" aria-label="AI Copilot">
          {/* Header */}
          <div className="copilot-header">
            <div className="copilot-header-left">
              <i className="bi bi-stars copilot-header-icon" />
              <div>
                <h3 className="copilot-title">AI Copilot</h3>
                <span className="copilot-subtitle">Powered by Llama</span>
              </div>
            </div>
            <div className="copilot-header-actions">
              {messages.length > 0 && (
                <button
                  className="copilot-btn-icon"
                  onClick={handleClear}
                  title="Clear conversation"
                >
                  <i className="bi bi-trash3" />
                </button>
              )}
              <button
                className="copilot-btn-icon"
                onClick={() => setIsOpen(false)}
                title="Close"
              >
                <i className="bi bi-x-lg" />
              </button>
            </div>
          </div>

          {/* Messages */}
          <div className="copilot-messages">
            {messages.length === 0 && !isLoading && (
              <div className="copilot-welcome">
                <div className="copilot-welcome-icon">
                  <i className="bi bi-robot" />
                </div>
                <p className="copilot-welcome-text">
                  Hi! I'm your BugForge AI Copilot. I can help you search issues, check analytics, explore projects, and more.
                </p>
                <div className="copilot-suggestions">
                  {SUGGESTED_PROMPTS.map((prompt, idx) => (
                    <button
                      key={idx}
                      className="copilot-suggestion-chip"
                      onClick={() => handleSend(prompt)}
                    >
                      {prompt}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {messages.map((msg, idx) => (
              <div
                key={idx}
                className={`copilot-msg copilot-msg--${msg.role} ${msg.isError ? 'copilot-msg--error' : ''}`}
              >
                <div className="copilot-msg-avatar">
                  <i className={`bi ${msg.role === 'user' ? 'bi-person-fill' : 'bi-stars'}`} />
                </div>
                <div className="copilot-msg-body">
                  {msg.role === 'assistant' ? (
                    <div
                      className="copilot-msg-content"
                      dangerouslySetInnerHTML={{ __html: renderMarkdown(msg.content) }}
                    />
                  ) : (
                    <div className="copilot-msg-content">{msg.content}</div>
                  )}
                  {msg.tools_used && msg.tools_used.length > 0 && (
                    <div className="copilot-tools-used">
                      <i className="bi bi-gear-fill" />
                      <span>
                        Used: {msg.tools_used.map((t) => t.replace(/_/g, ' ')).join(', ')}
                      </span>
                    </div>
                  )}
                </div>
              </div>
            ))}

            {isLoading && (
              <div className="copilot-msg copilot-msg--assistant">
                <div className="copilot-msg-avatar">
                  <i className="bi bi-stars" />
                </div>
                <div className="copilot-msg-body">
                  <div className="copilot-typing">
                    <span className="copilot-dot" />
                    <span className="copilot-dot" />
                    <span className="copilot-dot" />
                  </div>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Input area */}
          <div className="copilot-input-area">
            <textarea
              ref={inputRef}
              className="copilot-input"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask about issues, analytics, projects..."
              rows={1}
              disabled={isLoading}
            />
            <button
              className="copilot-send-btn"
              onClick={() => handleSend()}
              disabled={!input.trim() || isLoading}
              title="Send message"
            >
              <i className="bi bi-send-fill" />
            </button>
          </div>
        </div>
      )}
    </>
  )
}
