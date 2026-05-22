const categories = ['todos', 'urgente', 'trabajo', 'educacion', 'spam', 'salud', 'otros'];

export default function EmailCategoriesSidebar({ selected, onSelect }) {
  return (
    <div className="rounded-2xl border border-brand-blueSoft/20 bg-white p-4 shadow-soft">
      <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-brand-blue">
        Categorías
      </p>
      <div className="space-y-2">
        {categories.map((category) => (
          <button
            key={category}
            onClick={() => onSelect(category)}
            className={`w-full rounded-xl px-3 py-2 text-left text-sm font-medium ${
              selected === category
                ? 'bg-brand-blueDark text-white'
                : 'text-slate-700 hover:bg-brand-cream'
            }`}
          >
            {category === 'todos' ? 'Todos' : category}
          </button>
        ))}
      </div>
    </div>
  );
}