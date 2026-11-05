import os
import requests
import feedparser
import re, html, json
from pathlib import Path
from datetime import datetime, timedelta, timezone

# --- CONFIGURACIÓN ---
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RSS_URLS = [
    # WeWorkRemotely - Data Jobs
    "https://weworkremotely.com/categories/remote-data-jobs.rss",
    # WeWorkRemotely - Back-End
    "https://weworkremotely.com/categories/remote-back-end-programming-jobs.rss",
    # Jobicy - Data Science & Engineering
    "https://jobicy.com/?feed=job_feed&job_categories=data-science",
    # Remotive - Data (XML nativo)
    "https://remotive.com/api/remote-jobs?category=data&format=rss",
    # Feeds personalizados RSS.app
    "https://rss.app/feeds/jvEm3BPpjgctiLZU.xml",
    "https://rss.app/feeds/wKEAexrXjr3ThK1r.xml"
]

KEYWORDS_TECNICAS = [
    "data quality", "python", "pytorch", "data engineer", "biomedical",
    "healthtech", "healthcare", "machine learning", "dataset", 
    "signal processing", "computer vision", "pandas", "imu", "data pipeline"
]

TIPO_CONTRATO = ["intern", "internship", "prácticas", "beca", "trainee", "junior", "entry level"]

GEO_PRIORIDAD_ALTA = ["alicante", "valencia", "madrid", "remoto", "remote", "hybrid", "híbrido"]
GEO_PRIORIDAD_MEDIA = ["barcelona", "suiza", "switzerland", "alemania", "germany", "deutschland", "suisse"]
KEYWORDS_RECHAZADAS = ["onsite london", "onsite paris", "senior", "lead", "director", "5+ years", "unpaid"]
SENIORITY_TITULO = ["senior", "lead", "director", "principal", "staff"]
RECHAZO_FRASES = ["us only", "usa only", "north america only", "5+ years", "unpaid"]

def contiene(termino, texto):
    return re.search(rf"\b{re.escape(termino)}\b", texto) is not None

def enviar_telegram(mensaje):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("Faltan credenciales de Telegram.")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": mensaje, "parse_mode": "HTML", "disable_web_page_preview": True}
    requests.post(url, json=payload)

def clasificar_oferta(titulo, descripcion):
    titulo = titulo.lower()
    texto = f"{titulo} {descripcion}".lower()
    if any(contiene(k, titulo) for k in SENIORITY_TITULO):
        return None
    if any(contiene(k, texto) for k in RECHAZO_FRASES):
        return None
    if not any(contiene(k, texto) for k in KEYWORDS_TECNICAS):
        return None  # la tecnología es obligatoria; el contrato solo suma
    # ... resto de tu lógica de geografía, usando contiene() en lugar de "in"
    if any(mala_kw in texto for mala_kw in KEYWORDS_RECHAZADAS):
        return None
        
    tech_match = [kw for kw in KEYWORDS_TECNICAS if kw in texto]
    contrato_match = [kw for kw in TIPO_CONTRATO if kw in texto]
    
    if not tech_match and not contrato_match:
        return None

    alta_geo = [g for g in GEO_PRIORIDAD_ALTA if g in texto]
    media_geo = [g for g in GEO_PRIORIDAD_MEDIA if g in texto]

    is_barcelona = "barcelona" in texto
    is_flexible = "remote" in texto or "remoto" in texto or "hybrid" in texto or "híbrido" in texto

    if alta_geo and not (is_barcelona and not is_flexible):
        return "Tier A 🟢"
    elif media_geo or (is_barcelona and not is_flexible):
        return "Tier B 🟡"
    
    SEEN = Path("seen.json")
    seen = set(json.loads(SEEN.read_text())) if SEEN.exists() else set()
    
    return None

def buscar_ofertas():
    ayer = datetime.now(timezone.utc) - timedelta(days=1)
    ofertas_tier_a = []
    ofertas_tier_b = []

    for url in RSS_URLS:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries:
                if entry.link in seen: continue ; seen.add(entry.link)
                try:
                    fecha_pub = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
                    if fecha_pub < ayer:
                        continue
                except Exception:
                    pass
                
                texto_completo = (entry.title + " " + (entry.description if hasattr(entry, 'description') else '')).lower()
                tier = clasificar_oferta(texto_completo)
                
                oferta_data = {
                    "titulo": entry.title,
                    "link": entry.link,
                    "empresa": getattr(entry, 'author', 'Empresa Oculta')
                }
                
                if tier == "Tier A 🟢":
                    ofertas_tier_a.append(oferta_data)
                elif tier == "Tier B 🟡":
                    ofertas_tier_b.append(oferta_data)
                    
        except Exception as e:
            print(f"Error parseando {url}: {e}")

    return ofertas_tier_a, ofertas_tier_b

def main():
    tier_a, tier_b = buscar_ofertas()
    
    if tier_a or tier_b:
        mensaje = "🤖 <b>Job-Radar Healthtech Actualizado</b>\n\n"
        
        if tier_a:
            mensaje += "🔥 <b>TIER A (Prioridad Alta)</b>\n"
            for o in tier_a[:5]:
                mensaje += f"▪️ {o['empresa']} - {o['titulo']}\n<a href='{o['link']}'>Ver Oferta</a>\n\n"
                
        if tier_b:
            mensaje += "🌍 <b>TIER B (Prioridad Media)</b>\n"
            for o in tier_b[:5]:
                mensaje += f"▪️ {o['empresa']} - {o['titulo']}\n<a href='{o['link']}'>Ver Oferta</a>\n\n"
                
        enviar_telegram(mensaje)
    else:
        enviar_telegram("🤖 Job-Radar ejecutado: 0 nuevas ofertas relevantes hoy.")
    SEEN.write_text(json.dumps(sorted(seen)))

if __name__ == "__main__":
    main()
