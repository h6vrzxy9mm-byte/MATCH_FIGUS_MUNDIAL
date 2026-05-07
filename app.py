
import streamlit as st
import json
from pathlib import Path
import re
from math import radians, sin, cos, sqrt, atan2
from PIL import Image, ImageEnhance, ImageFilter, ImageOps
import pytesseract

try:
    from streamlit_js_eval import get_geolocation
except Exception:
    get_geolocation = None

DB = Path("database.json")

ADMIN_USER = "admin"
ADMIN_PASSWORD = "Regina2026"

PAISES = {
    "CAN": "🇨🇦 Canada",
    "BIH": "🇧🇦 Bosnia-Herzegovina",
    "QAT": "🇶🇦 Qatar",
    "SUI": "🇨🇭 Switzerland",
    "USA": "🇺🇸 USA",
    "PAR": "🇵🇾 Paraguay",
    "AUS": "🇦🇺 Australia",
    "TUR": "🇹🇷 Türkiye",
    "NED": "🇳🇱 Netherlands",
    "JPN": "🇯🇵 Japan",
    "SWE": "🇸🇪 Sweden",
    "TUN": "🇹🇳 Tunisia",
    "ESP": "🇪🇸 Spain",
    "CPV": "🇨🇻 Cabo Verde",
    "KSA": "🇸🇦 Saudi Arabia",
    "URU": "🇺🇾 Uruguay",
    "ARG": "🇦🇷 Argentina",
    "ALG": "🇩🇿 Algeria",
    "AUT": "🇦🇹 Austria",
    "JOR": "🇯🇴 Jordan",
    "ENG": "🏴 England",
    "CRO": "🇭🇷 Croatia",
    "GHA": "🇬🇭 Ghana",
    "PAN": "🇵🇦 Panama",
    "MEX": "🇲🇽 Mexico",
    "RSA": "🇿🇦 South Africa",
    "KOR": "🇰🇷 Korea Republic",
    "CZE": "🇨🇿 Czechia",
    "BRA": "🇧🇷 Brazil",
    "MAR": "🇲🇦 Morocco",
    "HAI": "🇭🇹 Haiti",
    "SCO": "🏴 Scotland",
    "GER": "🇩🇪 Germany",
    "CUW": "🇨🇼 Curaçao",
    "CIV": "🇨🇮 Côte d’Ivoire",
    "ECU": "🇪🇨 Ecuador",
    "BEL": "🇧🇪 Belgium",
    "EGY": "🇪🇬 Egypt",
    "IRN": "🇮🇷 IR Iran",
    "NZL": "🇳🇿 New Zealand",
    "FRA": "🇫🇷 France",
    "SEN": "🇸🇳 Senegal",
    "IRQ": "🇮🇶 Iraq",
    "NOR": "🇳🇴 Norway",
    "POR": "🇵🇹 Portugal",
    "COD": "🇨🇩 Congo DR",
    "UZB": "🇺🇿 Uzbekistan",
    "COL": "🇨🇴 Colombia"
}

NUMEROS = list(range(1, 21))

# Figuritas especiales del álbum
# FWC va de FWC00 a FWC19.
# Coca-Cola queda cargado como COC00 a COC19 para poder marcarla igual que las demás.
EXTRAS = {
    "FWC": {
        "nombre": "🏆 FIFA World Cup",
        "numeros": [f"{i:02d}" for i in range(0, 20)]
    },
    "COC": {
        "nombre": "🥤 Coca-Cola",
        "numeros": [f"{i:02d}" for i in range(0, 20)]
    }
}

def todas_las_figus():
    figus_paises = [f"{codigo}{num}" for codigo in PAISES.keys() for num in NUMEROS]
    figus_extras = [f"{codigo}{num}" for codigo, data in EXTRAS.items() for num in data["numeros"]]
    return figus_paises + figus_extras

def calcular_faltantes(album):
    return sorted(set(todas_las_figus()) - set(album))

