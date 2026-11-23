import { createBrowserRouter, Navigate } from 'react-router-dom';
import { LoginPage } from '../features/auth/LoginPage';
import { AppShell } from '../components/layout/AppShell';
import { ChatPage } from '../features/chat/ChatPage';
import { AdminLayout } from '../features/admin/AdminLayout';
import { DocumentsPage } from '../features/admin/DocumentsPage';
import { IngestionPage } from '../features/admin/IngestionPage';
import { QuarantinePage } from '../features/admin/QuarantinePage';
import { UsersPage } from '../features/admin/UsersPage';
import { AuditPage } from '../features/admin/AuditPage';
import { MonitoringPage } from '../features/admin/MonitoringPage';
import { ProtectedRoute } from './ProtectedRoute';
import { AdminRoute } from './AdminRoute';

export const router = createBrowserRouter([
  {
    path: '/login',
    element: <LoginPage />,
  },
  {
    element: <ProtectedRoute />,
    children: [
      {
        path: '/',
        element: <Navigate to="/chat" replace />,
      },
      {
        path: '/chat',
        element: <AppShell />,
        children: [
          {
            index: true,
            element: <ChatPage />,
          },
          {
            path: ':conversationId',
            element: <ChatPage />,
          },
        ],
      },
      {
        path: '/admin',
        element: <AdminRoute />,
        children: [
          {
            element: <AdminLayout />,
            children: [
              {
                index: true,
                element: <Navigate to="/admin/documents" replace />,
              },
              {
                path: 'documents',
                element: <DocumentsPage />,
              },
              {
                path: 'ingestion',
                element: <IngestionPage />,
              },
              {
                path: 'quarantine',
                element: <QuarantinePage />,
              },
              {
                path: 'users',
                element: <UsersPage />,
              },
              {
                path: 'audit',
                element: <AuditPage />,
              },
              {
                path: 'monitoring',
                element: <MonitoringPage />,
              },
            ],
          },
        ],
      },
    ],
  },
  {
    path: '*',
    element: <Navigate to="/chat" replace />,
  },
]);
