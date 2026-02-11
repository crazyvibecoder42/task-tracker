'use client';

import { usePathname } from 'next/navigation';
import Sidebar from '@/components/Sidebar';
import { AuthProvider, useAuth } from '@/contexts/AuthContext';

function LayoutContent({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { isAuthenticated, loading } = useAuth();

  // Pages that shouldn't show sidebar
  const noSidebarPages = ['/login', '/register'];
  const isAuthPage = noSidebarPages.some((page) => pathname?.startsWith(page));

  // Only show sidebar if:
  // 1. Not on auth pages (login/register)
  // 2. User is authenticated
  // 3. Not loading auth state
  const shouldShowSidebar = !isAuthPage && isAuthenticated && !loading;

  return (
    <div className="flex h-screen">
      {shouldShowSidebar && <Sidebar />}
      <main className={`flex-1 overflow-auto ${shouldShowSidebar ? '' : 'w-full'}`}>
        {children}
      </main>
    </div>
  );
}

export default function LayoutWrapper({ children }: { children: React.ReactNode }) {
  return (
    <AuthProvider>
      <LayoutContent>{children}</LayoutContent>
    </AuthProvider>
  );
}
