export default function Input({ label, error, ...props }) {
  return (
    <label className="block space-y-2">
      {label && <span className="text-sm font-medium text-slate-700">{label}</span>}
      <input
        className="w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm outline-none ring-0 transition focus:border-slate-900"
        {...props}
      />
      {error && <span className="text-xs text-rose-600">{error}</span>}
    </label>
  );
}
