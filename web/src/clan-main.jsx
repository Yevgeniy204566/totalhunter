import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import ChestSummaryPage from './pages/ChestSummaryPage.jsx'
import PublicAncientsPage from './pages/PublicAncientsPage.jsx'
import { setNeutralMode } from './api.js'
import './styles/theme.css'
import './styles/mobile.css'

setNeutralMode()

// Отдельная точка входа для нейтрального домена: в бандле только публичные страницы клана —
// ни лендинга, ни кабинета, ни гайда (их строки не должны попадать в JS этого домена).
ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <BrowserRouter>
      <Routes>
        <Route path="/c/:kingdom/:slug" element={<ChestSummaryPage neutral />} />
        <Route path="/chests/:slug" element={<ChestSummaryPage neutral />} />
        <Route path="/ancients/:slug" element={<PublicAncientsPage />} />
        <Route path="*" element={null} />
      </Routes>
    </BrowserRouter>
  </React.StrictMode>
)
