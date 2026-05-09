import { Route, Routes } from 'react-router-dom'
import { Toaster } from '@/components/ui/sonner'
import { ProtectedRoute } from '@/components/auth/ProtectedRoute'
import { RootRedirect } from '@/components/auth/RootRedirect'
import { AppShell } from '@/components/layout/AppShell'
import LoginPage from '@/pages/LoginPage'
import RegisterPage from '@/pages/RegisterPage'
import ChatPage from '@/pages/ChatPage'
import NotFoundPage from '@/pages/NotFoundPage'

export default function App() {
  return (
    <>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route element={<ProtectedRoute />}>
          <Route element={<AppShell />}>
            <Route path="/chat" element={<ChatPage />} />
            <Route path="/chat/:id" element={<ChatPage />} />
          </Route>
        </Route>
        <Route path="/" element={<RootRedirect />} />
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
      <Toaster richColors position="top-center" />
    </>
  )
}
