import { Routes, Route, Navigate } from 'react-router-dom'
import { isLoggedIn } from './auth.js'
import Layout from './components/Layout.jsx'
import LandingPage from './pages/LandingPage.jsx'
import LoginPage from './pages/LoginPage.jsx'
import DashboardPage from './pages/DashboardPage.jsx'
import BalancePage from './pages/BalancePage.jsx'
import ReferralsPage from './pages/ReferralsPage.jsx'
import FeedbackPage from './pages/FeedbackPage.jsx'
import GuidePage from './pages/GuidePage.jsx'
import LegalPage from './pages/LegalPage.jsx'
import ContactsPage from './pages/ContactsPage.jsx'
import RefPage from './pages/RefPage.jsx'
import DownloadPage from './pages/DownloadPage.jsx'
import EarnPage from './pages/EarnPage.jsx'
import ReferralTreePage from './pages/ReferralTreePage.jsx'
import RoyPage from './pages/RoyPage.jsx'
import ChestsPage from './pages/ChestsPage.jsx'
import ChestSummaryPage from './pages/ChestSummaryPage.jsx'
import AncientsPage from './pages/AncientsPage.jsx'
import RosterPage from './pages/RosterPage.jsx'

function PrivateRoute({ element }) {
  return isLoggedIn() ? element : <Navigate to="/login" replace />
}

export default function App() {
  return (
    <Routes>
      {/* ── EN public routes (default) ──────────────────── */}
      <Route path="/"          element={<LandingPage />} />
      <Route path="/guide"     element={<GuidePage />} />
      <Route path="/legal"     element={<LegalPage />} />
      <Route path="/contacts"  element={<ContactsPage />} />
      <Route path="/download"  element={<DownloadPage />} />
      <Route path="/login"     element={<LoginPage />} />
      <Route path="/ref/:code" element={<RefPage />} />
      <Route path="/chests/:slug" element={<ChestSummaryPage />} />
      <Route path="/c/:kingdom/:slug" element={<ChestSummaryPage />} />

      {/* ── RU public routes (/ru prefix) ───────────────── */}
      <Route path="/ru"              element={<LandingPage />} />
      <Route path="/ru/guide"        element={<GuidePage />} />
      <Route path="/ru/legal"        element={<LegalPage />} />
      <Route path="/ru/contacts"     element={<ContactsPage />} />
      <Route path="/ru/download"     element={<DownloadPage />} />
      <Route path="/ru/login"        element={<LoginPage />} />

      {/* ── Dashboard (no lang prefix, auth-protected) ──── */}
      <Route path="/dashboard" element={<PrivateRoute element={<Layout />} />}>
        <Route index               element={<DashboardPage />} />
        <Route path="balance"   element={<BalancePage />} />
        <Route path="referrals" element={<ReferralsPage />} />
        <Route path="chests"    element={<ChestsPage />} />
        <Route path="ancients"  element={<AncientsPage />} />
        <Route path="roster"    element={<RosterPage />} />
        <Route path="feedback" element={<FeedbackPage />} />
        <Route path="earn"    element={<EarnPage />} />
        <Route path="roy"     element={<RoyPage />} />
      </Route>
      <Route path="/dashboard/tree" element={<PrivateRoute element={<ReferralTreePage />} />} />

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
