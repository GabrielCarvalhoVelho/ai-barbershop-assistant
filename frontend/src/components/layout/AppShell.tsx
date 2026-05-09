import { Outlet } from 'react-router-dom';
import { Header } from './Header';
import { Sidebar } from './Sidebar';

export function AppShell() {
  return (
    <div className="flex h-dvh bg-background">
      <aside className="hidden w-[280px] shrink-0 border-r border-border bg-card md:flex md:flex-col">
        <Sidebar />
      </aside>
      <div className="flex min-w-0 flex-1 flex-col">
        <Header />
        <main className="min-h-0 flex-1">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
