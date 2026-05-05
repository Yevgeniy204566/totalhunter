import React from 'react'
import ReactDOM from 'react-dom/client'
import { GoogleOAuthProvider } from '@react-oauth/google'
import App from './App.jsx'
import { LangProvider } from './lang.js'
import './styles/theme.css'
import './styles/mobile.css'

const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <GoogleOAuthProvider clientId={GOOGLE_CLIENT_ID}>
      <LangProvider>
        <App />
      </LangProvider>
    </GoogleOAuthProvider>
  </React.StrictMode>
)