def match_key(usuario1, usuario2, me_puede_dar, yo_puedo_dar):
    partes = [
        usuario1,
        usuario2,
        ",".join(sorted(me_puede_dar)),
        ",".join(sorted(yo_puedo_dar)),
    ]
    return "|".join(partes)

def obtener_matches_nuevos(db, user, matches):
    usuario_actual = db["users"].get(user, {})
    vistos = set(usuario_actual.get("seen_matches", []))
    nuevos = []

    for m in matches:
        clave = match_key(
            user,
            m["usuario"],
            m["me_puede_dar"],
            m["yo_puedo_dar"]
        )
        if clave not in vistos:
            nuevos.append((clave, m))

    return nuevos

def normalizar_usuario(nombre):
    return nombre.strip().lower()

def distancia_km(lat1, lon1, lat2, lon2):
    try:
        R = 6371
        dlat = radians(float(lat2) - float(lat1))
        dlon = radians(float(lon2) - float(lon1))
        a = sin(dlat / 2) ** 2 + cos(radians(float(lat1))) * cos(radians(float(lat2))) * sin(dlon / 2) ** 2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))
        return round(R * c, 1)
    except Exception:
        return None

def load_db():
    if DB.exists():
        db = json.loads(DB.read_text(encoding="utf-8"))
    else:
        db = {"users": {}, "messages": []}

    if "users" not in db:
        db["users"] = {}
    if "messages" not in db:
        db["messages"] = []

    for usuario, data in db.get("users", {}).items():
        if "display_name" not in data:
            data["display_name"] = usuario
        if "album" not in data:
            antiguas_faltantes = set(data.get("faltantes", []))
            data["album"] = sorted(set(todas_las_figus()) - antiguas_faltantes)
        if "repetidas" not in data:
            data["repetidas"] = []
        if "city" not in data:
            data["city"] = ""
        if "lat" not in data:
            data["lat"] = None
        if "lon" not in data:
            data["lon"] = None
        if "seen_matches" not in data:
            data["seen_matches"] = []
        data["faltantes"] = calcular_faltantes(data.get("album", []))

    return db

def save_db(db):
    for usuario, data in db.get("users", {}).items():
        data["album"] = sorted(set(data.get("album", [])))
        data["repetidas"] = sorted(set(data.get("repetidas", [])))
        data["faltantes"] = calcular_faltantes(data.get("album", []))
    DB.write_text(json.dumps(db, indent=2, ensure_ascii=False), encoding="utf-8")

def normalizar_texto(texto):
    texto = texto.upper()
    reemplazos = {
        " ": "", "-": "", "_": "", ".": "", ":": "", "|": "", "\n": "", "\t": "",
        "Á": "A", "É": "E", "Í": "I", "Ó": "O", "Ú": "U"
    }
    for a, b in reemplazos.items():
        texto = texto.replace(a, b)
    return texto

def detectar_figu(texto):
    limpio = normalizar_texto(texto)

    correcciones = {
        "ESPI4": "ESP14",
        "ESP1A": "ESP14",
        "ESPIA": "ESP14",
        "ESP|4": "ESP14",
        "ARGI": "ARG1",
        "BRAI": "BRA1",
        "MEXI": "MEX1",
        "USAI": "USA1",
        "CANI": "CAN1",
        "KORI": "KOR1",
        "JPNI": "JPN1",
    }

    for mal, bien in correcciones.items():
        if normalizar_texto(mal) in limpio:
            return bien

    for codigo in PAISES.keys():
        match = re.search(rf"{codigo}([0-9]{{1,2}})", limpio)
        if match:
            numero = int(match.group(1))
            if 1 <= numero <= 20:
                return f"{codigo}{numero}"

    variantes = limpio.replace("I", "1").replace("L", "1").replace("O", "0")
    for codigo in PAISES.keys():
        match = re.search(rf"{codigo}([0-9]{{1,2}})", variantes)
        if match:
            numero = int(match.group(1))
            if 1 <= numero <= 20:
                return f"{codigo}{numero}"

    for codigo in PAISES.keys():
        if codigo in limpio:
            numeros = re.findall(r"\d{1,2}", limpio)
            for n in numeros:
                numero = int(n)
                if 1 <= numero <= 20:
                    return f"{codigo}{numero}"

    return None

