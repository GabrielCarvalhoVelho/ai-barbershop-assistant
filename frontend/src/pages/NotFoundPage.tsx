import { Link } from 'react-router-dom';

export default function NotFoundPage() {
  return (
    <div className="flex min-h-dvh flex-col items-center justify-center gap-2 p-4 text-center">
      <h1 className="text-3xl font-semibold">404</h1>
      <p className="text-muted-foreground">Página não encontrada.</p>
      <Link to="/" className="text-primary hover:underline">
        Voltar ao início
      </Link>
    </div>
  );
}
