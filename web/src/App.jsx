import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { isLoggedIn } from './auth.js'
import Layout from './components/Layout.jsx'
import LandingPage from './pages/LandingPage.jsx'
import LoginPage from './pages/LoginPage.jsx'
import DashboardPage from './pages/DashboardPage.jsx'
import BalancePage from './pages/BalancePage.jsx'
import HuntsPage from './pages/HuntsPage.jsx'
import ReferralsPage from './pages/ReferralsPage.jsx'
import DevicesPage from './pages/DevicesPage.jsx'
import TransactionsPage from './pages/TransactionsPage.jsx'
import FeedbackPage from './pages/FeedbackPage.jsx'
import GuidePage from './pages/GuidePage.jsx'
import LegalPage from './pages/LegalPage.jsx'
import ContactsPage from './pages/ContactsPage.jsx'
import RefPage from './pages/RefPage.jsx'
import DownloadPage from './pages/DownloadPage.jsx'

function PrivateRoute({ element }) {
  return isLoggedIn() ? element : <Navigate to="/login" replace />
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/"           element={<LandingPage />} />
        <Route path="/login"      element={<LoginPage />} />
        <Route path="/guide"      element={<GuidePage />} />
        <Route path="/legal"      element={<LegalPage />} />
        <Route path="/contacts"   element={<ContactsPage />} />
        <Route path="/ref/:code"  element={<RefPage />} />
        <Route path="/download"   element={<DownloadPage />} />
        <Route path="/dashboard"  element={<PrivateRoute element={<Layout />} />}>
          <Route index             element={<DashboardPage />} />
          <Route path="balance"      element={<BalancePage />} />
          <Route path="hunts"        element={<HuntsPage />} />
          <Route path="referrals"    element={<ReferralsPage />} />
          <Route path="devices"      element={<DevicesPage />} />
          <Route path="transactions" element={<TransactionsPage />} />
          <Route path="feedback"     element={<FeedbackPage />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