def preparar_zonas(img, crop_mode="normal"):
    ancho, alto = img.size
    recortes = [
        (0.48, 0.00, 1.00, 0.30),
        (0.55, 0.00, 1.00, 0.25),
        (0.45, 0.00, 1.00, 0.35),
    ]

    if crop_mode == "más arriba":
        recortes = [(0.45, 0.00, 1.00, 0.22), (0.50, 0.00, 1.00, 0.25)]
    elif crop_mode == "más amplio":
        recortes = [(0.35, 0.00, 1.00, 0.40), (0.40, 0.00, 1.00, 0.45)]

    zonas = []
    for l, t, r, b in recortes:
        zonas.append(img.crop((int(ancho*l), int(alto*t), int(ancho*r), int(alto*b))))

    return zonas

def mejorar_zona(zona):
    zona = ImageOps.exif_transpose(zona)
    zona = zona.resize((zona.width * 6, zona.height * 6))
    zona = zona.convert("L")
    zona = ImageEnhance.Contrast(zona).enhance(5)
    zona = ImageEnhance.Sharpness(zona).enhance(3)
    zona = zona.filter(ImageFilter.SHARPEN)
    return zona

def ocr_imagen(img, crop_mode="normal"):
    textos = []
    zonas_mejoradas = []

    try:
        img = ImageOps.exif_transpose(img)

        for zona in preparar_zonas(img, crop_mode):
            zona_m = mejorar_zona(zona)
            zonas_mejoradas.append(zona_m)

            for config in [
                "--psm 7 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
                "--psm 8 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
                "--psm 6 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
            ]:
                textos.append(pytesseract.image_to_string(zona_m, config=config))

        return "\n".join(textos), zonas_mejoradas

    except Exception:
        return "", zonas_mejoradas

def calcular_matches(db, user):
    current = db["users"][user]
    salida = []

    for other, data in db["users"].items():
        if other == user:
            continue

        yo_necesito = set(current.get("faltantes", calcular_faltantes(current.get("album", []))))
        yo_tengo = set(current.get("repetidas", []))

        el_necesita = set(data.get("faltantes", calcular_faltantes(data.get("album", []))))
        el_tiene = set(data.get("repetidas", []))

        me_puede_dar = sorted(yo_necesito.intersection(el_tiene))
        yo_puedo_dar = sorted(yo_tengo.intersection(el_necesita))

        if me_puede_dar and yo_puedo_dar:
            dist = None
            if current.get("lat") and current.get("lon") and data.get("lat") and data.get("lon"):
                dist = distancia_km(current["lat"], current["lon"], data["lat"], data["lon"])

            salida.append({
                "usuario": other,
                "nombre": data.get("display_name", other),
                "zona": data.get("city", "Sin cargar"),
                "distancia": dist,
                "me_puede_dar": me_puede_dar,
                "yo_puedo_dar": yo_puedo_dar
            })

    salida.sort(key=lambda x: x["distancia"] if x["distancia"] is not None else 999999)
    return salida

