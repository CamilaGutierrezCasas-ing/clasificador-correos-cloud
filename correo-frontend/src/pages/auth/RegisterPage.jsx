import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import AuthLayout from '../../layouts/AuthLayout';
import Input from '../../components/common/Input';
import Button from '../../components/common/Button';
import { useAuth } from '../../hooks/useAuth';

export default function RegisterPage() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({ name: '', email: '', password: '' });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleChange = (event) => {
    setForm((prev) => ({ ...prev, [event.target.name]: event.target.value }));
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setLoading(true);
    setError('');
    try {
      const user = await register(form);
      if (user.role.name === 'admin') navigate('/admin');
      else if (user.role.name === 'secretaria') navigate('/secretaria');
      else navigate('/usuario');
    } catch (err) {
      setError(err?.response?.data?.detail || 'No se pudo crear la cuenta');
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthLayout title="Crear cuenta" subtitle="Registra un nuevo usuario para acceder al sistema.">
      <form className="space-y-4" onSubmit={handleSubmit}>
        <Input label="Nombre completo" name="name" value={form.name} onChange={handleChange} required />
        <Input label="Correo electrónico" name="email" type="email" value={form.email} onChange={handleChange} required />
        <Input label="Contraseña" name="password" type="password" value={form.password} onChange={handleChange} required />
        {error && <p className="rounded-xl bg-rose-50 px-4 py-3 text-sm text-rose-600">{error}</p>}
        <Button type="submit" className="w-full" disabled={loading}>{loading ? 'Creando cuenta...' : 'Registrarme'}</Button>
      </form>
      <p className="mt-6 text-center text-sm text-slate-500">
        ¿Ya tienes cuenta? <Link to="/login" className="font-semibold text-slate-900">Inicia sesión</Link>
      </p>
    </AuthLayout>
  );
}
