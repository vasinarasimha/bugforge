import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import App from './App'
import { AuthProvider } from './context/AuthContext'
import 'bootstrap/dist/css/bootstrap.min.css'
import 'bootstrap-icons/font/bootstrap-icons.css'
import './index.css'

// Globally enforce autocomplete="off" on all forms, inputs, and textareas
if (typeof document !== 'undefined') {
  const disableAutocomplete = (root = document) => {
    try {
      const elements = root.querySelectorAll ? root.querySelectorAll('form, input, textarea, select') : []
      elements.forEach((el) => {
        if (el.tagName === 'FORM' || el.tagName === 'INPUT' || el.tagName === 'TEXTAREA') {
          if (el.getAttribute('autocomplete') !== 'off') {
            el.setAttribute('autocomplete', 'off')
          }
        }
      })
    } catch {
      // ignore
    }
  }

  disableAutocomplete(document)

  const observer = new MutationObserver((mutations) => {
    for (const mutation of mutations) {
      if (mutation.addedNodes && mutation.addedNodes.length) {
        mutation.addedNodes.forEach((node) => {
          if (node.nodeType === 1) {
            if (node.matches && (node.matches('input, form, textarea, select'))) {
              node.setAttribute('autocomplete', 'off')
            }
            disableAutocomplete(node)
          }
        })
      }
    }
  })

  observer.observe(document.documentElement, { childList: true, subtree: true })
}

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <BrowserRouter>
      <AuthProvider><App /></AuthProvider>
    </BrowserRouter>
  </StrictMode>,
)