def estadisticas_admin(db):
    total_usuarios = len(db.get("users", {}))
    total_mensajes = len(db.get("messages", []))
    total_album = 0
    total_repetidas = 0
    ciudades = {}
    figuritas_repetidas = {}
    figuritas_faltantes = {}
    usuarios_detalle = []

    for username, data in db.get("users", {}).items():
        album = data.get("album", [])
        repetidas = data.get("repetidas", [])
        faltantes = calcular_faltantes(album)
        ciudad = data.get("city", "Sin ciudad") or "Sin ciudad"

        total_album += len(album)
        total_repetidas += len(repetidas)
        ciudades[ciudad] = ciudades.get(ciudad, 0) + 1

        for f in repetidas:
            figuritas_repetidas[f] = figuritas_repetidas.get(f, 0) + 1

        for f in faltantes:
            figuritas_faltantes[f] = figuritas_faltantes.get(f, 0) + 1

        usuarios_detalle.append({
            "usuario": data.get("display_name", username),
            "zona": ciudad,
            "album": len(album),
            "faltantes": len(faltantes),
            "repetidas": len(repetidas),
            "matches": len(calcular_matches(db, username))
        })

    return {
        "total_usuarios": total_usuarios,
        "total_mensajes": total_mensajes,
        "total_album": total_album,
        "total_repetidas": total_repetidas,
        "ciudades": ciudades,
        "figuritas_repetidas": figuritas_repetidas,
        "figuritas_faltantes": figuritas_faltantes,
        "usuarios_detalle": usuarios_detalle
    }

def mobile_css():
    st.markdown("""
    <style>
    .stApp { background: linear-gradient(180deg, #f6f7fb 0%, #ffffff 100%); }
    section[data-testid="stSidebar"] { display: none; }
    .block-container { max-width: 560px; padding-top: 1rem; padding-left: .8rem; padding-right: .8rem; }

    /* OCULTAR BRANDING STREAMLIT */
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}

    [data-testid="stToolbar"] {
        display: none !important;
    }

    [data-testid="stDecoration"] {
        display: none !important;
    }

    [data-testid="stStatusWidget"] {
        display: none !important;
    }

    .stDeployButton {
        display: none !important;
    }

    iframe {
        display: none !important;
    }
    .hero {
        background: linear-gradient(135deg, #1d5cff, #00b894);
        color: white; border-radius: 26px; padding: 22px; margin-bottom: 16px;
        box-shadow: 0 12px 30px rgba(29,92,255,.25);
    }
    .hero h1 { color: white; font-size: 30px; margin-bottom: 4px; }
    .app-card {
        background: white; border-radius: 22px; padding: 18px; margin-bottom: 14px;
        box-shadow: 0 8px 24px rgba(0,0,0,.08); border: 1px solid rgba(0,0,0,.04);
    }
    .match-card {
        background: white; border-radius: 20px; padding: 16px; margin-bottom: 12px;
        border-left: 6px solid #00b894; box-shadow: 0 6px 18px rgba(0,0,0,.08);
    }
    .admin-card {
        background: #111827; color: white; border-radius: 22px; padding: 18px; margin-bottom: 14px;
        box-shadow: 0 8px 24px rgba(0,0,0,.12);
    }
    .stButton>button { border-radius: 999px; min-height: 42px; font-weight: 700; }
    </style>
    """, unsafe_allow_html=True)

mobile_css()

db = load_db()

st.markdown("""
<div class="hero">
<h1>⚽ Match Figus</h1>
<div>Intercambiá figuritas cerca tuyo</div>
</div>
""", unsafe_allow_html=True)

if "user" not in st.session_state:
    st.session_state.user = None
if "is_admin" not in st.session_state:
    st.session_state.is_admin = False

