import React, { useEffect } from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { GoogleOAuthProvider } from '@react-oauth/google'
import { Analytics } from '@vercel/analytics/react'
import App from './App.jsx'
import { LangProvider } from './lang.js'
import { startProtectLabels } from './lib/protectLabels.js'
import './styles/theme.css'
import './styles/mobile.css'

const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID

const container = document.getElementById('root')

// Подмена подписей и защита названий стартуют ТОЛЬКО после гидратации: эффект корня срабатывает, когда React
// закончил сверять страницу с серверной разметкой, иначе правки DOM вызвали бы расхождение.
function Boot({ children }) {
  useEffect(() => { startProtectLabels() }, [])
  return children
}

const app = (
  <React.StrictMode>
    <GoogleOAuthProvider clientId={GOOGLE_CLIENT_ID}>
      <BrowserRouter>
        <LangProvider>
          <Boot><App /></Boot>
        </LangProvider>
      </BrowserRouter>
    </GoogleOAuthProvider>
    <Analytics />
  </React.StrictMode>
)

if (container.hasChildNodes()) {
  ReactDOM.hydrateRoot(container, app)
} else {
  ReactDOM.createRoot(container).render(app)
}
