export default function Button({ children, variant = 'primary', className = '', ...props }) {
  const styles = {
    primary: 'bg-brand-red text-white hover:bg-brand-redDark',
    secondary: 'bg-white text-brand-blueDark border border-brand-blueSoft/30 hover:bg-brand-cream',
    danger: 'bg-brand-blueDark text-white hover:bg-brand-blue',
  };

  return (
    <button
      className={`inline-flex items-center justify-center rounded-xl px-4 py-2.5 text-sm font-semibold shadow-soft disabled:cursor-not-allowed disabled:opacity-60 ${styles[variant]} ${className}`}
      {...props}
    >
      {children}
    </button>
  );
}