if not st.session_state.user and not st.session_state.is_admin:
    st.markdown('<div class="app-card">', unsafe_allow_html=True)
    st.subheader("Ingresar")

    modo_login = st.radio(
        "Qué querés hacer",
        ["Entrar con usuario existente", "Crear usuario nuevo", "Entrar como administrador"]
    )

    if modo_login == "Entrar como administrador":
        admin_user = st.text_input("Usuario admin")
        admin_pass = st.text_input("Clave admin", type="password")

        if st.button("Entrar al panel admin"):
            if admin_user == ADMIN_USER and admin_pass == ADMIN_PASSWORD:
                st.session_state.is_admin = True
                st.session_state.user = "__admin__"
                st.rerun()
            else:
                st.error("Usuario o clave incorrectos.")

    else:
        username = st.text_input("Nombre de usuario único", help="Ejemplo: lisi_2026, fran_rio3, juli_figus")
        ciudad = st.text_input("Ciudad / barrio")

        if modo_login == "Crear usuario nuevo":
            if st.button("Crear usuario"):
                username_key = normalizar_usuario(username)

                if not username_key:
                    st.error("Escribí un nombre de usuario.")
                elif username_key in db["users"]:
                    st.error("Ese nombre de usuario ya existe. Elegí otro.")
                elif username_key == ADMIN_USER:
                    st.error("Ese nombre está reservado para administración.")
                else:
                    db["users"][username_key] = {
                        "display_name": username.strip(),
                        "city": ciudad.strip(),
                        "album": [],
                        "repetidas": [],
                        "faltantes": todas_las_figus(),
                        "lat": None,
                        "lon": None,
                        "seen_matches": []
                    }
                    save_db(db)
                    st.session_state.user = username_key
                    st.rerun()

        else:
            if st.button("Entrar"):
                username_key = normalizar_usuario(username)

                if username_key in db["users"]:
                    st.session_state.user = username_key
                    st.rerun()
                else:
                    st.error("Ese usuario no existe. Primero crealo como usuario nuevo.")

    st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

if st.session_state.is_admin:
    st.markdown('<div class="admin-card"><h2>📊 Panel Administrador</h2><p>Resumen general de la app</p></div>', unsafe_allow_html=True)

    stats = estadisticas_admin(db)

    tab_a, tab_b, tab_c, tab_d = st.tabs(["Resumen", "Usuarios", "Figuritas", "Mensajes"])

    with tab_a:
        col1, col2 = st.columns(2)
        col1.metric("👥 Usuarios", stats["total_usuarios"])
        col2.metric("💬 Mensajes", stats["total_mensajes"])

        col3, col4 = st.columns(2)
        col3.metric("📒 Figuritas cargadas", stats["total_album"])
        col4.metric("✅ Repetidas cargadas", stats["total_repetidas"])

        st.subheader("🌎 Usuarios por ciudad")
        if stats["ciudades"]:
            for ciudad, cantidad in sorted(stats["ciudades"].items(), key=lambda x: x[1], reverse=True):
                st.write(f"**{ciudad}:** {cantidad}")
        else:
            st.info("Todavía no hay usuarios.")

    with tab_b:
        st.subheader("👤 Usuarios registrados")

        if not stats["usuarios_detalle"]:
            st.info("Todavía no hay usuarios.")
        else:
            for u in sorted(stats["usuarios_detalle"], key=lambda x: x["album"], reverse=True):
                with st.container(border=True):
                    st.write(f"**Usuario:** {u['usuario']}")
                    st.write(f"📍 Zona: {u['zona']}")
                    st.write(f"📒 Álbum: {u['album']}")
                    st.write(f"❌ Faltantes: {u['faltantes']}")
                    st.write(f"✅ Repetidas: {u['repetidas']}")
                    st.write(f"🤝 Matches posibles: {u['matches']}")

    with tab_c:
        st.subheader("🔥 Figuritas más repetidas")
        repetidas_top = sorted(stats["figuritas_repetidas"].items(), key=lambda x: x[1], reverse=True)[:20]

        if repetidas_top:
            for figu, cantidad in repetidas_top:
                st.write(f"**{figu}:** {cantidad}")
        else:
            st.info("Todavía no hay repetidas cargadas.")

        st.subheader("🧩 Figuritas más faltantes")
        faltantes_top = sorted(stats["figuritas_faltantes"].items(), key=lambda x: x[1], reverse=True)[:20]

        if faltantes_top:
            for figu, cantidad in faltantes_top:
                st.write(f"**{figu}:** {cantidad}")
        else:
            st.info("No hay datos de faltantes.")

    with tab_d:
        st.subheader("💬 Mensajes enviados")

        mensajes = db.get("messages", [])

        if not mensajes:
            st.info("Todavía no hay mensajes.")
        else:
            for m in reversed(mensajes[-50:]):
                remitente = db["users"].get(m.get("from"), {}).get("display_name", m.get("from"))
                destinatario = db["users"].get(m.get("to"), {}).get("display_name", m.get("to"))

                with st.container(border=True):
                    st.write(f"**De:** {remitente}")
                    st.write(f"**Para:** {destinatario}")
                    st.write(m.get("msg", ""))

    if st.button("Cerrar panel admin"):
        st.session_state.is_admin = False
        st.session_state.user = None
        st.rerun()

    st.stop()

