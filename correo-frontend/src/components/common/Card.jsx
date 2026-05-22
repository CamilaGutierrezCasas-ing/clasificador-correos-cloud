export default function Card({ title, subtitle, actions, children, className = '' }) {
  return (
    <section className={`rounded-2xl border border-brand-blueSoft/20 bg-white p-6 shadow-soft ${className}`}>
      {(title || subtitle || actions) && (
        <div className="mb-5 flex flex-col gap-3 border-b border-brand-blueSoft/10 pb-4 md:flex-row md:items-start md:justify-between">
          <div>
            {title && <h2 className="text-lg font-semibold text-brand-blueDark">{title}</h2>}
            {subtitle && <p className="mt-1 text-sm text-slate-500">{subtitle}</p>}
          </div>
          {actions && <div>{actions}</div>}
        </div>
      )}
      {children}
    </section>
  );
}