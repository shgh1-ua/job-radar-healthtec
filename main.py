import os
import requests
import feedparser
from datetime import datetime, timedelta, timezone

# --- CONFIGURACIÓN ---
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

# Fuentes RSS de empleo (puedes añadir más si soportan RSS)
RSS_URLS = [
    "https://remotive.com/api/remote-jobs?category=software-dev&limit=50", # API abierta, formato JSON, requiere adaptación pero para este ejemplo usaremos feeds puros
    "https://rss.app/feeds/v1.1/tR7xW9..." # Ejemplo de feed público (luego te diré cómo sacar feeds gratuitos de búsquedas de LinkedIn/Infojobs mediante RSS.app u open-source)
    # Por ahora usaremos un feed de prueba de WeWorkRemotely para Data / Programming
    "https://weworkremotely.com/categories/remote-back-end-programming-jobs.rss",
    "https://weworkremotely.com/categories/remote-data-jobs.rss"
]

# Keywords de tu perfil para obligar a que la oferta pase el filtro
# Si la oferta tiene AL MENOS UNA de estas, nos interesa revisarla.
KEYWORDS_ACEPTADAS = [
    "data quality", "python", "pytorch", "data engineer", "biomedical",
    "healthtech", "healthcare", "machine learning", "dataset",
    "signal processing", "computer vision", "pandas"
]

# Zonas geográficas / Trabajo remoto
GEOGRAFIA = ["remote", "remoto", "alicante", "valencia", "madrid", "spain", "europe", "eu"]

# Zonas a descartar automáticamente (para evitar reubicación indeseada)
KEYWORDS_RECHAZADAS = ["barcelona presencial", "onsite london", "onsite berlin"]

def enviar_telegram(mensaje):
    """Envía un mensaje al bot de Telegram."""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("Faltan credenciales de Telegram.")
        return
    
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": mensaje,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Error enviando a Telegram: {e}")

def buscar_ofertas():
    """Lee los RSS, filtra por tus criterios y manda las alertas."""
    ayer = datetime.now(timezone.utc) - timedelta(days=1)
    ofertas_encontradas = []

    for url in RSS_URLS:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries:
                # Comprobar fecha (solo queremos ofertas de las últimas 24h)
                try:
                    fecha_pub = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
                    if fecha_pub < ayer:
                        continue
                except:
                    pass # Si no hay fecha clara, la evaluamos igual
                
                titulo = entry.title.lower()
                descripcion = entry.description.lower()
                texto_completo = titulo + " " + descripcion

                # 1. Filtro de descarte por ubicación estricta o palabras prohibidas
                rechazar = False
                for mala_kw in KEYWORDS_RECHAZADAS:
                    if mala_kw in texto_completo:
                        rechazar = True
                        break
                if rechazar:
                    continue

                # 2. Filtro de Geografía permitida
                geo_ok = any(geo in texto_completo for geo in GEOGRAFIA)
                
                # 3. Filtro de perfil técnico
                tech_ok = any(kw in texto_completo for kw in KEYWORDS_ACEPTADAS)

                if geo_ok and tech_ok:
                    ofertas_encontradas.append({
                        "titulo": entry.title,
                        "link": entry.link,
                        "empresa": getattr(entry, 'author', 'Empresa Oculta')
                    })
        except Exception as e:
            print(f"Error parseando {url}: {e}")

    return ofertas_encontradas

def main():
    ofertas = buscar_ofertas()
    
    if ofertas:
        # Agrupar mensajes para no hacer spam si hay muchas (mandar de 5 en 5 o un resumen)
        mensaje_final = f"🔥 <b>Nuevas Vacantes Healthtech/Data ({len(ofertas)} encontradas)</b>\n\n"
        for o in ofertas[:10]:  # Limitamos a top 10 diarias para no saturar
            mensaje_final += f"🏢 <b>{o['empresa']}</b>\n"
            mensaje_final += f"💼 {o['titulo']}\n"
            mensaje_final += f"🔗 <a href='{o['link']}'>Ver Oferta</a>\n\n"
        
        enviar_telegram(mensaje_final)
        print(f"Se han enviado {len(ofertas)} ofertas a Telegram.")
    else:
        print("No se han encontrado ofertas relevantes hoy.")
        # Opcional: enviar_telegram("🤖 Radar finalizado: Cero ofertas nuevas relevantes hoy.")

if __name__ == "__main__":
    main()
