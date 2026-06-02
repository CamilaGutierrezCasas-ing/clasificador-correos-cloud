from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
service_path = ROOT / "backend_base" / "app" / "services" / "email_service.py"

if not service_path.exists():
    raise SystemExit(f"No encontré el archivo: {service_path}")

text = service_path.read_text(encoding="utf-8")

# Bajar el umbral visual de revisión sugerida: evita que el panel parezca alarmante.
text = re.sub(
    r"LOW_CONFIDENCE_STATS_THRESHOLD\s*=\s*[0-9.]+",
    "LOW_CONFIDENCE_STATS_THRESHOLD = 0.15",
    text,
)

# Asegurar que baja confianza NO convierta la categoría a otros.
text = re.sub(
    r"\n\s*if\s+confidence\s*<\s*CONFIDENCE_THRESHOLD\s*:\s*\n\s*category\s*=\s*[\"']otros[\"']",
    "",
    text,
)

service_path.write_text(text, encoding="utf-8")
print("OK: email_service.py actualizado: LOW_CONFIDENCE_STATS_THRESHOLD=0.15 y sin forzar 'otros'.")
