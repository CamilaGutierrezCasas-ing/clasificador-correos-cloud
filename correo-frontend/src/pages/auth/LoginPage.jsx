import { Link } from 'react-router-dom';
import LoginForm from '../../components/auth/LoginForm';
import AuthLayout from '../../layouts/AuthLayout';

export default function LoginPage() {
  return (
    <AuthLayout
      title="Iniciar sesión"
      subtitle="Accede al sistema con tu correo y contraseña."
    >
      <LoginForm />
      <p className="mt-6 text-center text-sm text-slate-500">
        ¿No tienes cuenta?{' '}
        <Link to="/registro" className="font-semibold text-slate-900">
          Regístrate aquí
        </Link>
      </p>
    </AuthLayout>
  );
}