user = st.session_state.user
db = load_db()

if user not in db["users"]:
    st.session_state.user = None
    st.rerun()

usuario = db["users"][user]
matches_actuales = calcular_matches(db, user)

st.caption(f"Conectado como: {usuario.get('display_name', user)}")

tab1, tab2, tab3, tab4, tab5 = st.tabs(["Inicio", "Álbum", "Escanear", "Matches", "Mensajes"])

with tab1:
    st.markdown('<div class="app-card">', unsafe_allow_html=True)
    st.subheader("📍 Ubicación")

    if get_geolocation:
        geo = get_geolocation()
        if geo and "coords" in geo:
            db["users"][user]["lat"] = geo["coords"]["latitude"]
            db["users"][user]["lon"] = geo["coords"]["longitude"]
            save_db(db)
            st.success("Ubicación guardada.")
        else:
            st.info("Cuando el navegador pregunte, tocá Permitir ubicación.")
    else:
        st.warning("La geolocalización no está disponible. Revisá requirements.txt.")

    ciudad_actual = usuario.get("city", "")
    nueva_ciudad = st.text_input("Ciudad / barrio", value=ciudad_actual)
    if st.button("Guardar zona"):
        db["users"][user]["city"] = nueva_ciudad.strip()
        save_db(db)
        st.success("Zona guardada.")
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="app-card">', unsafe_allow_html=True)
    st.subheader("Resumen")

    matches_preview = calcular_matches(db, user)
    nuevos_preview = obtener_matches_nuevos(db, user, matches_preview)

    if nuevos_preview:
        st.success(f"🔔 Tenés {len(nuevos_preview)} match(es) nuevos. Entrá a la pestaña 🤝 Matches para verlos.")

    album = usuario.get("album", [])
    repetidas = usuario.get("repetidas", [])
    faltantes = calcular_faltantes(album)
    st.write(f"📒 Tenés en álbum: {len(album)}")
    st.write(f"❌ Faltantes: {len(faltantes)}")
    st.write(f"✅ Repetidas: {len(repetidas)}")
    st.write(f"🤝 Matches: {len(matches_actuales)}")
    st.markdown('</div>', unsafe_allow_html=True)

    if st.button("Cerrar sesión"):
        st.session_state.user = None
        st.rerun()

