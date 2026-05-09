import { useEffect, useState } from 'react';
import { useLocation } from 'react-router-dom';
import { Menu } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  Sheet,
  SheetContent,
  SheetTitle,
  SheetTrigger,
} from '@/components/ui/sheet';
import { Sidebar } from './Sidebar';
import { ThemeToggle } from './ThemeToggle';

export function Header() {
  const [open, setOpen] = useState(false);
  const location = useLocation();

  useEffect(() => {
    setOpen(false);
  }, [location]);

  return (
    <header className="flex h-14 shrink-0 items-center gap-2 border-b border-border bg-card px-4">
      <Sheet open={open} onOpenChange={setOpen}>
        <SheetTrigger asChild>
          <Button
            variant="ghost"
            size="icon"
            className="md:hidden"
            aria-label="Abrir menu"
          >
            <Menu className="h-5 w-5" />
          </Button>
        </SheetTrigger>
        <SheetContent side="left" className="w-[280px] p-0 sm:max-w-[280px]">
          <SheetTitle className="sr-only">Menu</SheetTitle>
          <Sidebar />
        </SheetContent>
      </Sheet>
      <h1 className="text-base font-semibold">Barbearia AI</h1>
      <div className="ml-auto">
        <ThemeToggle />
      </div>
    </header>
  );
}
