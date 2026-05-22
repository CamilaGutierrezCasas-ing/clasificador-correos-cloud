import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import Card from '../../components/common/Card';

export default function MicrosoftCallbackPage() {
  const navigate = useNavigate();
  const [message, setMessage] = useState('Conectando cuenta Microsoft...');

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const status = params.get('status');
    const callbackMessage = params.get('message');

    if (status === 'success') {
      setMessage(callbackMessage || 'Cuenta Microsoft conectada correctamente');
    } else {
      setMessage(callbackMessage || 'No se pudo completar la conexión con Microsoft');
    }

    const timer = setTimeout(() => {
      navigate('/usuario');
    }, 1500);

    return () => clearTimeout(timer);
  }, [navigate]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-brand-cream p-6">
      <div className="w-full max-w-lg">
        <Card title="Microsoft OAuth" subtitle="Procesando vinculación de cuenta">
          <p className="rounded-2xl bg-brand-cream px-4 py-4 text-sm text-brand-blueDark">
            {message}
          </p>
        </Card>
      </div>
    </div>
  );
}