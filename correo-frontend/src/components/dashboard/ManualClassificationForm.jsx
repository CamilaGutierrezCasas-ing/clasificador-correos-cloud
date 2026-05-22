import { useState } from 'react';
import { classifyEmail } from '../../api/emailApi';
import Button from '../common/Button';
import Card from '../common/Card';
import Input from '../common/Input';
import Textarea from '../common/Textarea';

const initialState = {
  subject: '',
  sender: '',
  source_account: 'local-demo',
  body: '',
};

export default function ManualClassificationForm({ onCreated }) {
  const [form, setForm] = useState(initialState);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  const handleChange = (event) => {
    setForm((prev) => ({ ...prev, [event.target.name]: event.target.value }));
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setLoading(true);
    setMessage('');
    setError('');

    try {
      const response = await classifyEmail(form);
      setMessage(`Correo clasificado como ${response.email.predicted_category} con modelo ${response.model_version}.`);
      setForm(initialState);
      onCreated(response.email);
    } catch (err) {
      setError(err?.response?.data?.detail || 'No se pudo clasificar el correo');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card title="Clasificación manual de prueba" subtitle="Útil mientras se completa la sincronización automática desde Microsoft Graph.">
      <form className="grid gap-4" onSubmit={handleSubmit}>
        <div className="grid gap-4 md:grid-cols-2">
          <Input label="Asunto" name="subject" value={form.subject} onChange={handleChange} placeholder="Solicitud urgente" />
          <Input label="Remitente" name="sender" value={form.sender} onChange={handleChange} placeholder="cliente@empresa.com" />
        </div>
        <Input label="Cuenta origen" name="source_account" value={form.source_account} onChange={handleChange} placeholder="cuenta-vinculada" />
        <Textarea label="Contenido del correo" name="body" value={form.body} onChange={handleChange} placeholder="Pega aquí el cuerpo del correo..." />
        {message && <p className="rounded-xl bg-emerald-50 px-4 py-3 text-sm text-emerald-700">{message}</p>}
        {error && <p className="rounded-xl bg-rose-50 px-4 py-3 text-sm text-rose-600">{error}</p>}
        <Button type="submit" disabled={loading}>
          {loading ? 'Clasificando...' : 'Clasificar correo'}
        </Button>
      </form>
    </Card>
  );
}