with tab2:
    st.subheader("📒 Mi álbum")
    st.info("Marcá las que ya tenés y las repetidas. Las faltantes se calculan solas.")

    album_guardado = set(usuario.get("album", []))
    repetidas_guardadas = set(usuario.get("repetidas", []))
    nuevo_album = set()
    nuevas_repetidas = set()

    st.subheader("📒 Figuritas que tengo")

    for codigo, nombre_pais in PAISES.items():
        with st.expander(f"{nombre_pais} — {codigo}"):
            cols_album = st.columns(5)
            for i, num in enumerate(NUMEROS):
                figu = f"{codigo}{num}"
                with cols_album[i % 5]:
                    if st.checkbox(figu, value=figu in album_guardado, key=f"album_{figu}"):
                        nuevo_album.add(figu)

    st.subheader("⭐ Especiales que tengo")

    for codigo, data in EXTRAS.items():
        with st.expander(f"{data['nombre']} — {codigo}"):
            cols_album = st.columns(5)
            for i, num in enumerate(data["numeros"]):
                figu = f"{codigo}{num}"
                with cols_album[i % 5]:
                    if st.checkbox(figu, value=figu in album_guardado, key=f"album_{figu}"):
                        nuevo_album.add(figu)

    st.subheader("✅ Figuritas repetidas")

    for codigo, nombre_pais in PAISES.items():
        with st.expander(f"{nombre_pais} — {codigo}"):
            cols_rep = st.columns(5)
            for i, num in enumerate(NUMEROS):
                figu = f"{codigo}{num}"
                with cols_rep[i % 5]:
                    if st.checkbox(figu, value=figu in repetidas_guardadas, key=f"rep_{figu}"):
                        nuevas_repetidas.add(figu)

    st.subheader("🥤⭐ Especiales repetidas")

    for codigo, data in EXTRAS.items():
        with st.expander(f"{data['nombre']} — {codigo}"):
            cols_rep = st.columns(5)
            for i, num in enumerate(data["numeros"]):
                figu = f"{codigo}{num}"
                with cols_rep[i % 5]:
                    if st.checkbox(figu, value=figu in repetidas_guardadas, key=f"rep_{figu}"):
                        nuevas_repetidas.add(figu)

    album_final = set(nuevo_album).union(nuevas_repetidas)
    faltantes = calcular_faltantes(album_final)

    st.write(f"📒 Tenés: {len(album_final)} de {len(todas_las_figus())}")
    st.write(f"❌ Faltan: {len(faltantes)}")
    st.write(f"✅ Repetidas: {len(nuevas_repetidas)}")

    with st.expander("Ver faltantes"):
        st.write(", ".join(faltantes) if faltantes else "¡Álbum completo!")

    if st.button("💾 Guardar álbum"):
        db["users"][user]["album"] = sorted(album_final)
        db["users"][user]["repetidas"] = sorted(nuevas_repetidas)
        db["users"][user]["faltantes"] = calcular_faltantes(album_final)
        save_db(db)
        st.success("Guardado correctamente.")

with tab3:
    st.subheader("📷 Escanear figuritas")
    st.info("Si no reconoce, probá cambiar el recorte. Igual siempre podés cargar manualmente abajo.")

    crop_mode = st.selectbox("Recorte para lectura", ["normal", "más arriba", "más amplio"])
    modo = st.radio("Modo", ["Subir varias fotos", "Usar cámara"])

    imagenes = []
    if modo == "Subir varias fotos":
        archivos = st.file_uploader("Subí fotos", type=["jpg", "jpeg", "png"], accept_multiple_files=True)
        if archivos:
            for archivo in archivos:
                imagenes.append((archivo.name, Image.open(archivo)))
    else:
        foto = st.camera_input("Sacá foto de una figurita")
        if foto:
            imagenes.append(("foto_camara", Image.open(foto)))

    detectadas = []

    if imagenes and st.button("🔎 Detectar todas"):
        for nombre, img in imagenes:
            texto, zonas = ocr_imagen(img, crop_mode)
            figu = detectar_figu(texto)

            st.markdown('<div class="app-card">', unsafe_allow_html=True)
            st.write(f"Imagen: {nombre}")
            st.image(img, width=220)

            for idx, zona in enumerate(zonas[:2]):
                st.image(zona, caption=f"Zona leída {idx+1}", width=220)

            st.code(texto if texto else "No se pudo leer texto")

            if figu:
                st.success(f"Detectada: {figu}")
                detectadas.append(figu)
            else:
                st.warning("No detectada. Cargala manualmente abajo.")
            st.markdown('</div>', unsafe_allow_html=True)

        st.session_state.detectadas = sorted(set(detectadas))

    detectadas_guardadas = st.session_state.get("detectadas", [])

    if detectadas_guardadas:
        st.subheader("Guardar detectadas")
        st.write(", ".join(detectadas_guardadas))
        destino = st.radio("Guardar detectadas como", ["Ya la tengo en el álbum", "Repetidas para cambiar"])
        if st.button("➕ Agregar detectadas"):
            db = load_db()
            for figu in detectadas_guardadas:
                if figu not in db["users"][user]["album"]:
                    db["users"][user]["album"].append(figu)
                if destino == "Repetidas para cambiar" and figu not in db["users"][user]["repetidas"]:
                    db["users"][user]["repetidas"].append(figu)
            save_db(db)
            st.success("Figuritas agregadas.")

    st.subheader("Carga manual rápida")
    opciones_manual = list(PAISES.keys()) + list(EXTRAS.keys())
    col_a, col_b = st.columns(2)
    with col_a:
        pais_manual = st.selectbox("País / especial", opciones_manual)
    with col_b:
        if pais_manual in EXTRAS:
            numero_manual = st.selectbox("Número", EXTRAS[pais_manual]["numeros"])
        else:
            numero_manual = st.selectbox("Número", NUMEROS)

    destino_manual = st.radio("Guardar manual como", ["Ya la tengo en el álbum", "Repetida para cambiar"], key="destino_manual")

    if st.button("Agregar manual"):
        figu = f"{pais_manual}{numero_manual}"
        db = load_db()

        if figu not in db["users"][user]["album"]:
            db["users"][user]["album"].append(figu)

        if destino_manual == "Repetida para cambiar" and figu not in db["users"][user]["repetidas"]:
            db["users"][user]["repetidas"].append(figu)

        save_db(db)
        st.success(f"{figu} agregada.")

