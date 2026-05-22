import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { meRequest } from '../../api/authApi';
import { useAuth } from '../../hooks/useAuth';
import Button from '../common/Button';

export default function LoginForm() {
  const navigate = useNavigate();
  const { login } = useAuth();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setErrorMessage('');

    try {
      await login({ email, password });

      const me = await meRequest();
      const roleName = (me?.role?.name || me?.role || '').toLowerCase();

      console.log('USER:', me);
      console.log('ROLE:', roleName);

      if (roleName === 'usuario') navigate('/usuario');
      else if (roleName === 'secretaria') navigate('/secretaria');
      else if (roleName === 'admin') navigate('/admin');
      else setErrorMessage('No se pudo identificar el rol del usuario.');
    } catch (error) {
      console.error('Error login:', error);
      setErrorMessage('No se pudo iniciar sesión.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <form className="space-y-4" onSubmit={handleSubmit}>
      <div>
        <label className="mb-1 block text-sm font-medium text-slate-700">
          Correo
        </label>
        <input
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="w-full rounded-xl border border-slate-300 px-4 py-3 outline-none focus:border-slate-500"
          placeholder="correo@ejemplo.com"
          required
        />
      </div>

      <div>
        <label className="mb-1 block text-sm font-medium text-slate-700">
          Contraseña
        </label>
        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="w-full rounded-xl border border-slate-300 px-4 py-3 outline-none focus:border-slate-500"
          placeholder="********"
          required
        />
      </div>

      {errorMessage && (
        <p className="text-sm text-rose-600">{errorMessage}</p>
      )}

      <Button type="submit" className="w-full" disabled={loading}>
        {loading ? 'Ingresando...' : 'Iniciar sesión'}
      </Button>
    </form>
  );
}