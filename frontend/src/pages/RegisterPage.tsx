import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Link, Navigate, useNavigate } from 'react-router-dom';
import { Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { useAuth } from '@/hooks/useAuth';
import { ApiException } from '@/lib/api';

const registerSchema = z
  .object({
    name: z
      .string()
      .min(2, 'Nome deve ter ao menos 2 caracteres.')
      .max(100, 'Nome deve ter no máximo 100 caracteres.'),
    phone: z
      .string()
      .min(10, 'Telefone deve ter ao menos 10 caracteres.')
      .max(20, 'Telefone deve ter no máximo 20 caracteres.'),
    email: z.string().email('Email inválido.').or(z.literal('')),
    password: z.string().min(6, 'Senha deve ter ao menos 6 caracteres.'),
    passwordConfirm: z.string(),
  })
  .refine((d) => d.password === d.passwordConfirm, {
    message: 'Senhas não conferem.',
    path: ['passwordConfirm'],
  });

type RegisterForm = z.infer<typeof registerSchema>;

export default function RegisterPage() {
  const { isAuthenticated, register: registerUser } = useAuth();
  const navigate = useNavigate();

  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<RegisterForm>({ resolver: zodResolver(registerSchema) });

  if (isAuthenticated) {
    return <Navigate to="/chat" replace />;
  }

  const onSubmit = async (data: RegisterForm) => {
    try {
      await registerUser({
        name: data.name.trim(),
        phone: data.phone.trim(),
        password: data.password,
        email: data.email.trim() === '' ? null : data.email.trim(),
      });
      navigate('/chat', { replace: true });
    } catch (e) {
      if (e instanceof ApiException) {
        if (e.code === 'AUTH_004') {
          setError('phone', { message: 'Telefone já cadastrado.' });
          return;
        }
        if (e.isRateLimit) {
          toast.error('Muitas tentativas. Aguarde alguns segundos.');
          return;
        }
        if (e.isNetworkError) {
          toast.error('Sem conexão com o servidor.');
          return;
        }
        toast.error(e.message);
      } else {
        toast.error('Erro inesperado.');
      }
    }
  };

  return (
    <div className="flex min-h-dvh items-center justify-center bg-background p-4">
      <div className="w-full max-w-md space-y-6 rounded-lg border border-border bg-card p-6 shadow-sm">
        <div className="space-y-1">
          <h1 className="text-2xl font-semibold">Criar conta</h1>
          <p className="text-sm text-muted-foreground">
            Cadastre-se para conversar com o assistente da barbearia.
          </p>
        </div>

        <form
          onSubmit={handleSubmit(onSubmit)}
          className="space-y-4"
          noValidate
        >
          <div className="space-y-1.5">
            <Label htmlFor="name">Nome</Label>
            <Input
              id="name"
              type="text"
              autoComplete="name"
              placeholder="Seu nome completo"
              {...register('name')}
              aria-invalid={!!errors.name}
            />
            {errors.name && (
              <p className="text-sm text-destructive">{errors.name.message}</p>
            )}
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="phone">Telefone</Label>
            <Input
              id="phone"
              type="tel"
              autoComplete="tel"
              placeholder="+5511999000000"
              {...register('phone')}
              aria-invalid={!!errors.phone}
            />
            {errors.phone && (
              <p className="text-sm text-destructive">{errors.phone.message}</p>
            )}
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="email">
              Email <span className="text-muted-foreground">(opcional)</span>
            </Label>
            <Input
              id="email"
              type="email"
              autoComplete="email"
              placeholder="voce@exemplo.com"
              {...register('email')}
              aria-invalid={!!errors.email}
            />
            {errors.email && (
              <p className="text-sm text-destructive">{errors.email.message}</p>
            )}
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="password">Senha</Label>
            <Input
              id="password"
              type="password"
              autoComplete="new-password"
              {...register('password')}
              aria-invalid={!!errors.password}
            />
            {errors.password && (
              <p className="text-sm text-destructive">
                {errors.password.message}
              </p>
            )}
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="passwordConfirm">Confirmar senha</Label>
            <Input
              id="passwordConfirm"
              type="password"
              autoComplete="new-password"
              {...register('passwordConfirm')}
              aria-invalid={!!errors.passwordConfirm}
            />
            {errors.passwordConfirm && (
              <p className="text-sm text-destructive">
                {errors.passwordConfirm.message}
              </p>
            )}
          </div>

          <Button type="submit" className="w-full" disabled={isSubmitting}>
            {isSubmitting ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              'Criar conta'
            )}
          </Button>
        </form>

        <p className="text-center text-sm text-muted-foreground">
          Já tem conta?{' '}
          <Link to="/login" className="font-medium text-primary hover:underline">
            Entrar
          </Link>
        </p>
      </div>
    </div>
  );
}