with tab4:
    st.subheader("🤝 Matches")
    matches = calcular_matches(db, user)
    nuevos = obtener_matches_nuevos(db, user, matches)
    claves_nuevas = {clave for clave, _ in nuevos}

    if nuevos:
        st.success(f"🔔 Tenés {len(nuevos)} match(es) nuevos!")

        if st.button("Marcar matches como vistos"):
            vistos = set(db["users"][user].get("seen_matches", []))
            vistos.update(claves_nuevas)
            db["users"][user]["seen_matches"] = sorted(vistos)
            save_db(db)
            st.success("Matches marcados como vistos.")
            st.rerun()

    if not matches:
        st.warning("Todavía no hay matches.")
    else:
        for m in matches:
            clave = match_key(
                user,
                m["usuario"],
                m["me_puede_dar"],
                m["yo_puedo_dar"]
            )

            etiqueta_nuevo = "🆕 NUEVO — " if clave in claves_nuevas else ""
            dist_txt = f" — a {m['distancia']} km" if m["distancia"] is not None else ""

            st.markdown(f"""
            <div class="match-card">
            <h3>{etiqueta_nuevo}✅ {m['nombre']}</h3>
            <p>📍 {m['zona']}{dist_txt}</p>
            <p><b>Te puede dar:</b> {", ".join(m['me_puede_dar'])}</p>
            <p><b>Vos le podés dar:</b> {", ".join(m['yo_puedo_dar'])}</p>
            </div>
            """, unsafe_allow_html=True)

            mensaje = st.text_input(
                f"Mensaje para {m['nombre']}",
                value=f"Hola {m['nombre']}, hacemos intercambio?",
                key=f"msg_{m['usuario']}"
            )

            if st.button(f"Enviar a {m['nombre']}", key=f"send_{m['usuario']}"):
                db["messages"].append({"from": user, "to": m["usuario"], "msg": mensaje})
                save_db(db)
                st.success("Mensaje enviado.")

with tab5:
    st.subheader("📩 Mensajes")
    mensajes = [m for m in db["messages"] if m["to"] == user]

    if not mensajes:
        st.info("Todavía no recibiste mensajes.")

    for m in mensajes:
        nombre_remitente = db["users"].get(m["from"], {}).get("display_name", m["from"])
        st.markdown('<div class="app-card">', unsafe_allow_html=True)
        st.write(f"📨 De: {nombre_remitente}")
        st.write(m["msg"])
        st.markdown('</div>', unsafe_allow_html=True)
