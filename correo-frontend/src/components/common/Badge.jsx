export default function Badge({ children, color = 'default' }) {
  const colors = {
    default: 'bg-brand-cream text-brand-blueDark',
    green: 'bg-emerald-100 text-emerald-700',
    blue: 'bg-brand-blueSoft/20 text-brand-blueDark',
    amber: 'bg-amber-100 text-amber-700',
    rose: 'bg-rose-100 text-rose-700',
    red: 'bg-brand-red/10 text-brand-red',
  };

  return (
    <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${colors[color]}`}>
      {children}
    </span>
  );
}