import streamlit as str_app
import pandas as pdimport streamlit as str_app
import pandas as pd
import psycopg2
from psycopg2 import pool as pg_pool
import os
import time
from datetime import datetime, date
from functools import wraps
from contextlib import contextmanager
import io
import base64
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

# =========================================================================
# CONFIGURACIÓN DE PÁGINA
# =========================================================================
str_app.set_page_config(
    page_title="Avícola Santa Isabel",
    page_icon="🥚",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# --- ICONO PERSONALIZADO (FAVICON) ---
if os.path.exists("LOGOASI.png"):
    with open("LOGOASI.png", "rb") as f:
        b64_svg = base64.b64encode(f.read()).decode('utf-8')
    data_uri = f"data:image/png;base64,{b64_svg}"
else:
    svg_huevo = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><rect width="100" height="100" rx="20" fill="#0f2942"/><text x="50" y="68" font-size="65" text-anchor="middle">🥚</text></svg>"""
    b64_svg = base64.b64encode(svg_huevo.encode('utf-8')).decode('utf-8')
    data_uri = f"data:image/svg+xml;base64,{b64_svg}"

str_app.markdown(f"""
    <script>
        var doc = window.parent.document;
        var oldIcons = doc.querySelectorAll("link[rel*='icon'], link[rel*='apple']");
        oldIcons.forEach(function(el) {{ el.remove(); }});
        var appleIcon = doc.createElement('link');
        appleIcon.rel = 'apple-touch-icon';
        appleIcon.href = '{data_uri}';
        doc.head.appendChild(appleIcon);
        var icon = doc.createElement('link');
        icon.rel = 'icon';
        icon.type = 'image/x-icon';
        icon.href = '{data_uri}';
        doc.head.appendChild(icon);
    </script>
""", unsafe_allow_html=True)

# --- ESTILOS CSS ---
str_app.markdown(
    """
    <style>
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}

    .stApp { background-color: #c8d6e5 !important; }

    .block-container {
        padding-top: 1.5rem; padding-bottom: 5rem;
        padding-left: 1.2rem; padding-right: 1.2rem;
        max-width: 540px;
        background-color: #0f2942 !important;
        border-radius: 16px;
        box-shadow: 0 10px 35px rgba(15, 41, 66, 0.3);
        margin-top: 1rem; margin-bottom: 2rem;
        border: 1px solid #1a3e63;
    }

    /* Botones principales y de envío */
    .stButton>button, div.stFormSubmitButton>button {
        width: 100% !important; border-radius: 10px !important; height: 3.2em !important;
        font-weight: 650 !important; background-color: #f26822 !important;
        color: white !important; border: 2px solid #ffffff !important;
    }

    .stButton>button p, .stButton>button span, div.stFormSubmitButton>button p, div.stFormSubmitButton>button span {
        color: white !important;
    }

    .stButton>button:hover, div.stFormSubmitButton>button:hover {
        background-color: #ffffff !important;
        border-color: #f26822 !important;
    }

    .stButton>button:hover p, .stButton>button:hover span, div.stFormSubmitButton>button:hover p, div.stFormSubmitButton>button:hover span {
        color: #f26822 !important;
    }

    /* Textos generales del contenedor */
    .block-container h1, .block-container h2, .block-container h3, .block-container h4, .block-container p {
        color: #ffffff;
    }

    /* Estilo armónico para los Expander (Historial / Remisiones) */
    [data-testid="stExpander"] {
        background-color: #163559 !important;
        border-radius: 8px !important;
        border: 1px solid #244c7c !important;
    }

    [data-testid="stExpander"] summary p, [data-testid="stExpander"] summary span {
        color: #ffffff !important;
        font-weight: bold !important;
    }

    [data-testid="stExpanderDetails"] {
        color: #ffffff !important;
    }

    /* Etiquetas de los campos */
    .stTextInput label, .stNumberInput label, .stSelectbox label, .stDateInput label, .stFileUploader label {
        color: #ffffff !important;
    }

    [data-testid="stMetric"] {
        background-color: #163559 !important;
        border-radius: 8px !important;
        border: 1px solid #244c7c !important;
        padding: 10px !important;
    }
    [data-testid="stMetricLabel"] p { color: #cbd5e1 !important; }
    [data-testid="stMetricValue"] { color: #ffffff !important; }

    .stSubheader { color: #f26822 !important; font-weight: bold !important; }
    </style>
    """,
    unsafe_allow_html=True
)

# =========================================================================
# CONSTANTES DE NEGOCIO
# (Centralizadas aquí: si mañana abren un Galpón 4, solo se edita esta lista)
# =========================================================================
GALPONES = ["Galpón 1", "Galpón 2", "Galpón 3"]
GALPONES_GASTOS = GALPONES + ["General / Granja"]
CLASIFICACIONES = ["yumbo", "extra", "aa", "a", "b", "c", "sucio", "roto"]
COLUMNAS_INVENTARIO = set(CLASIFICACIONES)
MESES_NOMBRES = {1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril', 5: 'Mayo', 6: 'Junio',
                  7: 'Julio', 8: 'Agosto', 9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'}
CATEGORIAS_GASTO_GALPON = ["Alimento", "Medicamentos / Sanidad", "Personal / Mano de Obra",
                            "Mantenimiento / Reparaciones", "Servicios Públicos", "Otros"]
CATEGORIAS_GASTO_VARIO = ["Personal", "Hogar", "Vehículo", "Impuestos", "Varios"]

NOMBRE_EMPRESA = "AGROAVICOLA SANTA ISABEL"
NIT_EMPRESA = "NIT. 901.786.799-7"
TELEFONOS_EMPRESA = "Cel. 3102397244 - 3125588606"


# =========================================================================
# CAPA DE BASE DE DATOS
# Se usa un pool de conexiones (en vez de abrir/cerrar una conexión nueva
# en cada consulta) y decoradores que atrapan errores de PostgreSQL para
# que nunca se vea un traceback crudo en pantalla.
# =========================================================================
@str_app.cache_resource(show_spinner=False)
def _obtener_pool():
    return pg_pool.SimpleConnectionPool(1, 10, str_app.secrets["postgres"]["url"])


@contextmanager
def get_conn():
    """Presta una conexión del pool y siempre la devuelve al terminar."""
    conexiones = _obtener_pool()
    conn = conexiones.getconn()
    try:
        yield conn
    finally:
        conexiones.putconn(conn)


def ejecutar(sql, params=None):
    """Ejecuta una sentencia de escritura (INSERT/UPDATE/DELETE/DDL) como una
    transacción atómica: si algo falla, se revierte todo automáticamente."""
    with get_conn() as conn:
        with conn:
            with conn.cursor() as cur:
                cur.execute(sql, params or ())


def consultar_uno(sql, params=None):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params or ())
            return cur.fetchone()


def leer_df(sql, params=None):
    with get_conn() as conn:
        return pd.read_sql_query(sql, conn, params=params)


def operacion_segura(func):
    """Decorador para funciones que ESCRIBEN en la base de datos.
    Atrapa errores de PostgreSQL y los muestra de forma amigable en vez de
    tumbar la app. Las validaciones de negocio (ValueError) se dejan pasar
    para que la pantalla que llamó pueda mostrar su propio mensaje."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            resultado = func(*args, **kwargs)
            return True if resultado is None else resultado
        except ValueError:
            raise
        except psycopg2.Error as e:
            str_app.error(f"⚠️ No se pudo guardar la información en la base de datos.\n\nDetalle: {e}")
            return False
    return wrapper


def lectura_segura(func):
    """Decorador para funciones que LEEN de la base de datos. Si la consulta
    falla, se devuelve una tabla vacía en vez de romper la página."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except psycopg2.Error as e:
            str_app.error(f"⚠️ No se pudieron cargar los datos.\n\nDetalle: {e}")
            return pd.DataFrame()
    return wrapper


# --- CREACIÓN DE TABLAS (se ejecuta una sola vez por sesión, no en cada clic) ---
def inicializar_todas_las_tablas():
    ejecutar("""
        CREATE TABLE IF NOT EXISTS clientes (
            id SERIAL PRIMARY KEY,
            nombre TEXT UNIQUE NOT NULL,
            cedula_nit TEXT,
            direccion TEXT,
            telefono TEXT,
            email TEXT
        );
    """)
    ejecutar("""
        CREATE TABLE IF NOT EXISTS inventario (
            galpon TEXT PRIMARY KEY,
            yumbo INT DEFAULT 0, extra INT DEFAULT 0, aa INT DEFAULT 0, a INT DEFAULT 0,
            b INT DEFAULT 0, c INT DEFAULT 0, sucio INT DEFAULT 0, roto INT DEFAULT 0
        );
    """)
    for g in GALPONES:
        ejecutar("INSERT INTO inventario (galpon) VALUES (%s) ON CONFLICT (galpon) DO NOTHING;", (g,))
    ejecutar("""
        CREATE TABLE IF NOT EXISTS remisiones (
            id SERIAL PRIMARY KEY,
            num_remision INT, fecha_emision DATE, cliente TEXT, cedula_nit TEXT,
            telefono TEXT, destino TEXT, email TEXT, conductor TEXT, tipo_huevo TEXT,
            cantidad INT, precio_unitario NUMERIC, total NUMERIC, galpon TEXT
        );
    """)
    ejecutar("""
        CREATE TABLE IF NOT EXISTS cartera (
            num_remision INT PRIMARY KEY, cliente TEXT, total NUMERIC, saldo NUMERIC,
            estado TEXT DEFAULT 'PENDIENTE'
        );
    """)
    ejecutar("""
        CREATE TABLE IF NOT EXISTS abonos_cartera (
            id SERIAL PRIMARY KEY, num_remision INT, fecha_abono TIMESTAMP, monto NUMERIC,
            comprobante BYTEA, nombre_comprobante TEXT
        );
    """)
    ejecutar("""
        CREATE TABLE IF NOT EXISTS gastos (
            id SERIAL PRIMARY KEY, fecha DATE, galpon TEXT, categoria TEXT,
            descripcion TEXT, valor NUMERIC
        );
    """)
    ejecutar("""
        CREATE TABLE IF NOT EXISTS gastos_varios (
            id SERIAL PRIMARY KEY, fecha DATE, categoria TEXT, descripcion TEXT, valor NUMERIC
        );
    """)
    ejecutar("""
        CREATE TABLE IF NOT EXISTS galpon_config (
            galpon TEXT PRIMARY KEY, edad_semanas INT DEFAULT 0, edad_dias INT DEFAULT 0,
            aves_iniciales INT DEFAULT 0
        );
    """)
    ejecutar("""
        CREATE TABLE IF NOT EXISTS registros_diarios (
            id SERIAL PRIMARY KEY, fecha DATE, galpon TEXT, mortalidad INT DEFAULT 0,
            concentrado_ingresado NUMERIC DEFAULT 0, concentrado_consumido NUMERIC DEFAULT 0,
            huevos_recolectados INT DEFAULT 0, observaciones TEXT
        );
    """)
    ejecutar("""
        CREATE TABLE IF NOT EXISTS historial_entradas (
            id SERIAL PRIMARY KEY, fecha DATE, galpon TEXT, clasificacion TEXT, cantidad INT
        );
    """)


def asegurar_tablas():
    """Solo corre las sentencias CREATE TABLE una vez por sesión de usuario,
    en vez de en cada clic como hacía la versión anterior."""
    if not str_app.session_state.get("_tablas_listas", False):
        inicializar_todas_las_tablas()
        str_app.session_state["_tablas_listas"] = True


# --- CLIENTES ---
@operacion_segura
def guardar_cliente(nombre, cedula, direccion, telefono, email):
    ejecutar("""
        INSERT INTO clientes (nombre, cedula_nit, direccion, telefono, email)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (nombre) DO UPDATE SET
            cedula_nit = EXCLUDED.cedula_nit, direccion = EXCLUDED.direccion,
            telefono = EXCLUDED.telefono, email = EXCLUDED.email;
    """, (nombre.strip().upper(), cedula, direccion, telefono, email))


@operacion_segura
def eliminar_cliente(cliente_id):
    ejecutar("DELETE FROM clientes WHERE id = %s", (cliente_id,))


@lectura_segura
def cargar_clientes():
    return leer_df("SELECT * FROM clientes ORDER BY nombre ASC")


# --- INVENTARIO ---
@lectura_segura
def cargar_inventario():
    df = leer_df("SELECT * FROM inventario ORDER BY galpon")
    return df.set_index('galpon')


@operacion_segura
def registrar_entrada_inventario(galpon, items_entrada, fecha_entrada):
    with get_conn() as conn:
        with conn:
            with conn.cursor() as cur:
                for item in items_entrada:
                    clasificacion = item['Clasificación'].lower()
                    if clasificacion not in COLUMNAS_INVENTARIO:
                        raise ValueError(f"Clasificación inválida: {clasificacion}")
                    cantidad = int(item['Cantidad'])
                    cur.execute(f"UPDATE inventario SET {clasificacion} = {clasificacion} + %s WHERE galpon = %s", (cantidad, galpon))
                    cur.execute(
                        "INSERT INTO historial_entradas (fecha, galpon, clasificacion, cantidad) VALUES (%s, %s, %s, %s)",
                        (fecha_entrada, galpon, clasificacion, cantidad)
                    )


@lectura_segura
def cargar_historial_entradas(galpon=None):
    if galpon:
        df = leer_df("SELECT * FROM historial_entradas WHERE galpon = %s ORDER BY fecha DESC, id DESC", (galpon,))
    else:
        df = leer_df("SELECT * FROM historial_entradas ORDER BY fecha DESC, id DESC")
    if not df.empty:
        df['fecha'] = pd.to_datetime(df['fecha']).dt.date
    return df


@operacion_segura
def actualizar_inventario_fisico(galpon, nuevo_stock_dict):
    ejecutar("""
        UPDATE inventario SET
            yumbo = %s, extra = %s, aa = %s, a = %s, b = %s, c = %s, sucio = %s, roto = %s
        WHERE galpon = %s
    """, (
        nuevo_stock_dict.get('yumbo', 0), nuevo_stock_dict.get('extra', 0), nuevo_stock_dict.get('aa', 0),
        nuevo_stock_dict.get('a', 0), nuevo_stock_dict.get('b', 0), nuevo_stock_dict.get('c', 0),
        nuevo_stock_dict.get('sucio', 0), nuevo_stock_dict.get('roto', 0), galpon
    ))


# --- REMISIONES / VENTAS ---
@lectura_segura
def cargar_remisiones():
    df = leer_df("SELECT * FROM remisiones ORDER BY id DESC")
    if not df.empty:
        if 'num_remision' not in df.columns:
            df['num_remision'] = df['id']
        if 'fecha_emision' in df.columns:
            df['fecha_emision'] = pd.to_datetime(df['fecha_emision']).dt.date
    return df


def obtener_siguiente_num_remision():
    try:
        res = consultar_uno("SELECT MAX(num_remision) FROM remisiones;")
        if res and res[0] is not None:
            return max(int(res[0]) + 1, 192)
    except psycopg2.Error:
        pass
    return 192


@operacion_segura
def registrar_venta_multiple(cliente, cedula, direccion, telefono, email, conductor, num_remision, fecha_remision, items_venta):
    # Se acumula lo pedido por (galpón, clasificación) ANTES de validar contra el
    # stock real, para no dejar pasar una remisión con dos filas del mismo huevo
    # que individualmente caben pero juntas superan el stock disponible.
    requerido = {}
    for item in items_venta:
        clasificacion = item['Clasificación'].lower()
        if clasificacion not in COLUMNAS_INVENTARIO:
            raise ValueError(f"Clasificación inválida: {clasificacion}")
        galp_origen = item.get('Galpón', GALPONES[0])
        clave = (galp_origen, clasificacion)
        requerido[clave] = requerido.get(clave, 0) + int(item['Cantidad (Huevos)'])

    with get_conn() as conn:
        with conn:
            with conn.cursor() as cur:
                for (galp_origen, clasificacion), cantidad_total in requerido.items():
                    cur.execute(f"SELECT {clasificacion} FROM inventario WHERE galpon = %s", (galp_origen,))
                    res = cur.fetchone()
                    stock_actual = res[0] if res else 0
                    if cantidad_total > stock_actual:
                        raise ValueError(
                            f"Stock insuficiente de '{clasificacion.upper()}' en {galp_origen}. "
                            f"Stock actual: {stock_actual:,}, solicitado: {cantidad_total:,}".replace(",", ".")
                        )

                cur.execute("""
                    SELECT column_name, is_generated, identity_generation
                    FROM information_schema.columns WHERE table_name = 'remisiones';
                """)
                columnas_validas = {c for c, is_gen, id_gen in cur.fetchall() if is_gen != 'ALWAYS' and id_gen != 'ALWAYS'}

                total_venta_acumulado = 0.0
                for item in items_venta:
                    clasificacion = item['Clasificación'].lower()
                    cantidad = int(item['Cantidad (Huevos)'])
                    subtotal = float(item['Subtotal ($)'])
                    precio_u = float(item['Precio Unitario ($)'])
                    galp_origen = item.get('Galpón', GALPONES[0])
                    total_venta_acumulado += subtotal

                    datos_insert = {
                        "num_remision": num_remision, "fecha_emision": fecha_remision,
                        "cliente": cliente, "cedula_nit": cedula, "telefono": telefono,
                        "destino": direccion, "email": email, "conductor": conductor,
                        "tipo_huevo": clasificacion, "cantidad": cantidad,
                        "precio_unitario": precio_u, "total": subtotal, "galpon": galp_origen
                    }
                    datos_reales = {k: v for k, v in datos_insert.items() if k in columnas_validas}
                    if datos_reales:
                        cols = ", ".join(datos_reales.keys())
                        vals = tuple(datos_reales.values())
                        placeholders = ", ".join(["%s"] * len(datos_reales))
                        cur.execute(f"INSERT INTO remisiones ({cols}) VALUES ({placeholders})", vals)

                    cur.execute(f"UPDATE inventario SET {clasificacion} = {clasificacion} - %s WHERE galpon = %s", (cantidad, galp_origen))

                cur.execute("""
                    INSERT INTO cartera (num_remision, cliente, total, saldo, estado)
                    VALUES (%s, %s, %s, %s, 'PENDIENTE')
                    ON CONFLICT (num_remision) DO UPDATE SET
                        cliente = EXCLUDED.cliente, total = EXCLUDED.total, saldo = EXCLUDED.saldo;
                """, (num_remision, cliente.strip().upper(), total_venta_acumulado, total_venta_acumulado))


# --- CARTERA ---
@lectura_segura
def cargar_cartera():
    return leer_df("SELECT * FROM cartera ORDER BY num_remision DESC")


@lectura_segura
def cargar_abonos_remision(num_remision):
    return leer_df("SELECT * FROM abonos_cartera WHERE num_remision = %s ORDER BY fecha_abono DESC", (num_remision,))


@operacion_segura
def registrar_abono(num_remision, monto_abono, comprobante_bytes=None, nombre_comprobante=None):
    with get_conn() as conn:
        with conn:
            with conn.cursor() as cur:
                fecha_actual = datetime.now()
                comp_binary = psycopg2.Binary(comprobante_bytes) if comprobante_bytes else None
                cur.execute("""
                    INSERT INTO abonos_cartera (num_remision, fecha_abono, monto, comprobante, nombre_comprobante)
                    VALUES (%s, %s, %s, %s, %s)
                """, (num_remision, fecha_actual, monto_abono, comp_binary, nombre_comprobante))

                cur.execute("SELECT total FROM cartera WHERE num_remision = %s", (num_remision,))
                res = cur.fetchone()
                if res:
                    total = float(res[0])
                    cur.execute("SELECT COALESCE(SUM(monto), 0) FROM abonos_cartera WHERE num_remision = %s", (num_remision,))
                    total_abonos = float(cur.fetchone()[0])
                    nuevo_saldo = max(0.0, total - total_abonos)
                    nuevo_estado = 'PAGADA' if nuevo_saldo <= 0 else 'PENDIENTE'
                    cur.execute("UPDATE cartera SET saldo = %s, estado = %s WHERE num_remision = %s", (nuevo_saldo, nuevo_estado, num_remision))


# --- GASTOS ---
@operacion_segura
def registrar_gasto(fecha, galpon, categoria, descripcion, valor):
    ejecutar("INSERT INTO gastos (fecha, galpon, categoria, descripcion, valor) VALUES (%s, %s, %s, %s, %s)",
              (fecha, galpon, categoria, descripcion, valor))


@lectura_segura
def cargar_gastos():
    df = leer_df("SELECT * FROM gastos ORDER BY fecha DESC, id DESC")
    if not df.empty:
        df['fecha'] = pd.to_datetime(df['fecha']).dt.date
    return df


@operacion_segura
def eliminar_gasto(gasto_id):
    ejecutar("DELETE FROM gastos WHERE id = %s", (gasto_id,))


@operacion_segura
def registrar_gasto_vario(fecha, categoria, descripcion, valor):
    ejecutar("INSERT INTO gastos_varios (fecha, categoria, descripcion, valor) VALUES (%s, %s, %s, %s)",
              (fecha, categoria, descripcion, valor))


@lectura_segura
def cargar_gastos_varios():
    df = leer_df("SELECT * FROM gastos_varios ORDER BY fecha DESC, id DESC")
    if not df.empty:
        df['fecha'] = pd.to_datetime(df['fecha']).dt.date
    return df


@operacion_segura
def eliminar_gasto_vario(gasto_id):
    ejecutar("DELETE FROM gastos_varios WHERE id = %s", (gasto_id,))


# --- REGISTRO DIARIO ---
@operacion_segura
def guardar_config_galpon(galpon, semanas, dias, aves):
    ejecutar("""
        INSERT INTO galpon_config (galpon, edad_semanas, edad_dias, aves_iniciales)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (galpon) DO UPDATE SET
            edad_semanas = EXCLUDED.edad_semanas, edad_dias = EXCLUDED.edad_dias,
            aves_iniciales = EXCLUDED.aves_iniciales;
    """, (galpon, semanas, dias, aves))


def cargar_config_galpon(galpon):
    try:
        res = consultar_uno("SELECT edad_semanas, edad_dias, aves_iniciales FROM galpon_config WHERE galpon = %s", (galpon,))
    except psycopg2.Error as e:
        str_app.error(f"⚠️ No se pudo cargar la configuración del galpón.\n\nDetalle: {e}")
        return None
    if res:
        return {"edad_semanas": res[0], "edad_dias": res[1], "aves_iniciales": res[2]}
    return None


@operacion_segura
def registrar_dia_galpon(fecha, galpon, mortalidad, conc_ingresado, conc_consumido, huevos, observaciones):
    ejecutar("""
        INSERT INTO registros_diarios (fecha, galpon, mortalidad, concentrado_ingresado, concentrado_consumido, huevos_recolectados, observaciones)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (fecha, galpon, mortalidad, conc_ingresado, conc_consumido, huevos, observaciones))


@lectura_segura
def cargar_registros_diarios(galpon=None):
    if galpon:
        df = leer_df("SELECT * FROM registros_diarios WHERE galpon = %s ORDER BY fecha DESC, id DESC", (galpon,))
    else:
        df = leer_df("SELECT * FROM registros_diarios ORDER BY fecha DESC, id DESC")
    if not df.empty:
        df['fecha'] = pd.to_datetime(df['fecha']).dt.date
    return df


@operacion_segura
def eliminar_registro_diario(reg_id):
    ejecutar("DELETE FROM registros_diarios WHERE id = %s", (reg_id,))


# --- REINICIO TOTAL DEL SISTEMA ---
@operacion_segura
def reiniciar_sistema_completo():
    tablas_a_limpiar = ["abonos_cartera", "cartera", "remisiones", "clientes", "gastos",
                         "gastos_varios", "registros_diarios", "galpon_config", "historial_entradas"]
    for tabla in tablas_a_limpiar:
        try:
            ejecutar(f"TRUNCATE TABLE {tabla} RESTART IDENTITY CASCADE;")
        except psycopg2.Error:
            ejecutar(f"DELETE FROM {tabla};")
    ejecutar("UPDATE inventario SET yumbo = 0, extra = 0, aa = 0, a = 0, b = 0, c = 0, sucio = 0, roto = 0;")


# =========================================================================
# RESUMEN GENERAL (DASHBOARD)
# =========================================================================
def calcular_resumen_general():
    resumen = {
        "stock_total": 0, "cartera_pendiente": 0.0, "produccion_hoy": 0,
        "mortalidad_mes": 0, "gastos_mes": 0.0, "ventas_mes": 0.0,
        "stock_por_galpon": {g: 0 for g in GALPONES},
        "produccion_por_galpon": {g: 0 for g in GALPONES},
        "mortalidad_por_galpon": {g: 0 for g in GALPONES},
    }
    hoy = date.today()
    inicio_mes = pd.Timestamp(hoy.replace(day=1))

    df_inv = cargar_inventario()
    if not df_inv.empty:
        cols_presentes = [c for c in COLUMNAS_INVENTARIO if c in df_inv.columns]
        resumen["stock_total"] = int(df_inv[cols_presentes].sum().sum())
        for g in GALPONES:
            if g in df_inv.index:
                resumen["stock_por_galpon"][g] = int(df_inv.loc[g, cols_presentes].sum())

    df_cartera = cargar_cartera()
    if not df_cartera.empty and "estado" in df_cartera.columns:
        resumen["cartera_pendiente"] = float(df_cartera[df_cartera["estado"] == "PENDIENTE"]["saldo"].sum())

    df_reg = cargar_registros_diarios()
    if not df_reg.empty:
        df_hoy = df_reg[df_reg["fecha"] == hoy]
        resumen["produccion_hoy"] = int(df_hoy["huevos_recolectados"].sum())
        if "galpon" in df_hoy.columns:
            for g in GALPONES:
                resumen["produccion_por_galpon"][g] = int(df_hoy[df_hoy["galpon"] == g]["huevos_recolectados"].sum())

        df_mes = df_reg[pd.to_datetime(df_reg["fecha"]) >= inicio_mes]
        resumen["mortalidad_mes"] = int(df_mes["mortalidad"].sum())
        if "galpon" in df_mes.columns:
            for g in GALPONES:
                resumen["mortalidad_por_galpon"][g] = int(df_mes[df_mes["galpon"] == g]["mortalidad"].sum())

    total_gastos_mes = 0.0
    df_gastos = cargar_gastos()
    if not df_gastos.empty:
        total_gastos_mes += float(df_gastos[pd.to_datetime(df_gastos["fecha"]) >= inicio_mes]["valor"].sum())
    df_gastos_v = cargar_gastos_varios()
    if not df_gastos_v.empty:
        total_gastos_mes += float(df_gastos_v[pd.to_datetime(df_gastos_v["fecha"]) >= inicio_mes]["valor"].sum())
    resumen["gastos_mes"] = total_gastos_mes

    df_rem = cargar_remisiones()
    if not df_rem.empty and "fecha_emision" in df_rem.columns and "total" in df_rem.columns:
        df_rem_mes = df_rem[pd.to_datetime(df_rem["fecha_emision"]) >= inicio_mes]
        resumen["ventas_mes"] = float(df_rem_mes["total"].sum())

    return resumen


def _fila_metrica_con_desglose(icono, titulo, valor_total, valores_por_galpon, es_moneda=False):
    """Muestra una métrica grande (ej. Stock Total) y, justo debajo, una fila
    con el mismo dato desglosado por cada uno de los galpones."""
    if es_moneda:
        texto_total = f"${valor_total:,.0f}".replace(",", ".")
    else:
        texto_total = f"{valor_total:,}".replace(",", ".")
    str_app.metric(f"{icono} {titulo}", texto_total)

    cols = str_app.columns(len(GALPONES))
    for col, g in zip(cols, GALPONES):
        valor_g = valores_por_galpon.get(g, 0)
        texto_g = f"${valor_g:,.0f}".replace(",", ".") if es_moneda else f"{valor_g:,}".replace(",", ".")
        col.markdown(
            f"<div style='text-align:center; background-color:#163559; border:1px solid #244c7c; "
            f"border-radius:8px; padding:6px 2px; margin-top:-8px;'>"
            f"<p style='margin:0; font-size:11px; color:#cbd5e1;'>{g}</p>"
            f"<p style='margin:0; font-size:14px; color:#ffffff; font-weight:bold;'>{texto_g}</p>"
            f"</div>", unsafe_allow_html=True
        )
    str_app.markdown("<div style='margin-bottom:12px;'></div>", unsafe_allow_html=True)


def mostrar_resumen_general():
    str_app.subheader("🏠 Resumen General")
    resumen = calcular_resumen_general()

    _fila_metrica_con_desglose("📦", "Stock Total", resumen["stock_total"], resumen["stock_por_galpon"])
    _fila_metrica_con_desglose("🥚", "Producción Hoy", resumen["produccion_hoy"], resumen["produccion_por_galpon"])
    _fila_metrica_con_desglose("💀", "Mortalidad del Mes", resumen["mortalidad_mes"], resumen["mortalidad_por_galpon"])

    str_app.markdown("---")
    c1, c2, c3 = str_app.columns(3)
    c1.metric("💰 Cartera Pendiente", f"${resumen['cartera_pendiente']:,.0f}".replace(",", "."))
    c2.metric("💸 Gastos del Mes", f"${resumen['gastos_mes']:,.0f}".replace(",", "."))
    c3.metric("📈 Ventas del Mes", f"${resumen['ventas_mes']:,.0f}".replace(",", "."))

    df_reg_all = cargar_registros_diarios()
    if not df_reg_all.empty:
        df_tendencia = df_reg_all.groupby("fecha")[["huevos_recolectados", "mortalidad"]].sum().reset_index()
        df_tendencia = df_tendencia.sort_values("fecha").tail(14).set_index("fecha")
        if not df_tendencia.empty:
            str_app.caption("📊 Producción y mortalidad — últimos 14 días con registro (todos los galpones)")
            str_app.line_chart(df_tendencia)

    str_app.markdown("---")


# =========================================================================
# UTILIDADES DE INTERFAZ (confirmaciones, exportación)
# =========================================================================
def confirmar_eliminacion(clave, etiqueta="🗑️ Eliminar", mensaje="¿Confirmas que deseas eliminar este registro? Esta acción no se puede deshacer."):
    """Botón de eliminar con doble confirmación para evitar borrados accidentales.
    Devuelve True únicamente en el momento en que el usuario confirma."""
    estado_key = f"confirmar_del_{clave}"
    if not str_app.session_state.get(estado_key, False):
        if str_app.button(etiqueta, key=f"btn_del_{clave}"):
            str_app.session_state[estado_key] = True
            str_app.rerun()
        return False

    str_app.warning(mensaje)
    c1, c2 = str_app.columns(2)
    confirmado = c1.button("✅ Sí, eliminar", key=f"si_del_{clave}", use_container_width=True)
    cancelado = c2.button("❌ Cancelar", key=f"no_del_{clave}", use_container_width=True)
    if cancelado:
        str_app.session_state[estado_key] = False
        str_app.rerun()
    if confirmado:
        str_app.session_state[estado_key] = False
    return confirmado


def boton_exportar_excel(df, nombre_archivo, etiqueta="📊 Descargar en Excel", key=None):
    if df is None or df.empty:
        return
    try:
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Datos")
        buffer.seek(0)
        str_app.download_button(etiqueta, data=buffer, file_name=nombre_archivo,
                                 mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key=key)
    except ImportError:
        str_app.caption("ℹ️ Instala 'openpyxl' en el servidor para habilitar la exportación a Excel.")


# =========================================================================
# GENERACIÓN DE PDF (estilos compartidos para no repetir código)
# =========================================================================
def _estilos_pdf():
    styles = getSampleStyleSheet()
    return {
        "normal": ParagraphStyle('NormalStyle', parent=styles['Normal'], fontName='Helvetica', fontSize=9, textColor=colors.HexColor("#333333")),
        "bold": ParagraphStyle('BoldStyle', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=9, textColor=colors.HexColor("#333333")),
        "right": ParagraphStyle('RightStyle', parent=styles['Normal'], fontName='Helvetica', fontSize=9, textColor=colors.HexColor("#333333"), alignment=2),
        "right_bold": ParagraphStyle('RightBoldStyle', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=9, textColor=colors.HexColor("#333333"), alignment=2),
        "th": ParagraphStyle('THStyle', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=9, textColor=colors.white, alignment=1),
        "th_left": ParagraphStyle('THLeftStyle', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=9, textColor=colors.white, alignment=0),
        "th_right": ParagraphStyle('THRightStyle', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=9, textColor=colors.white, alignment=2),
    }


def _logo_pdf(estilos):
    if os.path.exists("LOGOASI.png"):
        return Image("LOGOASI.png", width=70, height=70)
    return Paragraph("<b>🥚</b>", estilos["bold"])


def _moneda(valor):
    return f"$ {valor:,.0f}".replace(",", ".")


def _encabezado_pdf(estilos, subtitulo, texto_derecha):
    header_data = [[
        _logo_pdf(estilos),
        Paragraph(f"<b>{NOMBRE_EMPRESA}</b><br/><font size=8>{NIT_EMPRESA}<br/>{subtitulo}</font>", estilos["normal"]),
        Paragraph(texto_derecha, estilos["right"])
    ]]
    t_header = Table(header_data, colWidths=[80, 294, 160])
    t_header.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
    ]))
    return t_header


def generar_pdf_remision(num_remision, fecha_str, conductor, cliente_datos, items_df, total_factura):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    story = []
    e = _estilos_pdf()
    num_str = f"{num_remision:06d}"

    story.append(_encabezado_pdf(e, TELEFONOS_EMPRESA, f"<b>Remisión No.</b><br/><font size=13 color='#f26822'><b>{num_str}</b></font>"))
    story.append(Spacer(1, 10))

    info_data = [
        [Paragraph("<b>Fecha</b>", e["bold"]), Paragraph(f": {fecha_str}", e["normal"]), Paragraph("<b>Datos del cliente</b>", e["bold"]), ""],
        [Paragraph("<b>Conductor</b>", e["bold"]), Paragraph(f": {conductor}", e["normal"]), Paragraph("<b>Nombre / Razón Social</b>", e["bold"]), Paragraph(f": {cliente_datos['nombre']}", e["normal"])],
        [Paragraph("", e["normal"]), Paragraph("", e["normal"]), Paragraph("<b>Cédula / NIT</b>", e["bold"]), Paragraph(f": {cliente_datos['cedula']}", e["normal"])],
        [Paragraph("", e["normal"]), Paragraph("", e["normal"]), Paragraph("<b>Dirección</b>", e["bold"]), Paragraph(f": {cliente_datos['direccion']}", e["normal"])],
        [Paragraph("", e["normal"]), Paragraph("", e["normal"]), Paragraph("<b>Teléfono</b>", e["bold"]), Paragraph(f": {cliente_datos['telefono']}", e["normal"])],
        [Paragraph("", e["normal"]), Paragraph("", e["normal"]), Paragraph("<b>Email</b>", e["bold"]), Paragraph(f": {cliente_datos['email']}", e["normal"])],
    ]
    t_info = Table(info_data, colWidths=[70, 160, 110, 194])
    t_info.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP'), ('BOTTOMPADDING', (0, 0), (-1, -1), 3), ('TOPPADDING', (0, 0), (-1, -1), 3)]))
    story.append(t_info)
    story.append(Spacer(1, 15))

    table_data = [[
        Paragraph("Clasificación", e["th_left"]),
        Paragraph("Cantidad", e["th"]),
        Paragraph("Valor Unitario", e["th_right"]),
        Paragraph("Valor total", e["th_right"])
    ]]
    for _, fila in items_df.iterrows():
        table_data.append([
            Paragraph(str(fila["Clasificación"]).upper(), e["normal"]),
            Paragraph(f"{int(fila['Cantidad (Huevos)']):,}".replace(",", "."), e["right"]),
            Paragraph(_moneda(fila['Precio Unitario ($)']), e["right"]),
            Paragraph(_moneda(fila['Subtotal ($)']), e["right"])
        ])

    t_items = Table(table_data, colWidths=[140, 100, 130, 164])
    t_items.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#0f2942")),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6), ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor("#f8fafc"), colors.white]),
    ]))
    story.append(t_items)
    story.append(Spacer(1, 10))

    totales_data = [
        [Paragraph("<b>Subtotal</b>", e["right"]), Paragraph(f"<b>{_moneda(total_factura)}</b>", e["right_bold"])],
        [Paragraph("<b>IVA</b>", e["right"]), Paragraph("<b>$ 0</b>", e["right_bold"])],
        [Paragraph("<b>Total</b>", e["right"]), Paragraph(f"<b>{_moneda(total_factura)}</b>", e["right_bold"])]
    ]
    t_totales = Table(totales_data, colWidths=[374, 160])
    t_totales.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'RIGHT'), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 3), ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LINEABOVE', (0, 2), (-1, 2), 1, colors.HexColor("#0f2942")),
    ]))
    story.append(t_totales)

    doc.build(story)
    buffer.seek(0)
    return buffer


def generar_pdf_registro_diario(galpon_nombre, config, df_reg, current_edad_str, current_aves, saldo_conc):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    story = []
    e = _estilos_pdf()

    story.append(_encabezado_pdf(e, f"Reporte Registro Diario - {galpon_nombre}",
                                  f"<b>Fecha Reporte:</b><br/><font size=10 color='#f26822'><b>{datetime.now().strftime('%Y-%m-%d')}</b></font>"))
    story.append(Spacer(1, 10))

    aves_ini_val = config['aves_iniciales'] if config else 0
    resumen_data = [
        [Paragraph(f"<b>Edad Actual:</b> {current_edad_str}", e["normal"]), Paragraph(f"<b>Aves Actuales:</b> {current_aves:,}".replace(",", "."), e["normal"])],
        [Paragraph(f"<b>Aves Iniciales:</b> {aves_ini_val:,}".replace(",", "."), e["normal"]), Paragraph(f"<b>Saldo Concentrado:</b> {saldo_conc:,.1f} bultos", e["normal"])]
    ]
    t_resumen = Table(resumen_data, colWidths=[267, 267])
    t_resumen.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'), ('PADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(t_resumen)
    story.append(Spacer(1, 15))

    table_data = [[
        Paragraph("Fecha", e["th_left"]), Paragraph("Mortalidad", e["th"]),
        Paragraph("Ingreso Conc. (Bultos)", e["th_right"]), Paragraph("Consumo Conc. (Bultos)", e["th_right"]),
        Paragraph("Huevos", e["th_right"])
    ]]
    for _, fila in df_reg.iterrows():
        table_data.append([
            Paragraph(str(fila["fecha"]), e["normal"]),
            Paragraph(str(int(fila.get("mortalidad", 0))), e["right"]),
            Paragraph(f"{float(fila.get('concentrado_ingresado', 0)):.1f}", e["right"]),
            Paragraph(f"{float(fila.get('concentrado_consumido', 0)):.1f}", e["right"]),
            Paragraph(str(int(fila.get("huevos_recolectados", 0))), e["right"])
        ])

    t_items = Table(table_data, colWidths=[100, 90, 115, 115, 114])
    t_items.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#0f2942")),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5), ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor("#f8fafc"), colors.white]),
    ]))
    story.append(t_items)

    doc.build(story)
    buffer.seek(0)
    return buffer


def generar_pdf_gastos(df_gastos, titulo_reporte):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    story = []
    e = _estilos_pdf()

    story.append(_encabezado_pdf(e, titulo_reporte, f"<b>Fecha:</b><br/><font size=10 color='#f26822'><b>{datetime.now().strftime('%Y-%m-%d')}</b></font>"))
    story.append(Spacer(1, 15))

    table_data = [[
        Paragraph("Fecha", e["th_left"]), Paragraph("Galpón / Cat.", e["th_left"]),
        Paragraph("Categoría / Desc.", e["th_left"]), Paragraph("Valor ($)", e["th_right"])
    ]]

    total_gasto = 0.0
    for _, fila in df_gastos.iterrows():
        val = float(fila.get("valor", 0))
        total_gasto += val
        col2_val = str(fila.get("galpon", fila.get("categoria", "")))
        col3_val = str(fila.get("categoria", "")) if "galpon" in fila else str(fila.get("descripcion", ""))
        table_data.append([
            Paragraph(str(fila.get("fecha", "")), e["normal"]),
            Paragraph(col2_val, e["normal"]),
            Paragraph(col3_val, e["normal"]),
            Paragraph(_moneda(val), e["right"])
        ])

    t_items = Table(table_data, colWidths=[90, 110, 174, 160])
    t_items.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#0f2942")),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5), ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor("#f8fafc"), colors.white]),
    ]))
    story.append(t_items)
    story.append(Spacer(1, 10))

    totales_data = [[Paragraph("<b>Total Gastos</b>", e["right"]), Paragraph(f"<b>{_moneda(total_gasto)}</b>", e["right_bold"])]]
    t_totales = Table(totales_data, colWidths=[374, 160])
    t_totales.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'RIGHT'), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 3), ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LINEABOVE', (0, 0), (-1, 0), 1, colors.HexColor("#0f2942")),
    ]))
    story.append(t_totales)

    doc.build(story)
    buffer.seek(0)
    return buffer


# =========================================================================
# CONTROL DE SESIÓN Y AUTENTICACIÓN
# (Se dejan las contraseñas tal como estaban, a petición explícita del
# usuario. Sí se agregó un bloqueo temporal tras varios intentos fallidos
# para dificultar ataques de fuerza bruta desde la pantalla de login.)
# =========================================================================
if "usuario_autenticado" not in str_app.session_state:
    str_app.session_state.usuario_autenticado = None

PASS_ADMIN = "admin123"
PASS_INVITADO = "invitado123"

MAX_INTENTOS_LOGIN = 5
BLOQUEO_SEGUNDOS = 60

if str_app.session_state.usuario_autenticado is None:
    col_logo, col_tit = str_app.columns([1, 3.5])
    with col_logo:
        if os.path.exists("LOGOASI.png"):
            str_app.image("LOGOASI.png", width=110)
        else:
            str_app.markdown("<h1 style='margin: 0;'>🥚</h1>", unsafe_allow_html=True)
    with col_tit:
        str_app.markdown('<h2 style="margin: 0; color: #f26822 !important;">AVÍCOLA SANTA ISABEL</h2><p style="margin: 0;">CONTROL DE ACCESO</p>', unsafe_allow_html=True)

    str_app.markdown("---")
    str_app.subheader("🔒 Iniciar Sesión")

    intentos = str_app.session_state.get("intentos_fallidos", 0)
    bloqueado_hasta = str_app.session_state.get("bloqueado_hasta", 0)
    ahora = time.time()

    if intentos >= MAX_INTENTOS_LOGIN and ahora < bloqueado_hasta:
        segundos_restantes = int(bloqueado_hasta - ahora)
        str_app.error(f"🔒 Demasiados intentos fallidos. Intenta de nuevo en {segundos_restantes} segundos.")
    else:
        if ahora >= bloqueado_hasta:
            str_app.session_state["intentos_fallidos"] = 0

        tipo_usuario = str_app.selectbox("Seleccione el Tipo de Usuario", ["Administrador", "Invitado"])
        password_ingresada = str_app.text_input("Contraseña", type="password")

        if str_app.button("🚀 Ingresar al Sistema", use_container_width=True):
            clave_correcta = PASS_ADMIN if tipo_usuario == "Administrador" else PASS_INVITADO
            if password_ingresada == clave_correcta:
                str_app.session_state.usuario_autenticado = tipo_usuario
                str_app.session_state["intentos_fallidos"] = 0
                str_app.success(f"¡Bienvenido {tipo_usuario}!")
                str_app.rerun()
            else:
                str_app.session_state["intentos_fallidos"] = intentos + 1
                if str_app.session_state["intentos_fallidos"] >= MAX_INTENTOS_LOGIN:
                    str_app.session_state["bloqueado_hasta"] = time.time() + BLOQUEO_SEGUNDOS
                    str_app.error(f"🔒 Demasiados intentos fallidos. Intenta de nuevo en {BLOQUEO_SEGUNDOS} segundos.")
                else:
                    str_app.error(f"Contraseña de {tipo_usuario} incorrecta. Intento {str_app.session_state['intentos_fallidos']}/{MAX_INTENTOS_LOGIN}.")

else:
    asegurar_tablas()

    # --- ENCABEZADO ---
    col_logo, col_tit = str_app.columns([1, 3.5])
    with col_logo:
        if os.path.exists("LOGOASI.png"):
            str_app.image("LOGOASI.png", width=75)
        else:
            str_app.markdown("<h1 style='margin: 0;'>🥚</h1>", unsafe_allow_html=True)
    with col_tit:
        rol_actual = str_app.session_state.usuario_autenticado
        color_rol = "#f26822" if rol_actual == "Administrador" else "#3498db"
        str_app.markdown(f'<h2 style="margin: 0; color: #f26822 !important;">AVÍCOLA SANTA ISABEL</h2><p style="margin: 0;">Sesión: <b style="color: {color_rol};">{rol_actual}</b></p>', unsafe_allow_html=True)

    if str_app.button("🚪 Cerrar Sesión"):
        str_app.session_state.usuario_autenticado = None
        str_app.session_state.sesion_principal = None
        str_app.session_state.seccion_activa = None
        str_app.rerun()

    str_app.markdown("---")

    # Todo el contenido autenticado queda protegido por un manejador de
    # errores general: si la base de datos falla a mitad de una operación,
    # el usuario ve un mensaje claro con un botón de reintentar, en vez de
    # una pantalla rota.
    try:
        if "sesion_principal" not in str_app.session_state:
            str_app.session_state.sesion_principal = None

        if str_app.session_state.sesion_principal is None:
            mostrar_resumen_general()

            c_prin1, c_prin2 = str_app.columns(2)
            with c_prin1:
                if str_app.button("📦 Stock y Ventas", use_container_width=True):
                    str_app.session_state.sesion_principal = "📦 Stock y Ventas"
                    str_app.session_state.seccion_activa = None
                    str_app.rerun()
            with c_prin2:
                if str_app.button("📝 Registro Diario", use_container_width=True):
                    str_app.session_state.sesion_principal = "📝 Registro Diario"
                    str_app.rerun()

            if rol_actual == "Administrador":
                str_app.markdown("---")
                if "confirmar_reinicio" not in str_app.session_state:
                    str_app.session_state.confirmar_reinicio = False

                if not str_app.session_state.confirmar_reinicio:
                    if str_app.button("🧹 Reiniciar Sistema (Dejar en Ceros)", use_container_width=True):
                        str_app.session_state.confirmar_reinicio = True
                        str_app.rerun()
                else:
                    str_app.warning("⚠️ ¿Estás completamente seguro? Esto borrará todas las remisiones, abonos, clientes, gastos, registros diarios y pondrá el stock en 0.")
                    c_conf1, c_conf2 = str_app.columns(2)
                    with c_conf1:
                        if str_app.button("✅ Sí, borrar todo", use_container_width=True):
                            if reiniciar_sistema_completo():
                                str_app.session_state.confirmar_reinicio = False
                                str_app.success("¡El sistema ha sido reiniciado a ceros con éxito!")
                                str_app.rerun()
                    with c_conf2:
                        if str_app.button("❌ Cancelar", use_container_width=True):
                            str_app.session_state.confirmar_reinicio = False
                            str_app.rerun()
        else:
            if str_app.button("⬅️ Regresar al Menú Principal"):
                str_app.session_state.sesion_principal = None
                str_app.session_state.seccion_activa = None
                str_app.rerun()

        # --- CONTENIDO DE LAS SESIONES ---
        if str_app.session_state.sesion_principal == "📦 Stock y Ventas":

            if "seccion_activa" not in str_app.session_state or str_app.session_state.seccion_activa is None:
                str_app.subheader("📦 Módulo Stock y Ventas")
                str_app.caption("Seleccione una opción para continuar:")

                col_m1, col_m2 = str_app.columns(2)
                with col_m1:
                    if str_app.button("📥 Entradas de Stock", use_container_width=True):
                        str_app.session_state.seccion_activa = "📥 Entradas"
                        str_app.rerun()
                    if str_app.button("📤 Nueva Remisión", use_container_width=True):
                        str_app.session_state.seccion_activa = "📤 Remisiones"
                        str_app.rerun()
                    if str_app.button("📊 Ver Stock Actual", use_container_width=True):
                        str_app.session_state.seccion_activa = "📊 Stock"
                        str_app.rerun()
                    if str_app.button("💸 Control de Gastos", use_container_width=True):
                        str_app.session_state.seccion_activa = "💸 Gastos"
                        str_app.rerun()
                with col_m2:
                    if str_app.button("👥 Clientes", use_container_width=True):
                        str_app.session_state.seccion_activa = "👥 Clientes"
                        str_app.rerun()
                    if str_app.button("💰 Control de Cartera", use_container_width=True):
                        str_app.session_state.seccion_activa = "💰 Cartera"
                        str_app.rerun()
                    if str_app.button("⚖️ Inventario Físico", use_container_width=True):
                        str_app.session_state.seccion_activa = "⚖️ Inventario Fisico"
                        str_app.rerun()
                    if str_app.button("📜 Historial de Remisiones", use_container_width=True):
                        str_app.session_state.seccion_activa = "📜 Historial"
                        str_app.rerun()
                    if str_app.button("📈 Utilidades por Galpón", use_container_width=True):
                        str_app.session_state.seccion_activa = "📈 Utilidades"
                        str_app.rerun()
                    if str_app.button("🏷️ Gastos Varios", use_container_width=True):
                        str_app.session_state.seccion_activa = "🏷️ Gastos Varios"
                        str_app.rerun()

            else:
                if str_app.button("🔙 Volver al Menú de Stock"):
                    str_app.session_state.seccion_activa = None
                    str_app.rerun()

                str_app.markdown("---")

                # ---------------- ENTRADAS ----------------
                if str_app.session_state.seccion_activa == "📥 Entradas":
                    str_app.subheader("📥 Entrada de Producción / Clasificación")
                    if rol_actual == "Invitado":
                        str_app.warning("👀 Modo Invitado: Solo puedes visualizar la sección.")
                    else:
                        str_app.caption("Registre los huevos recolectados y clasificados para sumarlos al inventario del galpón correspondiente.")
                        galpon_destino = str_app.selectbox("Seleccione el Galpón de Destino", GALPONES)
                        fecha_entrada = str_app.date_input("Fecha de la Entrada", value=date.today(), key="fecha_entrada_stock")

                        df_base_entrada = pd.DataFrame([{"Clasificación": "a", "Cantidad": 0}])
                        df_entrada_editado = str_app.data_editor(
                            df_base_entrada, num_rows="dynamic",
                            column_config={
                                "Clasificación": str_app.column_config.SelectboxColumn("Clasificación", options=CLASIFICACIONES, required=True),
                                "Cantidad": str_app.column_config.NumberColumn("Cantidad (Huevos)", min_value=1, step=1, format="%d", required=True)
                            },
                            use_container_width=True, key="editor_entradas_stock"
                        )

                        if str_app.button("➕ Registrar Entrada al Inventario"):
                            entradas_validas = df_entrada_editado[df_entrada_editado["Cantidad"] > 0].copy()
                            if entradas_validas.empty:
                                str_app.warning("Debe ingresar al menos un ítem con cantidad mayor a 0.")
                            else:
                                lista_items_entrada = [{"Clasificación": r["Clasificación"], "Cantidad": int(r["Cantidad"])} for _, r in entradas_validas.iterrows()]
                                if registrar_entrada_inventario(galpon_destino, lista_items_entrada, fecha_entrada):
                                    str_app.toast("¡Registrado con éxito! 🎉", icon="✅")
                                    str_app.success(f"¡Entrada de inventario registrada correctamente en {galpon_destino} el {fecha_entrada}!")
                                    str_app.rerun()

                    str_app.markdown("---")
                    str_app.markdown("#### 📜 Historial de Entradas")
                    df_hist_entradas = cargar_historial_entradas()
                    if not df_hist_entradas.empty:
                        c_gf, c_fi, c_ff = str_app.columns(3)
                        galpon_filtro_hist = c_gf.selectbox("Galpón", ["Todos"] + GALPONES, key="filtro_galpon_hist_entradas")
                        fecha_ini_hist = c_fi.date_input("Desde", value=df_hist_entradas["fecha"].min(), key="hist_entradas_desde")
                        fecha_fin_hist = c_ff.date_input("Hasta", value=df_hist_entradas["fecha"].max(), key="hist_entradas_hasta")

                        df_hist_filtrado = df_hist_entradas[(df_hist_entradas["fecha"] >= fecha_ini_hist) & (df_hist_entradas["fecha"] <= fecha_fin_hist)]
                        if galpon_filtro_hist != "Todos":
                            df_hist_filtrado = df_hist_filtrado[df_hist_filtrado["galpon"] == galpon_filtro_hist]

                        if not df_hist_filtrado.empty:
                            df_hist_mostrar = df_hist_filtrado[["fecha", "galpon", "clasificacion", "cantidad"]].copy()
                            df_hist_mostrar.columns = ["Fecha", "Galpón", "Clasificación", "Cantidad"]
                            df_hist_mostrar["Clasificación"] = df_hist_mostrar["Clasificación"].str.upper()
                            str_app.dataframe(df_hist_mostrar, use_container_width=True, hide_index=True)
                            str_app.caption(f"Total en el rango: {int(df_hist_filtrado['cantidad'].sum()):,} huevos".replace(",", "."))
                            boton_exportar_excel(df_hist_mostrar, "Historial_Entradas_Stock.xlsx")
                        else:
                            str_app.info("No hay entradas registradas en el rango seleccionado.")
                    else:
                        str_app.info("Aún no hay entradas de stock registradas.")

                # ---------------- INVENTARIO FÍSICO ----------------
                elif str_app.session_state.seccion_activa == "⚖️ Inventario Fisico":
                    str_app.subheader("⚖️ Inventario Físico y Mermas")
                    if rol_actual == "Invitado":
                        str_app.warning("👀 Modo Invitado: Solo lectura.")
                    else:
                        galpon_fisico = str_app.selectbox("Seleccione el Galpón a Auditar", GALPONES)
                        df_inv_actual = cargar_inventario()
                        fila_galp = df_inv_actual.loc[galpon_fisico] if galpon_fisico in df_inv_actual.index else pd.Series({c: 0 for c in CLASIFICACIONES})

                        datos_fisicos = []
                        for col_clasif in CLASIFICACIONES:
                            stock_sistema = int(fila_galp.get(col_clasif, 0))
                            datos_fisicos.append({"Clasificación": col_clasif, "Stock Sistema": stock_sistema, "Conteo Físico Real": stock_sistema})

                        df_fisico_base = pd.DataFrame(datos_fisicos)
                        df_fisico_editado = str_app.data_editor(
                            df_fisico_base, disabled=["Clasificación", "Stock Sistema"],
                            column_config={
                                "Stock Sistema": str_app.column_config.NumberColumn("Stock Sistema", format="%d"),
                                "Conteo Físico Real": str_app.column_config.NumberColumn("Conteo Físico Real", min_value=0, step=1, format="%d")
                            },
                            use_container_width=True, key=f"editor_fisico_{galpon_fisico}"
                        )

                        df_fisico_editado["Diferencia (Merma/Faltante)"] = df_fisico_editado["Stock Sistema"] - df_fisico_editado["Conteo Físico Real"]
                        str_app.dataframe(df_fisico_editado[["Clasificación", "Stock Sistema", "Conteo Físico Real", "Diferencia (Merma/Faltante)"]], use_container_width=True, hide_index=True)

                        diferencia_total = int(df_fisico_editado["Diferencia (Merma/Faltante)"].sum())
                        if diferencia_total != 0:
                            str_app.caption(f"⚠️ Diferencia neta detectada: {diferencia_total:,} huevos".replace(",", "."))

                        if str_app.button("💾 Guardar y Ajustar Inventario Físico"):
                            nuevo_stock_dict = {r["Clasificación"]: int(r["Conteo Físico Real"]) for _, r in df_fisico_editado.iterrows()}
                            if actualizar_inventario_fisico(galpon_fisico, nuevo_stock_dict):
                                str_app.toast("¡Registrado con éxito! 🎉", icon="✅")
                                str_app.success(f"¡Inventario físico de {galpon_fisico} aplicado con éxito!")
                                str_app.rerun()

                # ---------------- GASTOS POR GALPÓN ----------------
                elif str_app.session_state.seccion_activa == "💸 Gastos":
                    str_app.subheader("💸 Control de Gastos por Galpón")
                    if rol_actual == "Invitado":
                        str_app.warning("👀 Modo Invitado: Solo lectura.")
                    else:
                        with str_app.form(key="form_registrar_gasto"):
                            c_fecha_g = str_app.date_input("Fecha del Gasto", value=date.today())
                            c_galpon_g = str_app.selectbox("Galpón Asociado", GALPONES_GASTOS)
                            c_categoria_g = str_app.selectbox("Categoría de Gasto", CATEGORIAS_GASTO_GALPON)
                            c_desc_g = str_app.text_input("Descripción del Gasto", placeholder="Ej. Compra de concentrado fase 1")
                            c_valor_g = str_app.number_input("Valor ($)", min_value=0.0, step=1000.0, format="%.0f")

                            if str_app.form_submit_button("💾 Guardar Gasto"):
                                if c_valor_g <= 0:
                                    str_app.error("El valor del gasto debe ser mayor a 0.")
                                elif not c_desc_g.strip():
                                    str_app.error("Debes escribir una descripción del gasto.")
                                else:
                                    if registrar_gasto(c_fecha_g, c_galpon_g, c_categoria_g, c_desc_g, c_valor_g):
                                        str_app.toast("¡Registrado con éxito! 🎉", icon="✅")
                                        str_app.success("¡Gasto registrado con éxito!")
                                        str_app.rerun()

                    str_app.markdown("---")
                    df_gastos = cargar_gastos()
                    if not df_gastos.empty:
                        df_gastos['dt_fecha'] = pd.to_datetime(df_gastos['fecha'])
                        df_gastos['Año'] = df_gastos['dt_fecha'].dt.year
                        df_gastos['Mes_Num'] = df_gastos['dt_fecha'].dt.month

                        c_f1, c_f2 = str_app.columns(2)
                        anio_sel_g = c_f1.selectbox("📅 Año (Gastos)", sorted(df_gastos['Año'].unique().tolist(), reverse=True), key="anio_gasto")
                        mes_nombre_sel = c_f2.selectbox("📅 Mes (Gastos)", list(MESES_NOMBRES.values()), key="mes_gasto")
                        mes_num_sel = [k for k, v in MESES_NOMBRES.items() if v == mes_nombre_sel][0]

                        df_gf = df_gastos[(df_gastos['Año'] == anio_sel_g) & (df_gastos['Mes_Num'] == mes_num_sel)]
                        str_app.markdown(f"**Total Gastos Mes:** ${df_gf['valor'].sum():,.0f}".replace(",", "."))

                        if not df_gf.empty:
                            c_pdf, c_xls = str_app.columns(2)
                            with c_pdf:
                                pdf_gastos_buf = generar_pdf_gastos(df_gf, f"Reporte de Gastos - {mes_nombre_sel} {anio_sel_g}")
                                str_app.download_button("📄 Descargar en PDF", data=pdf_gastos_buf, file_name=f"Gastos_{mes_nombre_sel}_{anio_sel_g}.pdf", mime="application/pdf")
                            with c_xls:
                                boton_exportar_excel(df_gf[["fecha", "galpon", "categoria", "descripcion", "valor"]], f"Gastos_{mes_nombre_sel}_{anio_sel_g}.xlsx")
                            str_app.markdown("---")

                        for _, row_g in df_gf.iterrows():
                            with str_app.expander(f"📅 {row_g['fecha']} — [{row_g['galpon']}] {row_g['categoria']}: ${float(row_g['valor']):,.0f}".replace(",", ".")):
                                str_app.write(f"**Desc:** {row_g['descripcion']}")
                                if rol_actual == "Administrador":
                                    if confirmar_eliminacion(f"gasto_{row_g['id']}", etiqueta="🗑️ Eliminar Gasto"):
                                        eliminar_gasto(row_g['id'])
                                        str_app.rerun()

                # ---------------- GASTOS VARIOS ----------------
                elif str_app.session_state.seccion_activa == "🏷️ Gastos Varios":
                    str_app.subheader("🏷️ Control de Gastos Varios y Personales")
                    if rol_actual == "Invitado":
                        str_app.warning("👀 Modo Invitado: Solo lectura.")
                    else:
                        with str_app.form(key="form_registrar_gv"):
                            c_fecha_gv = str_app.date_input("Fecha", value=date.today())
                            c_cat_gv = str_app.selectbox("Categoría", CATEGORIAS_GASTO_VARIO)
                            c_desc_gv = str_app.text_input("Descripción")
                            c_val_gv = str_app.number_input("Valor ($)", min_value=0.0, step=1000.0, format="%.0f")
                            if str_app.form_submit_button("💾 Guardar Gasto Vario"):
                                if c_val_gv <= 0:
                                    str_app.error("El valor debe ser mayor a 0.")
                                else:
                                    if registrar_gasto_vario(c_fecha_gv, c_cat_gv, c_desc_gv, c_val_gv):
                                        str_app.toast("¡Registrado con éxito! 🎉", icon="✅")
                                        str_app.success("¡Guardado!")
                                        str_app.rerun()

                    df_gv = cargar_gastos_varios()
                    if not df_gv.empty:
                        c_pdf, c_xls = str_app.columns(2)
                        with c_pdf:
                            pdf_gv_buf = generar_pdf_gastos(df_gv, "Reporte de Gastos Varios y Personales")
                            str_app.download_button("📄 Descargar en PDF", data=pdf_gv_buf, file_name="Gastos_Varios.pdf", mime="application/pdf")
                        with c_xls:
                            boton_exportar_excel(df_gv[["fecha", "categoria", "descripcion", "valor"]], "Gastos_Varios.xlsx")
                        str_app.markdown("---")

                        for _, r in df_gv.iterrows():
                            with str_app.expander(f"📅 {r['fecha']} — [{r['categoria']}] ${float(r['valor']):,.0f}".replace(",", ".")):
                                str_app.write(f"**Desc:** {r['descripcion']}")
                                if rol_actual == "Administrador":
                                    if confirmar_eliminacion(f"gv_{r['id']}", etiqueta="🗑️ Eliminar"):
                                        eliminar_gasto_vario(r['id'])
                                        str_app.rerun()

                # ---------------- CLIENTES ----------------
                elif str_app.session_state.seccion_activa == "👥 Clientes":
                    str_app.subheader("👥 Directorio de Clientes")
                    df_cli = cargar_clientes()

                    if rol_actual == "Administrador":
                        tab_n, tab_e, tab_l = str_app.tabs(["➕ Agregar", "✏️ Editar", "📋 Lista"])

                        with tab_n:
                            with str_app.form("form_cli_nuevo"):
                                nom = str_app.text_input("Nombre *")
                                ced = str_app.text_input("Cédula/NIT")
                                dir_ = str_app.text_input("Dirección")
                                tel = str_app.text_input("Teléfono")
                                em = str_app.text_input("Email")
                                if str_app.form_submit_button("Guardar"):
                                    if not nom.strip():
                                        str_app.error("El nombre es obligatorio.")
                                    else:
                                        if guardar_cliente(nom, ced, dir_, tel, em):
                                            str_app.toast("¡Registrado con éxito! 🎉", icon="✅")
                                            str_app.success("Guardado!")
                                            str_app.rerun()

                        with tab_e:
                            if df_cli.empty:
                                str_app.info("No hay clientes registrados todavía.")
                            else:
                                cliente_editar = str_app.selectbox("Selecciona el cliente a editar", df_cli["nombre"].tolist(), key="sel_editar_cliente")
                                d_cli = df_cli[df_cli["nombre"] == cliente_editar].iloc[0]
                                with str_app.form("form_cli_editar"):
                                    ced_e = str_app.text_input("Cédula/NIT", value=str(d_cli.get("cedula_nit", "") or ""))
                                    dir_e = str_app.text_input("Dirección", value=str(d_cli.get("direccion", "") or ""))
                                    tel_e = str_app.text_input("Teléfono", value=str(d_cli.get("telefono", "") or ""))
                                    em_e = str_app.text_input("Email", value=str(d_cli.get("email", "") or ""))
                                    if str_app.form_submit_button("💾 Guardar Cambios"):
                                        if guardar_cliente(cliente_editar, ced_e, dir_e, tel_e, em_e):
                                            str_app.toast("¡Actualizado con éxito! 🎉", icon="✅")
                                            str_app.success("¡Cliente actualizado!")
                                            str_app.rerun()

                        with tab_l:
                            filtro_cli = str_app.text_input("🔎 Buscar cliente por nombre")
                            df_cli_filtrado = df_cli[df_cli["nombre"].str.contains(filtro_cli.strip().upper(), na=False)] if filtro_cli.strip() else df_cli
                            for _, r in df_cli_filtrado.iterrows():
                                with str_app.expander(f"👤 {r['nombre']}"):
                                    str_app.write(f"Cédula/NIT: {r.get('cedula_nit', '') or '—'}")
                                    str_app.write(f"Dirección: {r.get('direccion', '') or '—'}")
                                    str_app.write(f"Tel: {r.get('telefono', '') or '—'}")
                                    str_app.write(f"Email: {r.get('email', '') or '—'}")
                                    if confirmar_eliminacion(f"cli_{r['id']}"):
                                        eliminar_cliente(r['id'])
                                        str_app.rerun()
                    else:
                        filtro_cli = str_app.text_input("🔎 Buscar cliente por nombre")
                        df_cli_filtrado = df_cli[df_cli["nombre"].str.contains(filtro_cli.strip().upper(), na=False)] if filtro_cli.strip() else df_cli
                        for _, r in df_cli_filtrado.iterrows():
                            str_app.write(f"👤 **{r['nombre']}** | Tel: {r.get('telefono', '') or '—'}")

                # ---------------- REMISIONES ----------------
                elif str_app.session_state.seccion_activa == "📤 Remisiones":
                    str_app.subheader("📋 Nueva Remisión")
                    if rol_actual == "Invitado":
                        str_app.warning("👀 Modo Invitado.")
                    else:
                        df_inv = cargar_inventario()
                        df_clientes = cargar_clientes()
                        num_rem_act = obtener_siguiente_num_remision()

                        str_app.markdown(f"### Remisión No. {num_rem_act:06d}")
                        fecha_rem = str_app.date_input("Fecha", value=date.today())
                        opciones_cli = ["-- Escribir cliente nuevo --"] + df_clientes["nombre"].tolist() if not df_clientes.empty else ["-- Escribir cliente nuevo --"]
                        cliente_sel = str_app.selectbox("Cliente Guardado", opciones_cli)

                        v_nom, v_ced, v_dir, v_tel, v_em = "", "", "CHOACHI", "", ""
                        if cliente_sel != "-- Escribir cliente nuevo --" and not df_clientes.empty:
                            d_cli = df_clientes[df_clientes["nombre"] == cliente_sel].iloc[0]
                            v_nom, v_ced, v_dir, v_tel, v_em = str(d_cli.get("nombre", "")), str(d_cli.get("cedula_nit", "")), str(d_cli.get("direccion", "CHOACHI")), str(d_cli.get("telefono", "")), str(d_cli.get("email", ""))

                        c_nom = str_app.text_input("Cliente *", value=v_nom)
                        c_ced = str_app.text_input("Cédula/NIT", value=v_ced)
                        c_dir = str_app.text_input("Dirección", value=v_dir)
                        c_tel = str_app.text_input("Teléfono", value=v_tel)
                        c_em = str_app.text_input("Email", value=v_em)
                        c_cond = str_app.text_input("Conductor", value="Ivan Herrera")
                        guardar_cli_auto = str_app.checkbox("Guardar cliente", value=True)

                        df_base = pd.DataFrame([{"Clasificación": "a", "Cantidad (Huevos)": 0, "Precio Unitario ($)": 0, "Galpón Origen": GALPONES[0]}])
                        df_editado = str_app.data_editor(
                            df_base, num_rows="dynamic",
                            column_config={
                                "Clasificación": str_app.column_config.SelectboxColumn("Clasificación", options=CLASIFICACIONES, required=True),
                                "Cantidad (Huevos)": str_app.column_config.NumberColumn("Cantidad (Huevos)", min_value=1, step=1, format="%d", required=True),
                                "Precio Unitario ($)": str_app.column_config.NumberColumn("Precio Unitario ($)", min_value=0, format="$%d", required=True),
                                "Galpón Origen": str_app.column_config.SelectboxColumn("Galpón Origen", options=GALPONES, required=True)
                            },
                            use_container_width=True
                        )
                        items_validos = df_editado[df_editado["Cantidad (Huevos)"] > 0].copy()

                        if not items_validos.empty:
                            items_validos["Subtotal ($)"] = items_validos["Cantidad (Huevos)"] * items_validos["Precio Unitario ($)"]
                            tot_fac = items_validos["Subtotal ($)"].sum()
                            str_app.markdown(f"#### Total: ${tot_fac:,.0f}".replace(",", "."))

                            if str_app.button("🚀 Generar Remisión"):
                                if not c_nom.strip():
                                    str_app.error("El nombre del cliente es obligatorio.")
                                else:
                                    if guardar_cli_auto and c_nom.strip():
                                        guardar_cliente(c_nom, c_ced, c_dir, c_tel, c_em)

                                    items_dict = [{'Clasificación': r['Clasificación'], 'Cantidad (Huevos)': r['Cantidad (Huevos)'], 'Precio Unitario ($)': r['Precio Unitario ($)'], 'Subtotal ($)': r['Subtotal ($)'], 'Galpón': r['Galpón Origen']} for _, r in items_validos.iterrows()]

                                    try:
                                        if registrar_venta_multiple(c_nom, c_ced, c_dir, c_tel, c_em, c_cond, num_rem_act, fecha_rem, items_dict):
                                            str_app.toast("¡Registrado con éxito! 🎉", icon="✅")
                                            str_app.success("¡Remisión guardada con éxito!")

                                            cliente_datos = {"nombre": c_nom, "cedula": c_ced, "direccion": c_dir, "telefono": c_tel, "email": c_em}
                                            pdf_buf = generar_pdf_remision(num_rem_act, str(fecha_rem), c_cond, cliente_datos, items_validos, tot_fac)
                                            str_app.download_button("📄 Descargar Remisión en PDF", data=pdf_buf, file_name=f"Remision_{num_rem_act:06d}.pdf", mime="application/pdf")
                                    except ValueError as e:
                                        str_app.error(str(e))

                # ---------------- CARTERA ----------------
                elif str_app.session_state.seccion_activa == "💰 Cartera":
                    str_app.subheader("💰 Control de Cartera e Historial de Abonos")
                    df_cartera = cargar_cartera()
                    if df_cartera.empty:
                        str_app.info("Sin deudas registradas.")
                    else:
                        solo_pendientes = str_app.checkbox("Mostrar solo remisiones PENDIENTES", value=True)
                        df_cartera_mostrar = df_cartera[df_cartera["estado"] == "PENDIENTE"] if solo_pendientes else df_cartera

                        for _, row in df_cartera_mostrar.iterrows():
                            with str_app.expander(f"Remisión N° {int(row['num_remision']):06d} — {row['cliente']} | Saldo: ${float(row['saldo']):,.0f} ({row['estado']})".replace(",", ".")):
                                str_app.markdown("#### 📜 Historial de Abonos")
                                df_abonos = cargar_abonos_remision(int(row['num_remision']))
                                if not df_abonos.empty:
                                    df_abonos_mostrar = df_abonos[['fecha_abono', 'monto', 'nombre_comprobante']].copy()
                                    df_abonos_mostrar.columns = ['Fecha y Hora', 'Monto ($)', 'Comprobante']
                                    df_abonos_mostrar['Monto ($)'] = df_abonos_mostrar['Monto ($)'].apply(lambda x: f"${float(x):,.0f}".replace(",", "."))
                                    str_app.dataframe(df_abonos_mostrar, use_container_width=True, hide_index=True)
                                else:
                                    str_app.info("No hay abonos registrados para esta remisión.")

                                str_app.markdown("---")
                                if rol_actual == "Administrador" and float(row['saldo']) > 0:
                                    with str_app.form(key=f"ab_{row['num_remision']}"):
                                        str_app.markdown("#### ➕ Registrar Nuevo Abono")
                                        monto = str_app.number_input("Abono ($)", min_value=0.0, max_value=float(row['saldo']), step=1000.0, format="%.0f")
                                        arch = str_app.file_uploader("Comprobante (Opcional)", type=["png", "jpg", "jpeg", "pdf"], key=f"f_{row['num_remision']}")
                                        if str_app.form_submit_button("Registrar Abono"):
                                            if monto <= 0:
                                                str_app.error("El monto del abono debe ser mayor a 0.")
                                            else:
                                                if registrar_abono(int(row['num_remision']), monto, arch.read() if arch else None, arch.name if arch else None):
                                                    str_app.toast("¡Abono registrado con éxito! 🎉", icon="✅")
                                                    str_app.success("¡Abono registrado correctamente!")
                                                    str_app.rerun()

                # ---------------- STOCK ----------------
                elif str_app.session_state.seccion_activa == "📊 Stock":
                    str_app.subheader("📦 Stock Actual")
                    df_stock = cargar_inventario()
                    if not df_stock.empty:
                        df_stock_mostrar = df_stock.copy()
                        df_stock_mostrar.loc["TOTAL"] = df_stock_mostrar.sum(numeric_only=True)
                        str_app.dataframe(df_stock_mostrar, use_container_width=True)
                        boton_exportar_excel(df_stock.reset_index(), "Stock_Actual.xlsx")
                    else:
                        str_app.info("Sin datos de inventario todavía.")

                # ---------------- HISTORIAL DE REMISIONES ----------------
                elif str_app.session_state.seccion_activa == "📜 Historial":
                    str_app.subheader("📜 Historial de Remisiones")
                    df_h = cargar_remisiones()
                    if not df_h.empty and "fecha_emision" in df_h.columns:
                        c_fi, c_ff = str_app.columns(2)
                        fecha_ini = c_fi.date_input("Desde", value=df_h["fecha_emision"].min(), key="hist_desde")
                        fecha_fin = c_ff.date_input("Hasta", value=df_h["fecha_emision"].max(), key="hist_hasta")
                        df_h = df_h[(df_h["fecha_emision"] >= fecha_ini) & (df_h["fecha_emision"] <= fecha_fin)]

                    if not df_h.empty:
                        for num_sel in sorted(df_h['num_remision'].unique(), reverse=True):
                            df_r = df_h[df_h['num_remision'] == num_sel]
                            f_sel = df_r.iloc[0]
                            cliente_nombre = f_sel.get('cliente', '')

                            with str_app.expander(f"Remisión #{int(num_sel):06d} – {cliente_nombre}"):
                                columnas_deseadas = ['tipo_huevo', 'cantidad', 'precio_unitario', 'total', 'galpon']
                                columnas_validas = [col for col in columnas_deseadas if col in df_r.columns]

                                if not df_r.empty and columnas_validas:
                                    str_app.dataframe(df_r[columnas_validas], use_container_width=True)

                                    cliente_datos = {
                                        "nombre": cliente_nombre, "cedula": f_sel.get('cedula_nit', ''),
                                        "direccion": f_sel.get('destino', 'CHOACHI'), "telefono": f_sel.get('telefono', ''),
                                        "email": f_sel.get('email', '')
                                    }
                                    items_pdf = df_r.rename(columns={'tipo_huevo': 'Clasificación', 'cantidad': 'Cantidad (Huevos)', 'precio_unitario': 'Precio Unitario ($)', 'total': 'Subtotal ($)'})
                                    total_factura = df_r['total'].sum()
                                    fecha_str = str(f_sel.get('fecha_emision', date.today()))
                                    conductor_val = f_sel.get('conductor', 'Ivan Herrera')

                                    pdf_buf = generar_pdf_remision(int(num_sel), fecha_str, conductor_val, cliente_datos, items_pdf, total_factura)
                                    str_app.download_button(f"📄 Descargar PDF Remisión #{int(num_sel):06d}", data=pdf_buf, file_name=f"Remision_{int(num_sel):06d}.pdf", mime="application/pdf", key=f"dl_hist_{num_sel}")
                                else:
                                    str_app.warning("No se encontraron registros o columnas válidas para esta remisión.")

                        boton_exportar_excel(df_h, "Historial_Remisiones.xlsx", key="xls_historial")
                    else:
                        str_app.info("No hay remisiones registradas en el rango seleccionado.")

                # ---------------- UTILIDADES POR GALPÓN ----------------
                elif str_app.session_state.seccion_activa == "📈 Utilidades":
                    str_app.subheader("📈 Utilidades por Galpón")
                    str_app.caption("Análisis financiero de ingresos por ventas, gastos directos y utilidad neta por galpón.")

                    df_rem = cargar_remisiones()
                    df_gas = cargar_gastos()

                    if df_rem.empty and df_gas.empty:
                        str_app.info("No hay datos suficientes de ventas o gastos para calcular utilidades.")
                    else:
                        if not df_rem.empty and 'fecha_emision' in df_rem.columns:
                            df_rem['dt_fecha'] = pd.to_datetime(df_rem['fecha_emision'])
                        if not df_gas.empty and 'fecha' in df_gas.columns:
                            df_gas['dt_fecha'] = pd.to_datetime(df_gas['fecha'])

                        anios_disponibles = set()
                        if not df_rem.empty and 'dt_fecha' in df_rem.columns:
                            anios_disponibles.update(df_rem['dt_fecha'].dt.year.unique().tolist())
                        if not df_gas.empty and 'dt_fecha' in df_gas.columns:
                            anios_disponibles.update(df_gas['dt_fecha'].dt.year.unique().tolist())
                        anios_disponibles = sorted(anios_disponibles, reverse=True) if anios_disponibles else [date.today().year]

                        vista_util = str_app.radio("Vista", ["📅 Mes específico", "📊 Histórico completo"], horizontal=True, key="vista_utilidades")

                        if vista_util == "📅 Mes específico":
                            c_fu1, c_fu2 = str_app.columns(2)
                            anio_sel_u = c_fu1.selectbox("📅 Año", anios_disponibles, key="anio_util")
                            indice_mes_actual = date.today().month - 1
                            mes_nombre_sel_u = c_fu2.selectbox("📅 Mes", list(MESES_NOMBRES.values()), index=indice_mes_actual, key="mes_util")
                            mes_num_sel_u = [k for k, v in MESES_NOMBRES.items() if v == mes_nombre_sel_u][0]

                            df_rem_periodo = df_rem[(df_rem['dt_fecha'].dt.year == anio_sel_u) & (df_rem['dt_fecha'].dt.month == mes_num_sel_u)] if not df_rem.empty and 'dt_fecha' in df_rem.columns else pd.DataFrame()
                            df_gas_periodo = df_gas[(df_gas['dt_fecha'].dt.year == anio_sel_u) & (df_gas['dt_fecha'].dt.month == mes_num_sel_u)] if not df_gas.empty and 'dt_fecha' in df_gas.columns else pd.DataFrame()
                            titulo_periodo = f"{mes_nombre_sel_u} {anio_sel_u}"
                        else:
                            df_rem_periodo = df_rem
                            df_gas_periodo = df_gas
                            titulo_periodo = "Histórico completo"

                        resumen_utilidades = []
                        for g in GALPONES:
                            ingresos = float(df_rem_periodo[df_rem_periodo['galpon'] == g]['total'].sum()) if not df_rem_periodo.empty and 'galpon' in df_rem_periodo.columns and 'total' in df_rem_periodo.columns else 0.0
                            gastos = float(df_gas_periodo[df_gas_periodo['galpon'] == g]['valor'].sum()) if not df_gas_periodo.empty and 'galpon' in df_gas_periodo.columns and 'valor' in df_gas_periodo.columns else 0.0
                            resumen_utilidades.append({"Galpón": g, "Ingresos ($)": ingresos, "Gastos ($)": gastos, "Utilidad ($)": ingresos - gastos})

                        gastos_generales = float(df_gas_periodo[df_gas_periodo['galpon'] == "General / Granja"]['valor'].sum()) if not df_gas_periodo.empty and 'galpon' in df_gas_periodo.columns and 'valor' in df_gas_periodo.columns else 0.0

                        df_util = pd.DataFrame(resumen_utilidades)
                        total_ingresos = df_util["Ingresos ($)"].sum()
                        total_gastos_galpones = df_util["Gastos ($)"].sum()
                        utilidad_neta_total = total_ingresos - (total_gastos_galpones + gastos_generales)

                        str_app.markdown(f"#### {titulo_periodo}")
                        col_u1, col_u2, col_u3 = str_app.columns(3)
                        col_u1.metric("Total Ingresos", f"${total_ingresos:,.0f}".replace(",", "."))
                        col_u2.metric("Total Gastos", f"${(total_gastos_galpones + gastos_generales):,.0f}".replace(",", "."))
                        col_u3.metric("Utilidad Neta", f"${utilidad_neta_total:,.0f}".replace(",", "."))

                        if total_ingresos > 0 or total_gastos_galpones > 0:
                            str_app.bar_chart(df_util.set_index("Galpón")[["Ingresos ($)", "Gastos ($)"]])
                        else:
                            str_app.caption(f"Sin movimientos registrados en {titulo_periodo}.")

                        str_app.markdown("---")
                        str_app.markdown("#### 📋 Detalle Financiero por Galpón")

                        df_mostrar = df_util.copy()
                        for col in ["Ingresos ($)", "Gastos ($)", "Utilidad ($)"]:
                            df_mostrar[col] = df_mostrar[col].apply(lambda x: f"$ {x:,.0f}".replace(",", "."))
                        str_app.dataframe(df_mostrar, use_container_width=True, hide_index=True)
                        boton_exportar_excel(df_util, f"Utilidades_{titulo_periodo.replace(' ', '_')}.xlsx")

                        if gastos_generales > 0:
                            str_app.info(f"💡 Gastos Generales / Granja no asignados a un galpón específico: $ {gastos_generales:,.0f}".replace(",", "."))

                        # --- Evolución mensual de la utilidad total (independiente del filtro de arriba) ---
                        str_app.markdown("---")
                        str_app.markdown("#### 📈 Evolución Mensual de la Utilidad (Todos los Galpones)")

                        serie_ingresos_mes = pd.Series(dtype=float)
                        serie_gastos_mes = pd.Series(dtype=float)
                        if not df_rem.empty and 'dt_fecha' in df_rem.columns and 'total' in df_rem.columns:
                            serie_ingresos_mes = df_rem.groupby(df_rem['dt_fecha'].dt.to_period('M'))['total'].sum().rename("Ingresos")
                        if not df_gas.empty and 'dt_fecha' in df_gas.columns and 'valor' in df_gas.columns:
                            serie_gastos_mes = df_gas.groupby(df_gas['dt_fecha'].dt.to_period('M'))['valor'].sum().rename("Gastos")

                        df_evolucion = pd.concat([serie_ingresos_mes, serie_gastos_mes], axis=1).fillna(0.0)
                        if not df_evolucion.empty:
                            df_evolucion["Utilidad"] = df_evolucion["Ingresos"] - df_evolucion["Gastos"]
                            df_evolucion = df_evolucion.sort_index()
                            df_evolucion.index = df_evolucion.index.astype(str)
                            str_app.bar_chart(df_evolucion[["Utilidad"]])

                            with str_app.expander("Ver detalle mes a mes"):
                                df_evolucion_mostrar = df_evolucion.reset_index().rename(columns={"index": "Mes"})
                                for col in ["Ingresos", "Gastos", "Utilidad"]:
                                    df_evolucion_mostrar[col] = df_evolucion_mostrar[col].apply(lambda x: f"$ {x:,.0f}".replace(",", "."))
                                str_app.dataframe(df_evolucion_mostrar, use_container_width=True, hide_index=True)
                                boton_exportar_excel(df_evolucion.reset_index().rename(columns={"index": "Mes"}), "Evolucion_Mensual_Utilidad.xlsx")
                        else:
                            str_app.caption("Aún no hay suficientes datos para mostrar la evolución mensual.")

        elif str_app.session_state.sesion_principal == "📝 Registro Diario":
            str_app.subheader("📝 Módulo de Registro Diario (Edades, Mortalidad y Concentrado)")
            galpon_reg = str_app.selectbox("Seleccione el Galpón", GALPONES, key="galp_reg_sel")
            tab_config, tab_diario, tab_historial = str_app.tabs(["⚙️ Configuración Inicial", "✍️ Registrar Día", "📊 Historial y PDF"])

            with tab_config:
                str_app.markdown("#### Configuración Inicial del Lote (Se ingresa una sola vez)")
                config_actual = cargar_config_galpon(galpon_reg)

                ini_sem = config_actual['edad_semanas'] if config_actual else 0
                ini_dias = config_actual['edad_dias'] if config_actual else 0
                ini_aves = config_actual['aves_iniciales'] if config_actual else 0

                with str_app.form(f"form_config_{galpon_reg}"):
                    c_sem = str_app.number_input("Edad Inicial (Semanas)", min_value=0, value=int(ini_sem), step=1)
                    c_dias = str_app.number_input("Edad Inicial (Días adicionales 0-6)", min_value=0, max_value=6, value=int(ini_dias), step=1)
                    c_aves = str_app.number_input("Número de Aves Iniciales del Lote", min_value=0, value=int(ini_aves), step=10)

                    if str_app.form_submit_button("💾 Guardar Configuración del Galpón"):
                        if c_aves <= 0:
                            str_app.error("El número de aves iniciales debe ser mayor a 0.")
                        else:
                            if guardar_config_galpon(galpon_reg, c_sem, c_dias, c_aves):
                                str_app.toast("¡Registrado con éxito! 🎉", icon="✅")
                                str_app.success(f"¡Configuración de {galpon_reg} guardada con éxito!")
                                str_app.rerun()

            with tab_diario:
                if rol_actual == "Invitado":
                    str_app.warning("👀 Modo Invitado: No tienes permisos para registrar datos diarios.")
                else:
                    config = cargar_config_galpon(galpon_reg)
                    if not config:
                        str_app.warning("⚠️ Primero debes configurar la Edad y Aves Iniciales en la pestaña 'Configuración Inicial'.")
                    else:
                        with str_app.form(f"form_reg_diario_{galpon_reg}"):
                            fecha_reg = str_app.date_input("Fecha del Registro", value=date.today())
                            mortalidad = str_app.number_input("Mortalidad del Día (Aves muertas)", min_value=0, value=0, step=1)
                            conc_ing = str_app.number_input("Concentrado Ingresado (Bultos)", min_value=0.0, value=0.0, step=0.5, format="%g")
                            conc_cons = str_app.number_input("Concentrado Consumido (Bultos)", min_value=0.0, value=0.0, step=0.5, format="%g")
                            huevos = str_app.number_input("Huevos Recolectados (Opcional)", min_value=0, value=0, step=1)
                            obs = str_app.text_input("Observaciones / Novedades")

                            if str_app.form_submit_button("📥 Guardar Registro Diario"):
                                if registrar_dia_galpon(fecha_reg, galpon_reg, int(mortalidad), float(conc_ing), float(conc_cons), int(huevos), obs):
                                    str_app.toast("¡Registrado con éxito! 🎉", icon="✅")
                                    str_app.success(f"¡Registro diario guardado para {galpon_reg}! La edad y el stock de aves se han actualizado automáticamente.")
                                    str_app.rerun()

            with tab_historial:
                str_app.markdown(f"#### 📊 Resumen y Registros de {galpon_reg}")
                config = cargar_config_galpon(galpon_reg)
                df_reg = cargar_registros_diarios(galpon_reg)

                if not config:
                    str_app.info("Galpón sin configuración inicial.")
                else:
                    dias_acumulados = len(df_reg)
                    total_dias_calc = config['edad_dias'] + dias_acumulados
                    semanas_extra = total_dias_calc // 7
                    dias_finales = total_dias_calc % 7
                    edad_actual_sem = config['edad_semanas'] + semanas_extra
                    edad_actual_str = f"{edad_actual_sem} semanas y {dias_finales} días"

                    total_mortalidad = int(df_reg['mortalidad'].sum()) if not df_reg.empty else 0
                    aves_actuales = config['aves_iniciales'] - total_mortalidad
                    porc_mortalidad_acum = (total_mortalidad / config['aves_iniciales'] * 100) if config['aves_iniciales'] > 0 else 0.0

                    total_conc_ing = float(df_reg['concentrado_ingresado'].sum()) if not df_reg.empty else 0.0
                    total_conc_cons = float(df_reg['concentrado_consumido'].sum()) if not df_reg.empty else 0.0
                    saldo_concentrado = total_conc_ing - total_conc_cons
                    total_huevos_lote = int(df_reg['huevos_recolectados'].sum()) if not df_reg.empty else 0

                    # Conversión alimenticia aproximada: bultos de concentrado consumidos
                    # por cada 100 huevos producidos en la vida del lote (métrica típica
                    # de seguimiento avícola para vigilar eficiencia del alimento).
                    conversion_bultos_100h = (total_conc_cons / (total_huevos_lote / 100)) if total_huevos_lote > 0 else None

                    porc_prod_semana = 0.0
                    if not df_reg.empty and 'huevos_recolectados' in df_reg.columns:
                        df_ultimos_7 = df_reg.head(7)
                        total_huevos_7d = df_ultimos_7['huevos_recolectados'].sum()
                        dias_conteo = len(df_ultimos_7)
                        if dias_conteo > 0 and aves_actuales > 0:
                            promedio_diario_huevos = total_huevos_7d / dias_conteo
                            porc_prod_semana = (promedio_diario_huevos / aves_actuales) * 100

                    conversion_str = f"{conversion_bultos_100h:.2f} bultos / 100 huevos" if conversion_bultos_100h is not None else "Sin datos de huevos aún"

                    str_app.markdown(f"""
                        <div style="background-color: #1a3e63; color: white; padding: 15px; border-radius: 8px; margin-bottom: 15px; border-left: 5px solid #f26822;">
                            <p style="margin: 0; font-size: 16px; color: #f26822 !important;"><b>Edad Actual del Lote:</b> {edad_actual_str}</p>
                            <p style="margin: 0; font-size: 14px;">Aves Iniciales: {config['aves_iniciales']:,} | Mortalidad Acumulada: {total_mortalidad} ({porc_mortalidad_acum:.2f}%)</p>
                            <p style="margin: 0; font-size: 15px; color: #f26822 !important;"><b>Aves Vivas Actuales:</b> {aves_actuales:,}</p>
                            <p style="margin: 0; font-size: 15px; color: #f26822 !important;"><b>% Producción Acumulado (Últimos 7 días):</b> {porc_prod_semana:.2f}%</p>
                            <hr style="border-color: #2c5282; margin: 8px 0;">
                            <p style="margin: 0; font-size: 14px;">Concentrado Ingresado: {total_conc_ing:.1f} bultos | Consumido: {total_conc_cons:.1f} bultos</p>
                            <p style="margin: 0; font-size: 15px; color: #2c5282 !important;"><b>Saldo Concentrado Bodega:</b> {saldo_concentrado:.1f} bultos</p>
                            <p style="margin: 0; font-size: 14px;"><b>Conversión Alimenticia:</b> {conversion_str}</p>
                        </div>
                    """, unsafe_allow_html=True)

                    if porc_mortalidad_acum >= 5:
                        str_app.warning(f"⚠️ La mortalidad acumulada de {galpon_reg} ({porc_mortalidad_acum:.1f}%) está en un nivel que conviene revisar.")

                    if not df_reg.empty:
                        df_tendencia_galpon = df_reg[["fecha", "huevos_recolectados", "mortalidad"]].sort_values("fecha").set_index("fecha")
                        str_app.line_chart(df_tendencia_galpon)

                        c_pdf, c_xls = str_app.columns(2)
                        with c_pdf:
                            pdf_buf = generar_pdf_registro_diario(galpon_reg, config, df_reg, edad_actual_str, aves_actuales, saldo_concentrado)
                            str_app.download_button(f"📄 Descargar Reporte PDF de {galpon_reg}", data=pdf_buf, file_name=f"Registro_Diario_{galpon_reg.replace(' ', '_')}.pdf", mime="application/pdf")
                        with c_xls:
                            boton_exportar_excel(df_reg, f"Registro_Diario_{galpon_reg.replace(' ', '_')}.xlsx")

                        str_app.markdown("---")
                        str_app.markdown("#### 📑 Detalle Histórico de Registros")
                        for _, row in df_reg.iterrows():
                            r_id = row['id']
                            r_fecha = str(row['fecha'])
                            r_mort = int(row['mortalidad'])
                            r_ing = float(row['concentrado_ingresado'])
                            r_cons = float(row['concentrado_consumido'])
                            r_hue = int(row['huevos_recolectados'])
                            r_obs = row['observaciones']

                            with str_app.expander(f"📅 {r_fecha} | Mortalidad: {r_mort} | Conc. Consumido: {r_cons} bultos"):
                                str_app.write(f"**Concentrado Ingresado:** {r_ing} bultos")
                                str_app.write(f"**Huevos Recolectados:** {r_hue}")
                                str_app.write(f"**Observaciones:** {r_obs}")
                                if rol_actual == "Administrador":
                                    if confirmar_eliminacion(f"reg_{r_id}", etiqueta="🗑️ Eliminar Registro"):
                                        eliminar_registro_diario(r_id)
                                        str_app.warning("Registro diario eliminado y cálculos actualizados.")
                                        str_app.rerun()
                    else:
                        str_app.info("No hay registros diarios ingresados todavía para este galpón.")

    except psycopg2.Error as e:
        str_app.error("⚠️ Ocurrió un problema de conexión con la base de datos. Intenta de nuevo en unos segundos.")
        with str_app.expander("Detalle técnico"):
            str_app.code(str(e))
        if str_app.button("🔄 Reintentar"):
            str_app.rerun()
    except Exception as e:
        str_app.error("⚠️ Ocurrió un error inesperado al procesar esta sección.")
        with str_app.expander("Detalle técnico"):
            str_app.code(str(e))
        if str_app.button("🔄 Reintentar", key="reintentar_general"):
            str_app.rerun()
import psycopg2
from psycopg2 import pool as pg_pool
import os
import time
from datetime import datetime, date
from functools import wraps
from contextlib import contextmanager
import io
import base64
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

# =========================================================================
# CONFIGURACIÓN DE PÁGINA
# =========================================================================
str_app.set_page_config(
    page_title="Avícola Santa Isabel",
    page_icon="🥚",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# --- ICONO PERSONALIZADO (FAVICON) ---
if os.path.exists("LOGOASI.png"):
    with open("LOGOASI.png", "rb") as f:
        b64_svg = base64.b64encode(f.read()).decode('utf-8')
    data_uri = f"data:image/png;base64,{b64_svg}"
else:
    svg_huevo = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><rect width="100" height="100" rx="20" fill="#0f2942"/><text x="50" y="68" font-size="65" text-anchor="middle">🥚</text></svg>"""
    b64_svg = base64.b64encode(svg_huevo.encode('utf-8')).decode('utf-8')
    data_uri = f"data:image/svg+xml;base64,{b64_svg}"

str_app.markdown(f"""
    <script>
        var doc = window.parent.document;
        var oldIcons = doc.querySelectorAll("link[rel*='icon'], link[rel*='apple']");
        oldIcons.forEach(function(el) {{ el.remove(); }});
        var appleIcon = doc.createElement('link');
        appleIcon.rel = 'apple-touch-icon';
        appleIcon.href = '{data_uri}';
        doc.head.appendChild(appleIcon);
        var icon = doc.createElement('link');
        icon.rel = 'icon';
        icon.type = 'image/x-icon';
        icon.href = '{data_uri}';
        doc.head.appendChild(icon);
    </script>
""", unsafe_allow_html=True)

# --- ESTILOS CSS ---
str_app.markdown(
    """
    <style>
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}

    .stApp { background-color: #c8d6e5 !important; }

    .block-container {
        padding-top: 1.5rem; padding-bottom: 5rem;
        padding-left: 1.2rem; padding-right: 1.2rem;
        max-width: 540px;
        background-color: #0f2942 !important;
        border-radius: 16px;
        box-shadow: 0 10px 35px rgba(15, 41, 66, 0.3);
        margin-top: 1rem; margin-bottom: 2rem;
        border: 1px solid #1a3e63;
    }

    /* Botones principales y de envío */
    .stButton>button, div.stFormSubmitButton>button {
        width: 100% !important; border-radius: 10px !important; height: 3.2em !important;
        font-weight: 650 !important; background-color: #f26822 !important;
        color: white !important; border: 2px solid #ffffff !important;
    }

    .stButton>button p, .stButton>button span, div.stFormSubmitButton>button p, div.stFormSubmitButton>button span {
        color: white !important;
    }

    .stButton>button:hover, div.stFormSubmitButton>button:hover {
        background-color: #ffffff !important;
        border-color: #f26822 !important;
    }

    .stButton>button:hover p, .stButton>button:hover span, div.stFormSubmitButton>button:hover p, div.stFormSubmitButton>button:hover span {
        color: #f26822 !important;
    }

    /* Textos generales del contenedor */
    .block-container h1, .block-container h2, .block-container h3, .block-container h4, .block-container p {
        color: #ffffff;
    }

    /* Estilo armónico para los Expander (Historial / Remisiones) */
    [data-testid="stExpander"] {
        background-color: #163559 !important;
        border-radius: 8px !important;
        border: 1px solid #244c7c !important;
    }

    [data-testid="stExpander"] summary p, [data-testid="stExpander"] summary span {
        color: #ffffff !important;
        font-weight: bold !important;
    }

    [data-testid="stExpanderDetails"] {
        color: #ffffff !important;
    }

    /* Etiquetas de los campos */
    .stTextInput label, .stNumberInput label, .stSelectbox label, .stDateInput label, .stFileUploader label {
        color: #ffffff !important;
    }

    [data-testid="stMetric"] {
        background-color: #163559 !important;
        border-radius: 8px !important;
        border: 1px solid #244c7c !important;
        padding: 10px !important;
    }
    [data-testid="stMetricLabel"] p { color: #cbd5e1 !important; }
    [data-testid="stMetricValue"] { color: #ffffff !important; }

    .stSubheader { color: #f26822 !important; font-weight: bold !important; }
    </style>
    """,
    unsafe_allow_html=True
)

# =========================================================================
# CONSTANTES DE NEGOCIO
# (Centralizadas aquí: si mañana abren un Galpón 4, solo se edita esta lista)
# =========================================================================
GALPONES = ["Galpón 1", "Galpón 2", "Galpón 3"]
GALPONES_GASTOS = GALPONES + ["General / Granja"]
CLASIFICACIONES = ["yumbo", "extra", "aa", "a", "b", "c", "sucio", "roto","palido"]
COLUMNAS_INVENTARIO = set(CLASIFICACIONES)
MESES_NOMBRES = {1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril', 5: 'Mayo', 6: 'Junio',
                  7: 'Julio', 8: 'Agosto', 9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'}
CATEGORIAS_GASTO_GALPON = ["Alimento", "Medicamentos / Sanidad", "Personal / Mano de Obra",
                            "Mantenimiento / Reparaciones", "Servicios Públicos", "Otros"]
CATEGORIAS_GASTO_VARIO = ["Personal", "Hogar", "Vehículo", "Impuestos", "Varios"]

NOMBRE_EMPRESA = "AGROAVICOLA SANTA ISABEL"
NIT_EMPRESA = "NIT. 901.786.799-7"
TELEFONOS_EMPRESA = "Cel. 3102397244 - 3125588606"


# =========================================================================
# CAPA DE BASE DE DATOS
# Se usa un pool de conexiones (en vez de abrir/cerrar una conexión nueva
# en cada consulta) y decoradores que atrapan errores de PostgreSQL para
# que nunca se vea un traceback crudo en pantalla.
# =========================================================================
@str_app.cache_resource(show_spinner=False)
def _obtener_pool():
    return pg_pool.SimpleConnectionPool(1, 10, str_app.secrets["postgres"]["url"])


@contextmanager
def get_conn():
    """Presta una conexión del pool y siempre la devuelve al terminar."""
    conexiones = _obtener_pool()
    conn = conexiones.getconn()
    try:
        yield conn
    finally:
        conexiones.putconn(conn)


def ejecutar(sql, params=None):
    """Ejecuta una sentencia de escritura (INSERT/UPDATE/DELETE/DDL) como una
    transacción atómica: si algo falla, se revierte todo automáticamente."""
    with get_conn() as conn:
        with conn:
            with conn.cursor() as cur:
                cur.execute(sql, params or ())


def consultar_uno(sql, params=None):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params or ())
            return cur.fetchone()


def leer_df(sql, params=None):
    with get_conn() as conn:
        return pd.read_sql_query(sql, conn, params=params)


def operacion_segura(func):
    """Decorador para funciones que ESCRIBEN en la base de datos.
    Atrapa errores de PostgreSQL y los muestra de forma amigable en vez de
    tumbar la app. Las validaciones de negocio (ValueError) se dejan pasar
    para que la pantalla que llamó pueda mostrar su propio mensaje."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            resultado = func(*args, **kwargs)
            return True if resultado is None else resultado
        except ValueError:
            raise
        except psycopg2.Error as e:
            str_app.error(f"⚠️ No se pudo guardar la información en la base de datos.\n\nDetalle: {e}")
            return False
    return wrapper


def lectura_segura(func):
    """Decorador para funciones que LEEN de la base de datos. Si la consulta
    falla, se devuelve una tabla vacía en vez de romper la página."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except psycopg2.Error as e:
            str_app.error(f"⚠️ No se pudieron cargar los datos.\n\nDetalle: {e}")
            return pd.DataFrame()
    return wrapper


# --- CREACIÓN DE TABLAS (se ejecuta una sola vez por sesión, no en cada clic) ---
def inicializar_todas_las_tablas():
    ejecutar("""
        CREATE TABLE IF NOT EXISTS clientes (
            id SERIAL PRIMARY KEY,
            nombre TEXT UNIQUE NOT NULL,
            cedula_nit TEXT,
            direccion TEXT,
            telefono TEXT,
            email TEXT
        );
    """)
    ejecutar("""
        CREATE TABLE IF NOT EXISTS inventario (
            galpon TEXT PRIMARY KEY,
            yumbo INT DEFAULT 0, extra INT DEFAULT 0, aa INT DEFAULT 0, a INT DEFAULT 0,
            b INT DEFAULT 0, c INT DEFAULT 0, sucio INT DEFAULT 0, roto INT DEFAULT 0
        );
    """)
    for g in GALPONES:
        ejecutar("INSERT INTO inventario (galpon) VALUES (%s) ON CONFLICT (galpon) DO NOTHING;", (g,))
    ejecutar("""
        CREATE TABLE IF NOT EXISTS remisiones (
            id SERIAL PRIMARY KEY,
            num_remision INT, fecha_emision DATE, cliente TEXT, cedula_nit TEXT,
            telefono TEXT, destino TEXT, email TEXT, conductor TEXT, tipo_huevo TEXT,
            cantidad INT, precio_unitario NUMERIC, total NUMERIC, galpon TEXT
        );
    """)
    ejecutar("""
        CREATE TABLE IF NOT EXISTS cartera (
            num_remision INT PRIMARY KEY, cliente TEXT, total NUMERIC, saldo NUMERIC,
            estado TEXT DEFAULT 'PENDIENTE'
        );
    """)
    ejecutar("""
        CREATE TABLE IF NOT EXISTS abonos_cartera (
            id SERIAL PRIMARY KEY, num_remision INT, fecha_abono TIMESTAMP, monto NUMERIC,
            comprobante BYTEA, nombre_comprobante TEXT
        );
    """)
    ejecutar("""
        CREATE TABLE IF NOT EXISTS gastos (
            id SERIAL PRIMARY KEY, fecha DATE, galpon TEXT, categoria TEXT,
            descripcion TEXT, valor NUMERIC
        );
    """)
    ejecutar("""
        CREATE TABLE IF NOT EXISTS gastos_varios (
            id SERIAL PRIMARY KEY, fecha DATE, categoria TEXT, descripcion TEXT, valor NUMERIC
        );
    """)
    ejecutar("""
        CREATE TABLE IF NOT EXISTS galpon_config (
            galpon TEXT PRIMARY KEY, edad_semanas INT DEFAULT 0, edad_dias INT DEFAULT 0,
            aves_iniciales INT DEFAULT 0
        );
    """)
    ejecutar("""
        CREATE TABLE IF NOT EXISTS registros_diarios (
            id SERIAL PRIMARY KEY, fecha DATE, galpon TEXT, mortalidad INT DEFAULT 0,
            concentrado_ingresado NUMERIC DEFAULT 0, concentrado_consumido NUMERIC DEFAULT 0,
            huevos_recolectados INT DEFAULT 0, observaciones TEXT
        );
    """)
    ejecutar("""
        CREATE TABLE IF NOT EXISTS historial_entradas (
            id SERIAL PRIMARY KEY, fecha DATE, galpon TEXT, clasificacion TEXT, cantidad INT
        );
    """)


def asegurar_tablas():
    """Solo corre las sentencias CREATE TABLE una vez por sesión de usuario,
    en vez de en cada clic como hacía la versión anterior."""
    if not str_app.session_state.get("_tablas_listas", False):
        inicializar_todas_las_tablas()
        str_app.session_state["_tablas_listas"] = True


# --- CLIENTES ---
@operacion_segura
def guardar_cliente(nombre, cedula, direccion, telefono, email):
    ejecutar("""
        INSERT INTO clientes (nombre, cedula_nit, direccion, telefono, email)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (nombre) DO UPDATE SET
            cedula_nit = EXCLUDED.cedula_nit, direccion = EXCLUDED.direccion,
            telefono = EXCLUDED.telefono, email = EXCLUDED.email;
    """, (nombre.strip().upper(), cedula, direccion, telefono, email))


@operacion_segura
def eliminar_cliente(cliente_id):
    ejecutar("DELETE FROM clientes WHERE id = %s", (cliente_id,))


@lectura_segura
def cargar_clientes():
    return leer_df("SELECT * FROM clientes ORDER BY nombre ASC")


# --- INVENTARIO ---
@lectura_segura
def cargar_inventario():
    df = leer_df("SELECT * FROM inventario ORDER BY galpon")
    return df.set_index('galpon')


@operacion_segura
def registrar_entrada_inventario(galpon, items_entrada, fecha_entrada):
    with get_conn() as conn:
        with conn:
            with conn.cursor() as cur:
                for item in items_entrada:
                    clasificacion = item['Clasificación'].lower()
                    if clasificacion not in COLUMNAS_INVENTARIO:
                        raise ValueError(f"Clasificación inválida: {clasificacion}")
                    cantidad = int(item['Cantidad'])
                    cur.execute(f"UPDATE inventario SET {clasificacion} = {clasificacion} + %s WHERE galpon = %s", (cantidad, galpon))
                    cur.execute(
                        "INSERT INTO historial_entradas (fecha, galpon, clasificacion, cantidad) VALUES (%s, %s, %s, %s)",
                        (fecha_entrada, galpon, clasificacion, cantidad)
                    )


@lectura_segura
def cargar_historial_entradas(galpon=None):
    if galpon:
        df = leer_df("SELECT * FROM historial_entradas WHERE galpon = %s ORDER BY fecha DESC, id DESC", (galpon,))
    else:
        df = leer_df("SELECT * FROM historial_entradas ORDER BY fecha DESC, id DESC")
    if not df.empty:
        df['fecha'] = pd.to_datetime(df['fecha']).dt.date
    return df


@operacion_segura
def actualizar_inventario_fisico(galpon, nuevo_stock_dict):
    ejecutar("""
        UPDATE inventario SET
            yumbo = %s, extra = %s, aa = %s, a = %s, b = %s, c = %s, sucio = %s, roto = %s, palido = %s
        WHERE galpon = %s
    """, (
        nuevo_stock_dict.get('yumbo', 0), nuevo_stock_dict.get('extra', 0), nuevo_stock_dict.get('aa', 0),
        nuevo_stock_dict.get('a', 0), nuevo_stock_dict.get('b', 0), nuevo_stock_dict.get('c', 0),
        nuevo_stock_dict.get('sucio', 0), nuevo_stock_dict.get('roto', 0),nuevo_stock_dict.get('palido', 0), galpon
    ))


# --- REMISIONES / VENTAS ---
@lectura_segura
def cargar_remisiones():
    df = leer_df("SELECT * FROM remisiones ORDER BY id DESC")
    if not df.empty:
        if 'num_remision' not in df.columns:
            df['num_remision'] = df['id']
        if 'fecha_emision' in df.columns:
            df['fecha_emision'] = pd.to_datetime(df['fecha_emision']).dt.date
    return df


def obtener_siguiente_num_remision():
    try:
        res = consultar_uno("SELECT MAX(num_remision) FROM remisiones;")
        if res and res[0] is not None:
            return max(int(res[0]) + 1, 192)
    except psycopg2.Error:
        pass
    return 192


@operacion_segura
def registrar_venta_multiple(cliente, cedula, direccion, telefono, email, conductor, num_remision, fecha_remision, items_venta):
    # Se acumula lo pedido por (galpón, clasificación) ANTES de validar contra el
    # stock real, para no dejar pasar una remisión con dos filas del mismo huevo
    # que individualmente caben pero juntas superan el stock disponible.
    requerido = {}
    for item in items_venta:
        clasificacion = item['Clasificación'].lower()
        if clasificacion not in COLUMNAS_INVENTARIO:
            raise ValueError(f"Clasificación inválida: {clasificacion}")
        galp_origen = item.get('Galpón', GALPONES[0])
        clave = (galp_origen, clasificacion)
        requerido[clave] = requerido.get(clave, 0) + int(item['Cantidad (Huevos)'])

    with get_conn() as conn:
        with conn:
            with conn.cursor() as cur:
                for (galp_origen, clasificacion), cantidad_total in requerido.items():
                    cur.execute(f"SELECT {clasificacion} FROM inventario WHERE galpon = %s", (galp_origen,))
                    res = cur.fetchone()
                    stock_actual = res[0] if res else 0
                    if cantidad_total > stock_actual:
                        raise ValueError(
                            f"Stock insuficiente de '{clasificacion.upper()}' en {galp_origen}. "
                            f"Stock actual: {stock_actual:,}, solicitado: {cantidad_total:,}".replace(",", ".")
                        )

                cur.execute("""
                    SELECT column_name, is_generated, identity_generation
                    FROM information_schema.columns WHERE table_name = 'remisiones';
                """)
                columnas_validas = {c for c, is_gen, id_gen in cur.fetchall() if is_gen != 'ALWAYS' and id_gen != 'ALWAYS'}

                total_venta_acumulado = 0.0
                for item in items_venta:
                    clasificacion = item['Clasificación'].lower()
                    cantidad = int(item['Cantidad (Huevos)'])
                    subtotal = float(item['Subtotal ($)'])
                    precio_u = float(item['Precio Unitario ($)'])
                    galp_origen = item.get('Galpón', GALPONES[0])
                    total_venta_acumulado += subtotal

                    datos_insert = {
                        "num_remision": num_remision, "fecha_emision": fecha_remision,
                        "cliente": cliente, "cedula_nit": cedula, "telefono": telefono,
                        "destino": direccion, "email": email, "conductor": conductor,
                        "tipo_huevo": clasificacion, "cantidad": cantidad,
                        "precio_unitario": precio_u, "total": subtotal, "galpon": galp_origen
                    }
                    datos_reales = {k: v for k, v in datos_insert.items() if k in columnas_validas}
                    if datos_reales:
                        cols = ", ".join(datos_reales.keys())
                        vals = tuple(datos_reales.values())
                        placeholders = ", ".join(["%s"] * len(datos_reales))
                        cur.execute(f"INSERT INTO remisiones ({cols}) VALUES ({placeholders})", vals)

                    cur.execute(f"UPDATE inventario SET {clasificacion} = {clasificacion} - %s WHERE galpon = %s", (cantidad, galp_origen))

                cur.execute("""
                    INSERT INTO cartera (num_remision, cliente, total, saldo, estado)
                    VALUES (%s, %s, %s, %s, 'PENDIENTE')
                    ON CONFLICT (num_remision) DO UPDATE SET
                        cliente = EXCLUDED.cliente, total = EXCLUDED.total, saldo = EXCLUDED.saldo;
                """, (num_remision, cliente.strip().upper(), total_venta_acumulado, total_venta_acumulado))


# --- CARTERA ---
@lectura_segura
def cargar_cartera():
    return leer_df("SELECT * FROM cartera ORDER BY num_remision DESC")


@lectura_segura
def cargar_abonos_remision(num_remision):
    return leer_df("SELECT * FROM abonos_cartera WHERE num_remision = %s ORDER BY fecha_abono DESC", (num_remision,))


@operacion_segura
def registrar_abono(num_remision, monto_abono, comprobante_bytes=None, nombre_comprobante=None):
    with get_conn() as conn:
        with conn:
            with conn.cursor() as cur:
                fecha_actual = datetime.now()
                comp_binary = psycopg2.Binary(comprobante_bytes) if comprobante_bytes else None
                cur.execute("""
                    INSERT INTO abonos_cartera (num_remision, fecha_abono, monto, comprobante, nombre_comprobante)
                    VALUES (%s, %s, %s, %s, %s)
                """, (num_remision, fecha_actual, monto_abono, comp_binary, nombre_comprobante))

                cur.execute("SELECT total FROM cartera WHERE num_remision = %s", (num_remision,))
                res = cur.fetchone()
                if res:
                    total = float(res[0])
                    cur.execute("SELECT COALESCE(SUM(monto), 0) FROM abonos_cartera WHERE num_remision = %s", (num_remision,))
                    total_abonos = float(cur.fetchone()[0])
                    nuevo_saldo = max(0.0, total - total_abonos)
                    nuevo_estado = 'PAGADA' if nuevo_saldo <= 0 else 'PENDIENTE'
                    cur.execute("UPDATE cartera SET saldo = %s, estado = %s WHERE num_remision = %s", (nuevo_saldo, nuevo_estado, num_remision))


# --- GASTOS ---
@operacion_segura
def registrar_gasto(fecha, galpon, categoria, descripcion, valor):
    ejecutar("INSERT INTO gastos (fecha, galpon, categoria, descripcion, valor) VALUES (%s, %s, %s, %s, %s)",
              (fecha, galpon, categoria, descripcion, valor))


@lectura_segura
def cargar_gastos():
    df = leer_df("SELECT * FROM gastos ORDER BY fecha DESC, id DESC")
    if not df.empty:
        df['fecha'] = pd.to_datetime(df['fecha']).dt.date
    return df


@operacion_segura
def eliminar_gasto(gasto_id):
    ejecutar("DELETE FROM gastos WHERE id = %s", (gasto_id,))


@operacion_segura
def registrar_gasto_vario(fecha, categoria, descripcion, valor):
    ejecutar("INSERT INTO gastos_varios (fecha, categoria, descripcion, valor) VALUES (%s, %s, %s, %s)",
              (fecha, categoria, descripcion, valor))


@lectura_segura
def cargar_gastos_varios():
    df = leer_df("SELECT * FROM gastos_varios ORDER BY fecha DESC, id DESC")
    if not df.empty:
        df['fecha'] = pd.to_datetime(df['fecha']).dt.date
    return df


@operacion_segura
def eliminar_gasto_vario(gasto_id):
    ejecutar("DELETE FROM gastos_varios WHERE id = %s", (gasto_id,))


# --- REGISTRO DIARIO ---
@operacion_segura
def guardar_config_galpon(galpon, semanas, dias, aves):
    ejecutar("""
        INSERT INTO galpon_config (galpon, edad_semanas, edad_dias, aves_iniciales)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (galpon) DO UPDATE SET
            edad_semanas = EXCLUDED.edad_semanas, edad_dias = EXCLUDED.edad_dias,
            aves_iniciales = EXCLUDED.aves_iniciales;
    """, (galpon, semanas, dias, aves))


def cargar_config_galpon(galpon):
    try:
        res = consultar_uno("SELECT edad_semanas, edad_dias, aves_iniciales FROM galpon_config WHERE galpon = %s", (galpon,))
    except psycopg2.Error as e:
        str_app.error(f"⚠️ No se pudo cargar la configuración del galpón.\n\nDetalle: {e}")
        return None
    if res:
        return {"edad_semanas": res[0], "edad_dias": res[1], "aves_iniciales": res[2]}
    return None


@operacion_segura
def registrar_dia_galpon(fecha, galpon, mortalidad, conc_ingresado, conc_consumido, huevos, observaciones):
    ejecutar("""
        INSERT INTO registros_diarios (fecha, galpon, mortalidad, concentrado_ingresado, concentrado_consumido, huevos_recolectados, observaciones)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (fecha, galpon, mortalidad, conc_ingresado, conc_consumido, huevos, observaciones))


@lectura_segura
def cargar_registros_diarios(galpon=None):
    if galpon:
        df = leer_df("SELECT * FROM registros_diarios WHERE galpon = %s ORDER BY fecha DESC, id DESC", (galpon,))
    else:
        df = leer_df("SELECT * FROM registros_diarios ORDER BY fecha DESC, id DESC")
    if not df.empty:
        df['fecha'] = pd.to_datetime(df['fecha']).dt.date
    return df


@operacion_segura
def eliminar_registro_diario(reg_id):
    ejecutar("DELETE FROM registros_diarios WHERE id = %s", (reg_id,))


# --- REINICIO TOTAL DEL SISTEMA ---
@operacion_segura
def reiniciar_sistema_completo():
    tablas_a_limpiar = ["abonos_cartera", "cartera", "remisiones", "clientes", "gastos",
                         "gastos_varios", "registros_diarios", "galpon_config", "historial_entradas"]
    for tabla in tablas_a_limpiar:
        try:
            ejecutar(f"TRUNCATE TABLE {tabla} RESTART IDENTITY CASCADE;")
        except psycopg2.Error:
            ejecutar(f"DELETE FROM {tabla};")
    ejecutar("UPDATE inventario SET yumbo = 0, extra = 0, aa = 0, a = 0, b = 0, c = 0, sucio = 0, roto = 0; palido = 0;")


# =========================================================================
# RESUMEN GENERAL (DASHBOARD)
# =========================================================================
def calcular_resumen_general():
    resumen = {
        "stock_total": 0, "cartera_pendiente": 0.0, "produccion_hoy": 0,
        "mortalidad_mes": 0, "gastos_mes": 0.0, "ventas_mes": 0.0,
        "stock_por_galpon": {g: 0 for g in GALPONES},
        "produccion_por_galpon": {g: 0 for g in GALPONES},
        "mortalidad_por_galpon": {g: 0 for g in GALPONES},
    }
    hoy = date.today()
    inicio_mes = pd.Timestamp(hoy.replace(day=1))

    df_inv = cargar_inventario()
    if not df_inv.empty:
        cols_presentes = [c for c in COLUMNAS_INVENTARIO if c in df_inv.columns]
        resumen["stock_total"] = int(df_inv[cols_presentes].sum().sum())
        for g in GALPONES:
            if g in df_inv.index:
                resumen["stock_por_galpon"][g] = int(df_inv.loc[g, cols_presentes].sum())

    df_cartera = cargar_cartera()
    if not df_cartera.empty and "estado" in df_cartera.columns:
        resumen["cartera_pendiente"] = float(df_cartera[df_cartera["estado"] == "PENDIENTE"]["saldo"].sum())

    df_reg = cargar_registros_diarios()
    if not df_reg.empty:
        df_hoy = df_reg[df_reg["fecha"] == hoy]
        resumen["produccion_hoy"] = int(df_hoy["huevos_recolectados"].sum())
        if "galpon" in df_hoy.columns:
            for g in GALPONES:
                resumen["produccion_por_galpon"][g] = int(df_hoy[df_hoy["galpon"] == g]["huevos_recolectados"].sum())

        df_mes = df_reg[pd.to_datetime(df_reg["fecha"]) >= inicio_mes]
        resumen["mortalidad_mes"] = int(df_mes["mortalidad"].sum())
        if "galpon" in df_mes.columns:
            for g in GALPONES:
                resumen["mortalidad_por_galpon"][g] = int(df_mes[df_mes["galpon"] == g]["mortalidad"].sum())

    total_gastos_mes = 0.0
    df_gastos = cargar_gastos()
    if not df_gastos.empty:
        total_gastos_mes += float(df_gastos[pd.to_datetime(df_gastos["fecha"]) >= inicio_mes]["valor"].sum())
    df_gastos_v = cargar_gastos_varios()
    if not df_gastos_v.empty:
        total_gastos_mes += float(df_gastos_v[pd.to_datetime(df_gastos_v["fecha"]) >= inicio_mes]["valor"].sum())
    resumen["gastos_mes"] = total_gastos_mes

    df_rem = cargar_remisiones()
    if not df_rem.empty and "fecha_emision" in df_rem.columns and "total" in df_rem.columns:
        df_rem_mes = df_rem[pd.to_datetime(df_rem["fecha_emision"]) >= inicio_mes]
        resumen["ventas_mes"] = float(df_rem_mes["total"].sum())

    return resumen


def _fila_metrica_con_desglose(icono, titulo, valor_total, valores_por_galpon, es_moneda=False):
    """Muestra una métrica grande (ej. Stock Total) y, justo debajo, una fila
    con el mismo dato desglosado por cada uno de los galpones."""
    if es_moneda:
        texto_total = f"${valor_total:,.0f}".replace(",", ".")
    else:
        texto_total = f"{valor_total:,}".replace(",", ".")
    str_app.metric(f"{icono} {titulo}", texto_total)

    cols = str_app.columns(len(GALPONES))
    for col, g in zip(cols, GALPONES):
        valor_g = valores_por_galpon.get(g, 0)
        texto_g = f"${valor_g:,.0f}".replace(",", ".") if es_moneda else f"{valor_g:,}".replace(",", ".")
        col.markdown(
            f"<div style='text-align:center; background-color:#163559; border:1px solid #244c7c; "
            f"border-radius:8px; padding:6px 2px; margin-top:-8px;'>"
            f"<p style='margin:0; font-size:11px; color:#cbd5e1;'>{g}</p>"
            f"<p style='margin:0; font-size:14px; color:#ffffff; font-weight:bold;'>{texto_g}</p>"
            f"</div>", unsafe_allow_html=True
        )
    str_app.markdown("<div style='margin-bottom:12px;'></div>", unsafe_allow_html=True)


def mostrar_resumen_general():
    str_app.subheader("🏠 Resumen General")
    resumen = calcular_resumen_general()

    _fila_metrica_con_desglose("📦", "Stock Total", resumen["stock_total"], resumen["stock_por_galpon"])
    _fila_metrica_con_desglose("🥚", "Producción Hoy", resumen["produccion_hoy"], resumen["produccion_por_galpon"])
    _fila_metrica_con_desglose("💀", "Mortalidad del Mes", resumen["mortalidad_mes"], resumen["mortalidad_por_galpon"])

    str_app.markdown("---")
    c1, c2, c3 = str_app.columns(3)
    c1.metric("💰 Cartera Pendiente", f"${resumen['cartera_pendiente']:,.0f}".replace(",", "."))
    c2.metric("💸 Gastos del Mes", f"${resumen['gastos_mes']:,.0f}".replace(",", "."))
    c3.metric("📈 Ventas del Mes", f"${resumen['ventas_mes']:,.0f}".replace(",", "."))

    df_reg_all = cargar_registros_diarios()
    if not df_reg_all.empty:
        df_tendencia = df_reg_all.groupby("fecha")[["huevos_recolectados", "mortalidad"]].sum().reset_index()
        df_tendencia = df_tendencia.sort_values("fecha").tail(14).set_index("fecha")
        if not df_tendencia.empty:
            str_app.caption("📊 Producción y mortalidad — últimos 14 días con registro (todos los galpones)")
            str_app.line_chart(df_tendencia)

    str_app.markdown("---")


# =========================================================================
# UTILIDADES DE INTERFAZ (confirmaciones, exportación)
# =========================================================================
def confirmar_eliminacion(clave, etiqueta="🗑️ Eliminar", mensaje="¿Confirmas que deseas eliminar este registro? Esta acción no se puede deshacer."):
    """Botón de eliminar con doble confirmación para evitar borrados accidentales.
    Devuelve True únicamente en el momento en que el usuario confirma."""
    estado_key = f"confirmar_del_{clave}"
    if not str_app.session_state.get(estado_key, False):
        if str_app.button(etiqueta, key=f"btn_del_{clave}"):
            str_app.session_state[estado_key] = True
            str_app.rerun()
        return False

    str_app.warning(mensaje)
    c1, c2 = str_app.columns(2)
    confirmado = c1.button("✅ Sí, eliminar", key=f"si_del_{clave}", use_container_width=True)
    cancelado = c2.button("❌ Cancelar", key=f"no_del_{clave}", use_container_width=True)
    if cancelado:
        str_app.session_state[estado_key] = False
        str_app.rerun()
    if confirmado:
        str_app.session_state[estado_key] = False
    return confirmado


def boton_exportar_excel(df, nombre_archivo, etiqueta="📊 Descargar en Excel", key=None):
    if df is None or df.empty:
        return
    try:
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Datos")
        buffer.seek(0)
        str_app.download_button(etiqueta, data=buffer, file_name=nombre_archivo,
                                 mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key=key)
    except ImportError:
        str_app.caption("ℹ️ Instala 'openpyxl' en el servidor para habilitar la exportación a Excel.")


# =========================================================================
# GENERACIÓN DE PDF (estilos compartidos para no repetir código)
# =========================================================================
def _estilos_pdf():
    styles = getSampleStyleSheet()
    return {
        "normal": ParagraphStyle('NormalStyle', parent=styles['Normal'], fontName='Helvetica', fontSize=9, textColor=colors.HexColor("#333333")),
        "bold": ParagraphStyle('BoldStyle', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=9, textColor=colors.HexColor("#333333")),
        "right": ParagraphStyle('RightStyle', parent=styles['Normal'], fontName='Helvetica', fontSize=9, textColor=colors.HexColor("#333333"), alignment=2),
        "right_bold": ParagraphStyle('RightBoldStyle', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=9, textColor=colors.HexColor("#333333"), alignment=2),
        "th": ParagraphStyle('THStyle', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=9, textColor=colors.white, alignment=1),
        "th_left": ParagraphStyle('THLeftStyle', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=9, textColor=colors.white, alignment=0),
        "th_right": ParagraphStyle('THRightStyle', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=9, textColor=colors.white, alignment=2),
    }


def _logo_pdf(estilos):
    if os.path.exists("LOGOASI.png"):
        return Image("LOGOASI.png", width=70, height=70)
    return Paragraph("<b>🥚</b>", estilos["bold"])


def _moneda(valor):
    return f"$ {valor:,.0f}".replace(",", ".")


def _encabezado_pdf(estilos, subtitulo, texto_derecha):
    header_data = [[
        _logo_pdf(estilos),
        Paragraph(f"<b>{NOMBRE_EMPRESA}</b><br/><font size=8>{NIT_EMPRESA}<br/>{subtitulo}</font>", estilos["normal"]),
        Paragraph(texto_derecha, estilos["right"])
    ]]
    t_header = Table(header_data, colWidths=[80, 294, 160])
    t_header.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
    ]))
    return t_header


def generar_pdf_remision(num_remision, fecha_str, conductor, cliente_datos, items_df, total_factura):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    story = []
    e = _estilos_pdf()
    num_str = f"{num_remision:06d}"

    story.append(_encabezado_pdf(e, TELEFONOS_EMPRESA, f"<b>Remisión No.</b><br/><font size=13 color='#f26822'><b>{num_str}</b></font>"))
    story.append(Spacer(1, 10))

    info_data = [
        [Paragraph("<b>Fecha</b>", e["bold"]), Paragraph(f": {fecha_str}", e["normal"]), Paragraph("<b>Datos del cliente</b>", e["bold"]), ""],
        [Paragraph("<b>Conductor</b>", e["bold"]), Paragraph(f": {conductor}", e["normal"]), Paragraph("<b>Nombre / Razón Social</b>", e["bold"]), Paragraph(f": {cliente_datos['nombre']}", e["normal"])],
        [Paragraph("", e["normal"]), Paragraph("", e["normal"]), Paragraph("<b>Cédula / NIT</b>", e["bold"]), Paragraph(f": {cliente_datos['cedula']}", e["normal"])],
        [Paragraph("", e["normal"]), Paragraph("", e["normal"]), Paragraph("<b>Dirección</b>", e["bold"]), Paragraph(f": {cliente_datos['direccion']}", e["normal"])],
        [Paragraph("", e["normal"]), Paragraph("", e["normal"]), Paragraph("<b>Teléfono</b>", e["bold"]), Paragraph(f": {cliente_datos['telefono']}", e["normal"])],
        [Paragraph("", e["normal"]), Paragraph("", e["normal"]), Paragraph("<b>Email</b>", e["bold"]), Paragraph(f": {cliente_datos['email']}", e["normal"])],
    ]
    t_info = Table(info_data, colWidths=[70, 160, 110, 194])
    t_info.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP'), ('BOTTOMPADDING', (0, 0), (-1, -1), 3), ('TOPPADDING', (0, 0), (-1, -1), 3)]))
    story.append(t_info)
    story.append(Spacer(1, 15))

    table_data = [[
        Paragraph("Clasificación", e["th_left"]),
        Paragraph("Cantidad", e["th"]),
        Paragraph("Valor Unitario", e["th_right"]),
        Paragraph("Valor total", e["th_right"])
    ]]
    for _, fila in items_df.iterrows():
        table_data.append([
            Paragraph(str(fila["Clasificación"]).upper(), e["normal"]),
            Paragraph(f"{int(fila['Cantidad (Huevos)']):,}".replace(",", "."), e["right"]),
            Paragraph(_moneda(fila['Precio Unitario ($)']), e["right"]),
            Paragraph(_moneda(fila['Subtotal ($)']), e["right"])
        ])

    t_items = Table(table_data, colWidths=[140, 100, 130, 164])
    t_items.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#0f2942")),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6), ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor("#f8fafc"), colors.white]),
    ]))
    story.append(t_items)
    story.append(Spacer(1, 10))

    totales_data = [
        [Paragraph("<b>Subtotal</b>", e["right"]), Paragraph(f"<b>{_moneda(total_factura)}</b>", e["right_bold"])],
        [Paragraph("<b>IVA</b>", e["right"]), Paragraph("<b>$ 0</b>", e["right_bold"])],
        [Paragraph("<b>Total</b>", e["right"]), Paragraph(f"<b>{_moneda(total_factura)}</b>", e["right_bold"])]
    ]
    t_totales = Table(totales_data, colWidths=[374, 160])
    t_totales.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'RIGHT'), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 3), ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LINEABOVE', (0, 2), (-1, 2), 1, colors.HexColor("#0f2942")),
    ]))
    story.append(t_totales)

    doc.build(story)
    buffer.seek(0)
    return buffer


def generar_pdf_registro_diario(galpon_nombre, config, df_reg, current_edad_str, current_aves, saldo_conc):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    story = []
    e = _estilos_pdf()

    story.append(_encabezado_pdf(e, f"Reporte Registro Diario - {galpon_nombre}",
                                  f"<b>Fecha Reporte:</b><br/><font size=10 color='#f26822'><b>{datetime.now().strftime('%Y-%m-%d')}</b></font>"))
    story.append(Spacer(1, 10))

    aves_ini_val = config['aves_iniciales'] if config else 0
    resumen_data = [
        [Paragraph(f"<b>Edad Actual:</b> {current_edad_str}", e["normal"]), Paragraph(f"<b>Aves Actuales:</b> {current_aves:,}".replace(",", "."), e["normal"])],
        [Paragraph(f"<b>Aves Iniciales:</b> {aves_ini_val:,}".replace(",", "."), e["normal"]), Paragraph(f"<b>Saldo Concentrado:</b> {saldo_conc:,.1f} bultos", e["normal"])]
    ]
    t_resumen = Table(resumen_data, colWidths=[267, 267])
    t_resumen.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'), ('PADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(t_resumen)
    story.append(Spacer(1, 15))

    table_data = [[
        Paragraph("Fecha", e["th_left"]), Paragraph("Mortalidad", e["th"]),
        Paragraph("Ingreso Conc. (Bultos)", e["th_right"]), Paragraph("Consumo Conc. (Bultos)", e["th_right"]),
        Paragraph("Huevos", e["th_right"])
    ]]
    for _, fila in df_reg.iterrows():
        table_data.append([
            Paragraph(str(fila["fecha"]), e["normal"]),
            Paragraph(str(int(fila.get("mortalidad", 0))), e["right"]),
            Paragraph(f"{float(fila.get('concentrado_ingresado', 0)):.1f}", e["right"]),
            Paragraph(f"{float(fila.get('concentrado_consumido', 0)):.1f}", e["right"]),
            Paragraph(str(int(fila.get("huevos_recolectados", 0))), e["right"])
        ])

    t_items = Table(table_data, colWidths=[100, 90, 115, 115, 114])
    t_items.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#0f2942")),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5), ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor("#f8fafc"), colors.white]),
    ]))
    story.append(t_items)

    doc.build(story)
    buffer.seek(0)
    return buffer


def generar_pdf_gastos(df_gastos, titulo_reporte):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    story = []
    e = _estilos_pdf()

    story.append(_encabezado_pdf(e, titulo_reporte, f"<b>Fecha:</b><br/><font size=10 color='#f26822'><b>{datetime.now().strftime('%Y-%m-%d')}</b></font>"))
    story.append(Spacer(1, 15))

    table_data = [[
        Paragraph("Fecha", e["th_left"]), Paragraph("Galpón / Cat.", e["th_left"]),
        Paragraph("Categoría / Desc.", e["th_left"]), Paragraph("Valor ($)", e["th_right"])
    ]]

    total_gasto = 0.0
    for _, fila in df_gastos.iterrows():
        val = float(fila.get("valor", 0))
        total_gasto += val
        col2_val = str(fila.get("galpon", fila.get("categoria", "")))
        col3_val = str(fila.get("categoria", "")) if "galpon" in fila else str(fila.get("descripcion", ""))
        table_data.append([
            Paragraph(str(fila.get("fecha", "")), e["normal"]),
            Paragraph(col2_val, e["normal"]),
            Paragraph(col3_val, e["normal"]),
            Paragraph(_moneda(val), e["right"])
        ])

    t_items = Table(table_data, colWidths=[90, 110, 174, 160])
    t_items.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#0f2942")),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5), ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor("#f8fafc"), colors.white]),
    ]))
    story.append(t_items)
    story.append(Spacer(1, 10))

    totales_data = [[Paragraph("<b>Total Gastos</b>", e["right"]), Paragraph(f"<b>{_moneda(total_gasto)}</b>", e["right_bold"])]]
    t_totales = Table(totales_data, colWidths=[374, 160])
    t_totales.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'RIGHT'), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 3), ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LINEABOVE', (0, 0), (-1, 0), 1, colors.HexColor("#0f2942")),
    ]))
    story.append(t_totales)

    doc.build(story)
    buffer.seek(0)
    return buffer


# =========================================================================
# CONTROL DE SESIÓN Y AUTENTICACIÓN
# (Se dejan las contraseñas tal como estaban, a petición explícita del
# usuario. Sí se agregó un bloqueo temporal tras varios intentos fallidos
# para dificultar ataques de fuerza bruta desde la pantalla de login.)
# =========================================================================
if "usuario_autenticado" not in str_app.session_state:
    str_app.session_state.usuario_autenticado = None

PASS_ADMIN = "admin123"
PASS_INVITADO = "invitado123"

MAX_INTENTOS_LOGIN = 5
BLOQUEO_SEGUNDOS = 60

if str_app.session_state.usuario_autenticado is None:
    col_logo, col_tit = str_app.columns([1, 3.5])
    with col_logo:
        if os.path.exists("LOGOASI.png"):
            str_app.image("LOGOASI.png", width=110)
        else:
            str_app.markdown("<h1 style='margin: 0;'>🥚</h1>", unsafe_allow_html=True)
    with col_tit:
        str_app.markdown('<h2 style="margin: 0; color: #f26822 !important;">AVÍCOLA SANTA ISABEL</h2><p style="margin: 0;">CONTROL DE ACCESO</p>', unsafe_allow_html=True)

    str_app.markdown("---")
    str_app.subheader("🔒 Iniciar Sesión")

    intentos = str_app.session_state.get("intentos_fallidos", 0)
    bloqueado_hasta = str_app.session_state.get("bloqueado_hasta", 0)
    ahora = time.time()

    if intentos >= MAX_INTENTOS_LOGIN and ahora < bloqueado_hasta:
        segundos_restantes = int(bloqueado_hasta - ahora)
        str_app.error(f"🔒 Demasiados intentos fallidos. Intenta de nuevo en {segundos_restantes} segundos.")
    else:
        if ahora >= bloqueado_hasta:
            str_app.session_state["intentos_fallidos"] = 0

        tipo_usuario = str_app.selectbox("Seleccione el Tipo de Usuario", ["Administrador", "Invitado"])
        password_ingresada = str_app.text_input("Contraseña", type="password")

        if str_app.button("🚀 Ingresar al Sistema", use_container_width=True):
            clave_correcta = PASS_ADMIN if tipo_usuario == "Administrador" else PASS_INVITADO
            if password_ingresada == clave_correcta:
                str_app.session_state.usuario_autenticado = tipo_usuario
                str_app.session_state["intentos_fallidos"] = 0
                str_app.success(f"¡Bienvenido {tipo_usuario}!")
                str_app.rerun()
            else:
                str_app.session_state["intentos_fallidos"] = intentos + 1
                if str_app.session_state["intentos_fallidos"] >= MAX_INTENTOS_LOGIN:
                    str_app.session_state["bloqueado_hasta"] = time.time() + BLOQUEO_SEGUNDOS
                    str_app.error(f"🔒 Demasiados intentos fallidos. Intenta de nuevo en {BLOQUEO_SEGUNDOS} segundos.")
                else:
                    str_app.error(f"Contraseña de {tipo_usuario} incorrecta. Intento {str_app.session_state['intentos_fallidos']}/{MAX_INTENTOS_LOGIN}.")

else:
    asegurar_tablas()

    # --- ENCABEZADO ---
    col_logo, col_tit = str_app.columns([1, 3.5])
    with col_logo:
        if os.path.exists("LOGOASI.png"):
            str_app.image("LOGOASI.png", width=75)
        else:
            str_app.markdown("<h1 style='margin: 0;'>🥚</h1>", unsafe_allow_html=True)
    with col_tit:
        rol_actual = str_app.session_state.usuario_autenticado
        color_rol = "#f26822" if rol_actual == "Administrador" else "#3498db"
        str_app.markdown(f'<h2 style="margin: 0; color: #f26822 !important;">AVÍCOLA SANTA ISABEL</h2><p style="margin: 0;">Sesión: <b style="color: {color_rol};">{rol_actual}</b></p>', unsafe_allow_html=True)

    if str_app.button("🚪 Cerrar Sesión"):
        str_app.session_state.usuario_autenticado = None
        str_app.session_state.sesion_principal = None
        str_app.session_state.seccion_activa = None
        str_app.rerun()

    str_app.markdown("---")

    # Todo el contenido autenticado queda protegido por un manejador de
    # errores general: si la base de datos falla a mitad de una operación,
    # el usuario ve un mensaje claro con un botón de reintentar, en vez de
    # una pantalla rota.
    try:
        if "sesion_principal" not in str_app.session_state:
            str_app.session_state.sesion_principal = None

        if str_app.session_state.sesion_principal is None:
            mostrar_resumen_general()

            c_prin1, c_prin2 = str_app.columns(2)
            with c_prin1:
                if str_app.button("📦 Stock y Ventas", use_container_width=True):
                    str_app.session_state.sesion_principal = "📦 Stock y Ventas"
                    str_app.session_state.seccion_activa = None
                    str_app.rerun()
            with c_prin2:
                if str_app.button("📝 Registro Diario", use_container_width=True):
                    str_app.session_state.sesion_principal = "📝 Registro Diario"
                    str_app.rerun()

            if rol_actual == "Administrador":
                str_app.markdown("---")
                if "confirmar_reinicio" not in str_app.session_state:
                    str_app.session_state.confirmar_reinicio = False

                if not str_app.session_state.confirmar_reinicio:
                    if str_app.button("🧹 Reiniciar Sistema (Dejar en Ceros)", use_container_width=True):
                        str_app.session_state.confirmar_reinicio = True
                        str_app.rerun()
                else:
                    str_app.warning("⚠️ ¿Estás completamente seguro? Esto borrará todas las remisiones, abonos, clientes, gastos, registros diarios y pondrá el stock en 0.")
                    c_conf1, c_conf2 = str_app.columns(2)
                    with c_conf1:
                        if str_app.button("✅ Sí, borrar todo", use_container_width=True):
                            if reiniciar_sistema_completo():
                                str_app.session_state.confirmar_reinicio = False
                                str_app.success("¡El sistema ha sido reiniciado a ceros con éxito!")
                                str_app.rerun()
                    with c_conf2:
                        if str_app.button("❌ Cancelar", use_container_width=True):
                            str_app.session_state.confirmar_reinicio = False
                            str_app.rerun()
        else:
            if str_app.button("⬅️ Regresar al Menú Principal"):
                str_app.session_state.sesion_principal = None
                str_app.session_state.seccion_activa = None
                str_app.rerun()

        # --- CONTENIDO DE LAS SESIONES ---
        if str_app.session_state.sesion_principal == "📦 Stock y Ventas":

            if "seccion_activa" not in str_app.session_state or str_app.session_state.seccion_activa is None:
                str_app.subheader("📦 Módulo Stock y Ventas")
                str_app.caption("Seleccione una opción para continuar:")

                col_m1, col_m2 = str_app.columns(2)
                with col_m1:
                    if str_app.button("📥 Entradas de Stock", use_container_width=True):
                        str_app.session_state.seccion_activa = "📥 Entradas"
                        str_app.rerun()
                    if str_app.button("📤 Nueva Remisión", use_container_width=True):
                        str_app.session_state.seccion_activa = "📤 Remisiones"
                        str_app.rerun()
                    if str_app.button("📊 Ver Stock Actual", use_container_width=True):
                        str_app.session_state.seccion_activa = "📊 Stock"
                        str_app.rerun()
                    if str_app.button("💸 Control de Gastos", use_container_width=True):
                        str_app.session_state.seccion_activa = "💸 Gastos"
                        str_app.rerun()
                with col_m2:
                    if str_app.button("👥 Clientes", use_container_width=True):
                        str_app.session_state.seccion_activa = "👥 Clientes"
                        str_app.rerun()
                    if str_app.button("💰 Control de Cartera", use_container_width=True):
                        str_app.session_state.seccion_activa = "💰 Cartera"
                        str_app.rerun()
                    if str_app.button("⚖️ Inventario Físico", use_container_width=True):
                        str_app.session_state.seccion_activa = "⚖️ Inventario Fisico"
                        str_app.rerun()
                    if str_app.button("📜 Historial de Remisiones", use_container_width=True):
                        str_app.session_state.seccion_activa = "📜 Historial"
                        str_app.rerun()
                    if str_app.button("📈 Utilidades por Galpón", use_container_width=True):
                        str_app.session_state.seccion_activa = "📈 Utilidades"
                        str_app.rerun()
                    if str_app.button("🏷️ Gastos Varios", use_container_width=True):
                        str_app.session_state.seccion_activa = "🏷️ Gastos Varios"
                        str_app.rerun()

            else:
                if str_app.button("🔙 Volver al Menú de Stock"):
                    str_app.session_state.seccion_activa = None
                    str_app.rerun()

                str_app.markdown("---")

                # ---------------- ENTRADAS ----------------
                if str_app.session_state.seccion_activa == "📥 Entradas":
                    str_app.subheader("📥 Entrada de Producción / Clasificación")
                    if rol_actual == "Invitado":
                        str_app.warning("👀 Modo Invitado: Solo puedes visualizar la sección.")
                    else:
                        str_app.caption("Registre los huevos recolectados y clasificados para sumarlos al inventario del galpón correspondiente.")
                        galpon_destino = str_app.selectbox("Seleccione el Galpón de Destino", GALPONES)
                        fecha_entrada = str_app.date_input("Fecha de la Entrada", value=date.today(), key="fecha_entrada_stock")

                        df_base_entrada = pd.DataFrame([{"Clasificación": "a", "Cantidad": 0}])
                        df_entrada_editado = str_app.data_editor(
                            df_base_entrada, num_rows="dynamic",
                            column_config={
                                "Clasificación": str_app.column_config.SelectboxColumn("Clasificación", options=CLASIFICACIONES, required=True),
                                "Cantidad": str_app.column_config.NumberColumn("Cantidad (Huevos)", min_value=1, step=1, format="%d", required=True)
                            },
                            use_container_width=True, key="editor_entradas_stock"
                        )

                        if str_app.button("➕ Registrar Entrada al Inventario"):
                            entradas_validas = df_entrada_editado[df_entrada_editado["Cantidad"] > 0].copy()
                            if entradas_validas.empty:
                                str_app.warning("Debe ingresar al menos un ítem con cantidad mayor a 0.")
                            else:
                                lista_items_entrada = [{"Clasificación": r["Clasificación"], "Cantidad": int(r["Cantidad"])} for _, r in entradas_validas.iterrows()]
                                if registrar_entrada_inventario(galpon_destino, lista_items_entrada, fecha_entrada):
                                    str_app.toast("¡Registrado con éxito! 🎉", icon="✅")
                                    str_app.success(f"¡Entrada de inventario registrada correctamente en {galpon_destino} el {fecha_entrada}!")
                                    str_app.rerun()

                    str_app.markdown("---")
                    str_app.markdown("#### 📜 Historial de Entradas")
                    df_hist_entradas = cargar_historial_entradas()
                    if not df_hist_entradas.empty:
                        c_gf, c_fi, c_ff = str_app.columns(3)
                        galpon_filtro_hist = c_gf.selectbox("Galpón", ["Todos"] + GALPONES, key="filtro_galpon_hist_entradas")
                        fecha_ini_hist = c_fi.date_input("Desde", value=df_hist_entradas["fecha"].min(), key="hist_entradas_desde")
                        fecha_fin_hist = c_ff.date_input("Hasta", value=df_hist_entradas["fecha"].max(), key="hist_entradas_hasta")

                        df_hist_filtrado = df_hist_entradas[(df_hist_entradas["fecha"] >= fecha_ini_hist) & (df_hist_entradas["fecha"] <= fecha_fin_hist)]
                        if galpon_filtro_hist != "Todos":
                            df_hist_filtrado = df_hist_filtrado[df_hist_filtrado["galpon"] == galpon_filtro_hist]

                        if not df_hist_filtrado.empty:
                            df_hist_mostrar = df_hist_filtrado[["fecha", "galpon", "clasificacion", "cantidad"]].copy()
                            df_hist_mostrar.columns = ["Fecha", "Galpón", "Clasificación", "Cantidad"]
                            df_hist_mostrar["Clasificación"] = df_hist_mostrar["Clasificación"].str.upper()
                            str_app.dataframe(df_hist_mostrar, use_container_width=True, hide_index=True)
                            str_app.caption(f"Total en el rango: {int(df_hist_filtrado['cantidad'].sum()):,} huevos".replace(",", "."))
                            boton_exportar_excel(df_hist_mostrar, "Historial_Entradas_Stock.xlsx")
                        else:
                            str_app.info("No hay entradas registradas en el rango seleccionado.")
                    else:
                        str_app.info("Aún no hay entradas de stock registradas.")

                # ---------------- INVENTARIO FÍSICO ----------------
                elif str_app.session_state.seccion_activa == "⚖️ Inventario Fisico":
                    str_app.subheader("⚖️ Inventario Físico y Mermas")
                    if rol_actual == "Invitado":
                        str_app.warning("👀 Modo Invitado: Solo lectura.")
                    else:
                        galpon_fisico = str_app.selectbox("Seleccione el Galpón a Auditar", GALPONES)
                        df_inv_actual = cargar_inventario()
                        fila_galp = df_inv_actual.loc[galpon_fisico] if galpon_fisico in df_inv_actual.index else pd.Series({c: 0 for c in CLASIFICACIONES})

                        datos_fisicos = []
                        for col_clasif in CLASIFICACIONES:
                            stock_sistema = int(fila_galp.get(col_clasif, 0))
                            datos_fisicos.append({"Clasificación": col_clasif, "Stock Sistema": stock_sistema, "Conteo Físico Real": stock_sistema})

                        df_fisico_base = pd.DataFrame(datos_fisicos)
                        df_fisico_editado = str_app.data_editor(
                            df_fisico_base, disabled=["Clasificación", "Stock Sistema"],
                            column_config={
                                "Stock Sistema": str_app.column_config.NumberColumn("Stock Sistema", format="%d"),
                                "Conteo Físico Real": str_app.column_config.NumberColumn("Conteo Físico Real", min_value=0, step=1, format="%d")
                            },
                            use_container_width=True, key=f"editor_fisico_{galpon_fisico}"
                        )

                        df_fisico_editado["Diferencia (Merma/Faltante)"] = df_fisico_editado["Stock Sistema"] - df_fisico_editado["Conteo Físico Real"]
                        str_app.dataframe(df_fisico_editado[["Clasificación", "Stock Sistema", "Conteo Físico Real", "Diferencia (Merma/Faltante)"]], use_container_width=True, hide_index=True)

                        diferencia_total = int(df_fisico_editado["Diferencia (Merma/Faltante)"].sum())
                        if diferencia_total != 0:
                            str_app.caption(f"⚠️ Diferencia neta detectada: {diferencia_total:,} huevos".replace(",", "."))

                        if str_app.button("💾 Guardar y Ajustar Inventario Físico"):
                            nuevo_stock_dict = {r["Clasificación"]: int(r["Conteo Físico Real"]) for _, r in df_fisico_editado.iterrows()}
                            if actualizar_inventario_fisico(galpon_fisico, nuevo_stock_dict):
                                str_app.toast("¡Registrado con éxito! 🎉", icon="✅")
                                str_app.success(f"¡Inventario físico de {galpon_fisico} aplicado con éxito!")
                                str_app.rerun()

                # ---------------- GASTOS POR GALPÓN ----------------
                elif str_app.session_state.seccion_activa == "💸 Gastos":
                    str_app.subheader("💸 Control de Gastos por Galpón")
                    if rol_actual == "Invitado":
                        str_app.warning("👀 Modo Invitado: Solo lectura.")
                    else:
                        with str_app.form(key="form_registrar_gasto"):
                            c_fecha_g = str_app.date_input("Fecha del Gasto", value=date.today())
                            c_galpon_g = str_app.selectbox("Galpón Asociado", GALPONES_GASTOS)
                            c_categoria_g = str_app.selectbox("Categoría de Gasto", CATEGORIAS_GASTO_GALPON)
                            c_desc_g = str_app.text_input("Descripción del Gasto", placeholder="Ej. Compra de concentrado fase 1")
                            c_valor_g = str_app.number_input("Valor ($)", min_value=0.0, step=1000.0, format="%.0f")

                            if str_app.form_submit_button("💾 Guardar Gasto"):
                                if c_valor_g <= 0:
                                    str_app.error("El valor del gasto debe ser mayor a 0.")
                                elif not c_desc_g.strip():
                                    str_app.error("Debes escribir una descripción del gasto.")
                                else:
                                    if registrar_gasto(c_fecha_g, c_galpon_g, c_categoria_g, c_desc_g, c_valor_g):
                                        str_app.toast("¡Registrado con éxito! 🎉", icon="✅")
                                        str_app.success("¡Gasto registrado con éxito!")
                                        str_app.rerun()

                    str_app.markdown("---")
                    df_gastos = cargar_gastos()
                    if not df_gastos.empty:
                        df_gastos['dt_fecha'] = pd.to_datetime(df_gastos['fecha'])
                        df_gastos['Año'] = df_gastos['dt_fecha'].dt.year
                        df_gastos['Mes_Num'] = df_gastos['dt_fecha'].dt.month

                        c_f1, c_f2 = str_app.columns(2)
                        anio_sel_g = c_f1.selectbox("📅 Año (Gastos)", sorted(df_gastos['Año'].unique().tolist(), reverse=True), key="anio_gasto")
                        mes_nombre_sel = c_f2.selectbox("📅 Mes (Gastos)", list(MESES_NOMBRES.values()), key="mes_gasto")
                        mes_num_sel = [k for k, v in MESES_NOMBRES.items() if v == mes_nombre_sel][0]

                        df_gf = df_gastos[(df_gastos['Año'] == anio_sel_g) & (df_gastos['Mes_Num'] == mes_num_sel)]
                        str_app.markdown(f"**Total Gastos Mes:** ${df_gf['valor'].sum():,.0f}".replace(",", "."))

                        if not df_gf.empty:
                            c_pdf, c_xls = str_app.columns(2)
                            with c_pdf:
                                pdf_gastos_buf = generar_pdf_gastos(df_gf, f"Reporte de Gastos - {mes_nombre_sel} {anio_sel_g}")
                                str_app.download_button("📄 Descargar en PDF", data=pdf_gastos_buf, file_name=f"Gastos_{mes_nombre_sel}_{anio_sel_g}.pdf", mime="application/pdf")
                            with c_xls:
                                boton_exportar_excel(df_gf[["fecha", "galpon", "categoria", "descripcion", "valor"]], f"Gastos_{mes_nombre_sel}_{anio_sel_g}.xlsx")
                            str_app.markdown("---")

                        for _, row_g in df_gf.iterrows():
                            with str_app.expander(f"📅 {row_g['fecha']} — [{row_g['galpon']}] {row_g['categoria']}: ${float(row_g['valor']):,.0f}".replace(",", ".")):
                                str_app.write(f"**Desc:** {row_g['descripcion']}")
                                if rol_actual == "Administrador":
                                    if confirmar_eliminacion(f"gasto_{row_g['id']}", etiqueta="🗑️ Eliminar Gasto"):
                                        eliminar_gasto(row_g['id'])
                                        str_app.rerun()

                # ---------------- GASTOS VARIOS ----------------
                elif str_app.session_state.seccion_activa == "🏷️ Gastos Varios":
                    str_app.subheader("🏷️ Control de Gastos Varios y Personales")
                    if rol_actual == "Invitado":
                        str_app.warning("👀 Modo Invitado: Solo lectura.")
                    else:
                        with str_app.form(key="form_registrar_gv"):
                            c_fecha_gv = str_app.date_input("Fecha", value=date.today())
                            c_cat_gv = str_app.selectbox("Categoría", CATEGORIAS_GASTO_VARIO)
                            c_desc_gv = str_app.text_input("Descripción")
                            c_val_gv = str_app.number_input("Valor ($)", min_value=0.0, step=1000.0, format="%.0f")
                            if str_app.form_submit_button("💾 Guardar Gasto Vario"):
                                if c_val_gv <= 0:
                                    str_app.error("El valor debe ser mayor a 0.")
                                else:
                                    if registrar_gasto_vario(c_fecha_gv, c_cat_gv, c_desc_gv, c_val_gv):
                                        str_app.toast("¡Registrado con éxito! 🎉", icon="✅")
                                        str_app.success("¡Guardado!")
                                        str_app.rerun()

                    df_gv = cargar_gastos_varios()
                    if not df_gv.empty:
                        c_pdf, c_xls = str_app.columns(2)
                        with c_pdf:
                            pdf_gv_buf = generar_pdf_gastos(df_gv, "Reporte de Gastos Varios y Personales")
                            str_app.download_button("📄 Descargar en PDF", data=pdf_gv_buf, file_name="Gastos_Varios.pdf", mime="application/pdf")
                        with c_xls:
                            boton_exportar_excel(df_gv[["fecha", "categoria", "descripcion", "valor"]], "Gastos_Varios.xlsx")
                        str_app.markdown("---")

                        for _, r in df_gv.iterrows():
                            with str_app.expander(f"📅 {r['fecha']} — [{r['categoria']}] ${float(r['valor']):,.0f}".replace(",", ".")):
                                str_app.write(f"**Desc:** {r['descripcion']}")
                                if rol_actual == "Administrador":
                                    if confirmar_eliminacion(f"gv_{r['id']}", etiqueta="🗑️ Eliminar"):
                                        eliminar_gasto_vario(r['id'])
                                        str_app.rerun()

                # ---------------- CLIENTES ----------------
                elif str_app.session_state.seccion_activa == "👥 Clientes":
                    str_app.subheader("👥 Directorio de Clientes")
                    df_cli = cargar_clientes()

                    if rol_actual == "Administrador":
                        tab_n, tab_e, tab_l = str_app.tabs(["➕ Agregar", "✏️ Editar", "📋 Lista"])

                        with tab_n:
                            with str_app.form("form_cli_nuevo"):
                                nom = str_app.text_input("Nombre *")
                                ced = str_app.text_input("Cédula/NIT")
                                dir_ = str_app.text_input("Dirección")
                                tel = str_app.text_input("Teléfono")
                                em = str_app.text_input("Email")
                                if str_app.form_submit_button("Guardar"):
                                    if not nom.strip():
                                        str_app.error("El nombre es obligatorio.")
                                    else:
                                        if guardar_cliente(nom, ced, dir_, tel, em):
                                            str_app.toast("¡Registrado con éxito! 🎉", icon="✅")
                                            str_app.success("Guardado!")
                                            str_app.rerun()

                        with tab_e:
                            if df_cli.empty:
                                str_app.info("No hay clientes registrados todavía.")
                            else:
                                cliente_editar = str_app.selectbox("Selecciona el cliente a editar", df_cli["nombre"].tolist(), key="sel_editar_cliente")
                                d_cli = df_cli[df_cli["nombre"] == cliente_editar].iloc[0]
                                with str_app.form("form_cli_editar"):
                                    ced_e = str_app.text_input("Cédula/NIT", value=str(d_cli.get("cedula_nit", "") or ""))
                                    dir_e = str_app.text_input("Dirección", value=str(d_cli.get("direccion", "") or ""))
                                    tel_e = str_app.text_input("Teléfono", value=str(d_cli.get("telefono", "") or ""))
                                    em_e = str_app.text_input("Email", value=str(d_cli.get("email", "") or ""))
                                    if str_app.form_submit_button("💾 Guardar Cambios"):
                                        if guardar_cliente(cliente_editar, ced_e, dir_e, tel_e, em_e):
                                            str_app.toast("¡Actualizado con éxito! 🎉", icon="✅")
                                            str_app.success("¡Cliente actualizado!")
                                            str_app.rerun()

                        with tab_l:
                            filtro_cli = str_app.text_input("🔎 Buscar cliente por nombre")
                            df_cli_filtrado = df_cli[df_cli["nombre"].str.contains(filtro_cli.strip().upper(), na=False)] if filtro_cli.strip() else df_cli
                            for _, r in df_cli_filtrado.iterrows():
                                with str_app.expander(f"👤 {r['nombre']}"):
                                    str_app.write(f"Cédula/NIT: {r.get('cedula_nit', '') or '—'}")
                                    str_app.write(f"Dirección: {r.get('direccion', '') or '—'}")
                                    str_app.write(f"Tel: {r.get('telefono', '') or '—'}")
                                    str_app.write(f"Email: {r.get('email', '') or '—'}")
                                    if confirmar_eliminacion(f"cli_{r['id']}"):
                                        eliminar_cliente(r['id'])
                                        str_app.rerun()
                    else:
                        filtro_cli = str_app.text_input("🔎 Buscar cliente por nombre")
                        df_cli_filtrado = df_cli[df_cli["nombre"].str.contains(filtro_cli.strip().upper(), na=False)] if filtro_cli.strip() else df_cli
                        for _, r in df_cli_filtrado.iterrows():
                            str_app.write(f"👤 **{r['nombre']}** | Tel: {r.get('telefono', '') or '—'}")

                # ---------------- REMISIONES ----------------
                elif str_app.session_state.seccion_activa == "📤 Remisiones":
                    str_app.subheader("📋 Nueva Remisión")
                    if rol_actual == "Invitado":
                        str_app.warning("👀 Modo Invitado.")
                    else:
                        df_inv = cargar_inventario()
                        df_clientes = cargar_clientes()
                        num_rem_act = obtener_siguiente_num_remision()

                        str_app.markdown(f"### Remisión No. {num_rem_act:06d}")
                        fecha_rem = str_app.date_input("Fecha", value=date.today())
                        opciones_cli = ["-- Escribir cliente nuevo --"] + df_clientes["nombre"].tolist() if not df_clientes.empty else ["-- Escribir cliente nuevo --"]
                        cliente_sel = str_app.selectbox("Cliente Guardado", opciones_cli)

                        v_nom, v_ced, v_dir, v_tel, v_em = "", "", "CHOACHI", "", ""
                        if cliente_sel != "-- Escribir cliente nuevo --" and not df_clientes.empty:
                            d_cli = df_clientes[df_clientes["nombre"] == cliente_sel].iloc[0]
                            v_nom, v_ced, v_dir, v_tel, v_em = str(d_cli.get("nombre", "")), str(d_cli.get("cedula_nit", "")), str(d_cli.get("direccion", "CHOACHI")), str(d_cli.get("telefono", "")), str(d_cli.get("email", ""))

                        c_nom = str_app.text_input("Cliente *", value=v_nom)
                        c_ced = str_app.text_input("Cédula/NIT", value=v_ced)
                        c_dir = str_app.text_input("Dirección", value=v_dir)
                        c_tel = str_app.text_input("Teléfono", value=v_tel)
                        c_em = str_app.text_input("Email", value=v_em)
                        c_cond = str_app.text_input("Conductor", value="Ivan Herrera")
                        guardar_cli_auto = str_app.checkbox("Guardar cliente", value=True)

                        df_base = pd.DataFrame([{"Clasificación": "a", "Cantidad (Huevos)": 0, "Precio Unitario ($)": 0, "Galpón Origen": GALPONES[0]}])
                        df_editado = str_app.data_editor(
                            df_base, num_rows="dynamic",
                            column_config={
                                "Clasificación": str_app.column_config.SelectboxColumn("Clasificación", options=CLASIFICACIONES, required=True),
                                "Cantidad (Huevos)": str_app.column_config.NumberColumn("Cantidad (Huevos)", min_value=1, step=1, format="%d", required=True),
                                "Precio Unitario ($)": str_app.column_config.NumberColumn("Precio Unitario ($)", min_value=0, format="$%d", required=True),
                                "Galpón Origen": str_app.column_config.SelectboxColumn("Galpón Origen", options=GALPONES, required=True)
                            },
                            use_container_width=True
                        )
                        items_validos = df_editado[df_editado["Cantidad (Huevos)"] > 0].copy()

                        if not items_validos.empty:
                            items_validos["Subtotal ($)"] = items_validos["Cantidad (Huevos)"] * items_validos["Precio Unitario ($)"]
                            tot_fac = items_validos["Subtotal ($)"].sum()
                            str_app.markdown(f"#### Total: ${tot_fac:,.0f}".replace(",", "."))

                            if str_app.button("🚀 Generar Remisión"):
                                if not c_nom.strip():
                                    str_app.error("El nombre del cliente es obligatorio.")
                                else:
                                    if guardar_cli_auto and c_nom.strip():
                                        guardar_cliente(c_nom, c_ced, c_dir, c_tel, c_em)

                                    items_dict = [{'Clasificación': r['Clasificación'], 'Cantidad (Huevos)': r['Cantidad (Huevos)'], 'Precio Unitario ($)': r['Precio Unitario ($)'], 'Subtotal ($)': r['Subtotal ($)'], 'Galpón': r['Galpón Origen']} for _, r in items_validos.iterrows()]

                                    try:
                                        if registrar_venta_multiple(c_nom, c_ced, c_dir, c_tel, c_em, c_cond, num_rem_act, fecha_rem, items_dict):
                                            str_app.toast("¡Registrado con éxito! 🎉", icon="✅")
                                            str_app.success("¡Remisión guardada con éxito!")

                                            cliente_datos = {"nombre": c_nom, "cedula": c_ced, "direccion": c_dir, "telefono": c_tel, "email": c_em}
                                            pdf_buf = generar_pdf_remision(num_rem_act, str(fecha_rem), c_cond, cliente_datos, items_validos, tot_fac)
                                            str_app.download_button("📄 Descargar Remisión en PDF", data=pdf_buf, file_name=f"Remision_{num_rem_act:06d}.pdf", mime="application/pdf")
                                    except ValueError as e:
                                        str_app.error(str(e))

                # ---------------- CARTERA ----------------
                elif str_app.session_state.seccion_activa == "💰 Cartera":
                    str_app.subheader("💰 Control de Cartera e Historial de Abonos")
                    df_cartera = cargar_cartera()
                    if df_cartera.empty:
                        str_app.info("Sin deudas registradas.")
                    else:
                        solo_pendientes = str_app.checkbox("Mostrar solo remisiones PENDIENTES", value=True)
                        df_cartera_mostrar = df_cartera[df_cartera["estado"] == "PENDIENTE"] if solo_pendientes else df_cartera

                        for _, row in df_cartera_mostrar.iterrows():
                            with str_app.expander(f"Remisión N° {int(row['num_remision']):06d} — {row['cliente']} | Saldo: ${float(row['saldo']):,.0f} ({row['estado']})".replace(",", ".")):
                                str_app.markdown("#### 📜 Historial de Abonos")
                                df_abonos = cargar_abonos_remision(int(row['num_remision']))
                                if not df_abonos.empty:
                                    df_abonos_mostrar = df_abonos[['fecha_abono', 'monto', 'nombre_comprobante']].copy()
                                    df_abonos_mostrar.columns = ['Fecha y Hora', 'Monto ($)', 'Comprobante']
                                    df_abonos_mostrar['Monto ($)'] = df_abonos_mostrar['Monto ($)'].apply(lambda x: f"${float(x):,.0f}".replace(",", "."))
                                    str_app.dataframe(df_abonos_mostrar, use_container_width=True, hide_index=True)
                                else:
                                    str_app.info("No hay abonos registrados para esta remisión.")

                                str_app.markdown("---")
                                if rol_actual == "Administrador" and float(row['saldo']) > 0:
                                    with str_app.form(key=f"ab_{row['num_remision']}"):
                                        str_app.markdown("#### ➕ Registrar Nuevo Abono")
                                        monto = str_app.number_input("Abono ($)", min_value=0.0, max_value=float(row['saldo']), step=1000.0, format="%.0f")
                                        arch = str_app.file_uploader("Comprobante (Opcional)", type=["png", "jpg", "jpeg", "pdf"], key=f"f_{row['num_remision']}")
                                        if str_app.form_submit_button("Registrar Abono"):
                                            if monto <= 0:
                                                str_app.error("El monto del abono debe ser mayor a 0.")
                                            else:
                                                if registrar_abono(int(row['num_remision']), monto, arch.read() if arch else None, arch.name if arch else None):
                                                    str_app.toast("¡Abono registrado con éxito! 🎉", icon="✅")
                                                    str_app.success("¡Abono registrado correctamente!")
                                                    str_app.rerun()

                # ---------------- STOCK ----------------
                elif str_app.session_state.seccion_activa == "📊 Stock":
                    str_app.subheader("📦 Stock Actual")
                    df_stock = cargar_inventario()
                    if not df_stock.empty:
                        df_stock_mostrar = df_stock.copy()
                        df_stock_mostrar.loc["TOTAL"] = df_stock_mostrar.sum(numeric_only=True)
                        str_app.dataframe(df_stock_mostrar, use_container_width=True)
                        boton_exportar_excel(df_stock.reset_index(), "Stock_Actual.xlsx")
                    else:
                        str_app.info("Sin datos de inventario todavía.")

                # ---------------- HISTORIAL DE REMISIONES ----------------
                elif str_app.session_state.seccion_activa == "📜 Historial":
                    str_app.subheader("📜 Historial de Remisiones")
                    df_h = cargar_remisiones()
                    if not df_h.empty and "fecha_emision" in df_h.columns:
                        c_fi, c_ff = str_app.columns(2)
                        fecha_ini = c_fi.date_input("Desde", value=df_h["fecha_emision"].min(), key="hist_desde")
                        fecha_fin = c_ff.date_input("Hasta", value=df_h["fecha_emision"].max(), key="hist_hasta")
                        df_h = df_h[(df_h["fecha_emision"] >= fecha_ini) & (df_h["fecha_emision"] <= fecha_fin)]

                    if not df_h.empty:
                        for num_sel in sorted(df_h['num_remision'].unique(), reverse=True):
                            df_r = df_h[df_h['num_remision'] == num_sel]
                            f_sel = df_r.iloc[0]
                            cliente_nombre = f_sel.get('cliente', '')

                            with str_app.expander(f"Remisión #{int(num_sel):06d} – {cliente_nombre}"):
                                columnas_deseadas = ['tipo_huevo', 'cantidad', 'precio_unitario', 'total', 'galpon']
                                columnas_validas = [col for col in columnas_deseadas if col in df_r.columns]

                                if not df_r.empty and columnas_validas:
                                    str_app.dataframe(df_r[columnas_validas], use_container_width=True)

                                    cliente_datos = {
                                        "nombre": cliente_nombre, "cedula": f_sel.get('cedula_nit', ''),
                                        "direccion": f_sel.get('destino', 'CHOACHI'), "telefono": f_sel.get('telefono', ''),
                                        "email": f_sel.get('email', '')
                                    }
                                    items_pdf = df_r.rename(columns={'tipo_huevo': 'Clasificación', 'cantidad': 'Cantidad (Huevos)', 'precio_unitario': 'Precio Unitario ($)', 'total': 'Subtotal ($)'})
                                    total_factura = df_r['total'].sum()
                                    fecha_str = str(f_sel.get('fecha_emision', date.today()))
                                    conductor_val = f_sel.get('conductor', 'Ivan Herrera')

                                    pdf_buf = generar_pdf_remision(int(num_sel), fecha_str, conductor_val, cliente_datos, items_pdf, total_factura)
                                    str_app.download_button(f"📄 Descargar PDF Remisión #{int(num_sel):06d}", data=pdf_buf, file_name=f"Remision_{int(num_sel):06d}.pdf", mime="application/pdf", key=f"dl_hist_{num_sel}")
                                else:
                                    str_app.warning("No se encontraron registros o columnas válidas para esta remisión.")

                        boton_exportar_excel(df_h, "Historial_Remisiones.xlsx", key="xls_historial")
                    else:
                        str_app.info("No hay remisiones registradas en el rango seleccionado.")

                # ---------------- UTILIDADES POR GALPÓN ----------------
                elif str_app.session_state.seccion_activa == "📈 Utilidades":
                    str_app.subheader("📈 Utilidades por Galpón")
                    str_app.caption("Análisis financiero de ingresos por ventas, gastos directos y utilidad neta por galpón.")

                    df_rem = cargar_remisiones()
                    df_gas = cargar_gastos()

                    if df_rem.empty and df_gas.empty:
                        str_app.info("No hay datos suficientes de ventas o gastos para calcular utilidades.")
                    else:
                        if not df_rem.empty and 'fecha_emision' in df_rem.columns:
                            df_rem['dt_fecha'] = pd.to_datetime(df_rem['fecha_emision'])
                        if not df_gas.empty and 'fecha' in df_gas.columns:
                            df_gas['dt_fecha'] = pd.to_datetime(df_gas['fecha'])

                        anios_disponibles = set()
                        if not df_rem.empty and 'dt_fecha' in df_rem.columns:
                            anios_disponibles.update(df_rem['dt_fecha'].dt.year.unique().tolist())
                        if not df_gas.empty and 'dt_fecha' in df_gas.columns:
                            anios_disponibles.update(df_gas['dt_fecha'].dt.year.unique().tolist())
                        anios_disponibles = sorted(anios_disponibles, reverse=True) if anios_disponibles else [date.today().year]

                        vista_util = str_app.radio("Vista", ["📅 Mes específico", "📊 Histórico completo"], horizontal=True, key="vista_utilidades")

                        if vista_util == "📅 Mes específico":
                            c_fu1, c_fu2 = str_app.columns(2)
                            anio_sel_u = c_fu1.selectbox("📅 Año", anios_disponibles, key="anio_util")
                            indice_mes_actual = date.today().month - 1
                            mes_nombre_sel_u = c_fu2.selectbox("📅 Mes", list(MESES_NOMBRES.values()), index=indice_mes_actual, key="mes_util")
                            mes_num_sel_u = [k for k, v in MESES_NOMBRES.items() if v == mes_nombre_sel_u][0]

                            df_rem_periodo = df_rem[(df_rem['dt_fecha'].dt.year == anio_sel_u) & (df_rem['dt_fecha'].dt.month == mes_num_sel_u)] if not df_rem.empty and 'dt_fecha' in df_rem.columns else pd.DataFrame()
                            df_gas_periodo = df_gas[(df_gas['dt_fecha'].dt.year == anio_sel_u) & (df_gas['dt_fecha'].dt.month == mes_num_sel_u)] if not df_gas.empty and 'dt_fecha' in df_gas.columns else pd.DataFrame()
                            titulo_periodo = f"{mes_nombre_sel_u} {anio_sel_u}"
                        else:
                            df_rem_periodo = df_rem
                            df_gas_periodo = df_gas
                            titulo_periodo = "Histórico completo"

                        resumen_utilidades = []
                        for g in GALPONES:
                            ingresos = float(df_rem_periodo[df_rem_periodo['galpon'] == g]['total'].sum()) if not df_rem_periodo.empty and 'galpon' in df_rem_periodo.columns and 'total' in df_rem_periodo.columns else 0.0
                            gastos = float(df_gas_periodo[df_gas_periodo['galpon'] == g]['valor'].sum()) if not df_gas_periodo.empty and 'galpon' in df_gas_periodo.columns and 'valor' in df_gas_periodo.columns else 0.0
                            resumen_utilidades.append({"Galpón": g, "Ingresos ($)": ingresos, "Gastos ($)": gastos, "Utilidad ($)": ingresos - gastos})

                        gastos_generales = float(df_gas_periodo[df_gas_periodo['galpon'] == "General / Granja"]['valor'].sum()) if not df_gas_periodo.empty and 'galpon' in df_gas_periodo.columns and 'valor' in df_gas_periodo.columns else 0.0

                        df_util = pd.DataFrame(resumen_utilidades)
                        total_ingresos = df_util["Ingresos ($)"].sum()
                        total_gastos_galpones = df_util["Gastos ($)"].sum()
                        utilidad_neta_total = total_ingresos - (total_gastos_galpones + gastos_generales)

                        str_app.markdown(f"#### {titulo_periodo}")
                        col_u1, col_u2, col_u3 = str_app.columns(3)
                        col_u1.metric("Total Ingresos", f"${total_ingresos:,.0f}".replace(",", "."))
                        col_u2.metric("Total Gastos", f"${(total_gastos_galpones + gastos_generales):,.0f}".replace(",", "."))
                        col_u3.metric("Utilidad Neta", f"${utilidad_neta_total:,.0f}".replace(",", "."))

                        if total_ingresos > 0 or total_gastos_galpones > 0:
                            str_app.bar_chart(df_util.set_index("Galpón")[["Ingresos ($)", "Gastos ($)"]])
                        else:
                            str_app.caption(f"Sin movimientos registrados en {titulo_periodo}.")

                        str_app.markdown("---")
                        str_app.markdown("#### 📋 Detalle Financiero por Galpón")

                        df_mostrar = df_util.copy()
                        for col in ["Ingresos ($)", "Gastos ($)", "Utilidad ($)"]:
                            df_mostrar[col] = df_mostrar[col].apply(lambda x: f"$ {x:,.0f}".replace(",", "."))
                        str_app.dataframe(df_mostrar, use_container_width=True, hide_index=True)
                        boton_exportar_excel(df_util, f"Utilidades_{titulo_periodo.replace(' ', '_')}.xlsx")

                        if gastos_generales > 0:
                            str_app.info(f"💡 Gastos Generales / Granja no asignados a un galpón específico: $ {gastos_generales:,.0f}".replace(",", "."))

                        # --- Evolución mensual de la utilidad total (independiente del filtro de arriba) ---
                        str_app.markdown("---")
                        str_app.markdown("#### 📈 Evolución Mensual de la Utilidad (Todos los Galpones)")

                        serie_ingresos_mes = pd.Series(dtype=float)
                        serie_gastos_mes = pd.Series(dtype=float)
                        if not df_rem.empty and 'dt_fecha' in df_rem.columns and 'total' in df_rem.columns:
                            serie_ingresos_mes = df_rem.groupby(df_rem['dt_fecha'].dt.to_period('M'))['total'].sum().rename("Ingresos")
                        if not df_gas.empty and 'dt_fecha' in df_gas.columns and 'valor' in df_gas.columns:
                            serie_gastos_mes = df_gas.groupby(df_gas['dt_fecha'].dt.to_period('M'))['valor'].sum().rename("Gastos")

                        df_evolucion = pd.concat([serie_ingresos_mes, serie_gastos_mes], axis=1).fillna(0.0)
                        if not df_evolucion.empty:
                            df_evolucion["Utilidad"] = df_evolucion["Ingresos"] - df_evolucion["Gastos"]
                            df_evolucion = df_evolucion.sort_index()
                            df_evolucion.index = df_evolucion.index.astype(str)
                            str_app.bar_chart(df_evolucion[["Utilidad"]])

                            with str_app.expander("Ver detalle mes a mes"):
                                df_evolucion_mostrar = df_evolucion.reset_index().rename(columns={"index": "Mes"})
                                for col in ["Ingresos", "Gastos", "Utilidad"]:
                                    df_evolucion_mostrar[col] = df_evolucion_mostrar[col].apply(lambda x: f"$ {x:,.0f}".replace(",", "."))
                                str_app.dataframe(df_evolucion_mostrar, use_container_width=True, hide_index=True)
                                boton_exportar_excel(df_evolucion.reset_index().rename(columns={"index": "Mes"}), "Evolucion_Mensual_Utilidad.xlsx")
                        else:
                            str_app.caption("Aún no hay suficientes datos para mostrar la evolución mensual.")

        elif str_app.session_state.sesion_principal == "📝 Registro Diario":
            str_app.subheader("📝 Módulo de Registro Diario (Edades, Mortalidad y Concentrado)")
            galpon_reg = str_app.selectbox("Seleccione el Galpón", GALPONES, key="galp_reg_sel")
            tab_config, tab_diario, tab_historial = str_app.tabs(["⚙️ Configuración Inicial", "✍️ Registrar Día", "📊 Historial y PDF"])

            with tab_config:
                str_app.markdown("#### Configuración Inicial del Lote (Se ingresa una sola vez)")
                config_actual = cargar_config_galpon(galpon_reg)

                ini_sem = config_actual['edad_semanas'] if config_actual else 0
                ini_dias = config_actual['edad_dias'] if config_actual else 0
                ini_aves = config_actual['aves_iniciales'] if config_actual else 0

                with str_app.form(f"form_config_{galpon_reg}"):
                    c_sem = str_app.number_input("Edad Inicial (Semanas)", min_value=0, value=int(ini_sem), step=1)
                    c_dias = str_app.number_input("Edad Inicial (Días adicionales 0-6)", min_value=0, max_value=6, value=int(ini_dias), step=1)
                    c_aves = str_app.number_input("Número de Aves Iniciales del Lote", min_value=0, value=int(ini_aves), step=10)

                    if str_app.form_submit_button("💾 Guardar Configuración del Galpón"):
                        if c_aves <= 0:
                            str_app.error("El número de aves iniciales debe ser mayor a 0.")
                        else:
                            if guardar_config_galpon(galpon_reg, c_sem, c_dias, c_aves):
                                str_app.toast("¡Registrado con éxito! 🎉", icon="✅")
                                str_app.success(f"¡Configuración de {galpon_reg} guardada con éxito!")
                                str_app.rerun()

            with tab_diario:
                if rol_actual == "Invitado":
                    str_app.warning("👀 Modo Invitado: No tienes permisos para registrar datos diarios.")
                else:
                    config = cargar_config_galpon(galpon_reg)
                    if not config:
                        str_app.warning("⚠️ Primero debes configurar la Edad y Aves Iniciales en la pestaña 'Configuración Inicial'.")
                    else:
                        with str_app.form(f"form_reg_diario_{galpon_reg}"):
                            fecha_reg = str_app.date_input("Fecha del Registro", value=date.today())
                            mortalidad = str_app.number_input("Mortalidad del Día (Aves muertas)", min_value=0, value=0, step=1)
                            conc_ing = str_app.number_input("Concentrado Ingresado (Bultos)", min_value=0.0, value=0.0, step=0.5, format="%g")
                            conc_cons = str_app.number_input("Concentrado Consumido (Bultos)", min_value=0.0, value=0.0, step=0.5, format="%g")
                            huevos = str_app.number_input("Huevos Recolectados (Opcional)", min_value=0, value=0, step=1)
                            obs = str_app.text_input("Observaciones / Novedades")

                            if str_app.form_submit_button("📥 Guardar Registro Diario"):
                                if registrar_dia_galpon(fecha_reg, galpon_reg, int(mortalidad), float(conc_ing), float(conc_cons), int(huevos), obs):
                                    str_app.toast("¡Registrado con éxito! 🎉", icon="✅")
                                    str_app.success(f"¡Registro diario guardado para {galpon_reg}! La edad y el stock de aves se han actualizado automáticamente.")
                                    str_app.rerun()

            with tab_historial:
                str_app.markdown(f"#### 📊 Resumen y Registros de {galpon_reg}")
                config = cargar_config_galpon(galpon_reg)
                df_reg = cargar_registros_diarios(galpon_reg)

                if not config:
                    str_app.info("Galpón sin configuración inicial.")
                else:
                    dias_acumulados = len(df_reg)
                    total_dias_calc = config['edad_dias'] + dias_acumulados
                    semanas_extra = total_dias_calc // 7
                    dias_finales = total_dias_calc % 7
                    edad_actual_sem = config['edad_semanas'] + semanas_extra
                    edad_actual_str = f"{edad_actual_sem} semanas y {dias_finales} días"

                    total_mortalidad = int(df_reg['mortalidad'].sum()) if not df_reg.empty else 0
                    aves_actuales = config['aves_iniciales'] - total_mortalidad
                    porc_mortalidad_acum = (total_mortalidad / config['aves_iniciales'] * 100) if config['aves_iniciales'] > 0 else 0.0

                    total_conc_ing = float(df_reg['concentrado_ingresado'].sum()) if not df_reg.empty else 0.0
                    total_conc_cons = float(df_reg['concentrado_consumido'].sum()) if not df_reg.empty else 0.0
                    saldo_concentrado = total_conc_ing - total_conc_cons
                    total_huevos_lote = int(df_reg['huevos_recolectados'].sum()) if not df_reg.empty else 0

                    # Conversión alimenticia aproximada: bultos de concentrado consumidos
                    # por cada 100 huevos producidos en la vida del lote (métrica típica
                    # de seguimiento avícola para vigilar eficiencia del alimento).
                    conversion_bultos_100h = (total_conc_cons / (total_huevos_lote / 100)) if total_huevos_lote > 0 else None

                    porc_prod_semana = 0.0
                    if not df_reg.empty and 'huevos_recolectados' in df_reg.columns:
                        df_ultimos_7 = df_reg.head(7)
                        total_huevos_7d = df_ultimos_7['huevos_recolectados'].sum()
                        dias_conteo = len(df_ultimos_7)
                        if dias_conteo > 0 and aves_actuales > 0:
                            promedio_diario_huevos = total_huevos_7d / dias_conteo
                            porc_prod_semana = (promedio_diario_huevos / aves_actuales) * 100

                    conversion_str = f"{conversion_bultos_100h:.2f} bultos / 100 huevos" if conversion_bultos_100h is not None else "Sin datos de huevos aún"

                    str_app.markdown(f"""
                        <div style="background-color: #1a3e63; color: white; padding: 15px; border-radius: 8px; margin-bottom: 15px; border-left: 5px solid #f26822;">
                            <p style="margin: 0; font-size: 16px; color: #f26822 !important;"><b>Edad Actual del Lote:</b> {edad_actual_str}</p>
                            <p style="margin: 0; font-size: 14px;">Aves Iniciales: {config['aves_iniciales']:,} | Mortalidad Acumulada: {total_mortalidad} ({porc_mortalidad_acum:.2f}%)</p>
                            <p style="margin: 0; font-size: 15px; color: #f26822 !important;"><b>Aves Vivas Actuales:</b> {aves_actuales:,}</p>
                            <p style="margin: 0; font-size: 15px; color: #f26822 !important;"><b>% Producción Acumulado (Últimos 7 días):</b> {porc_prod_semana:.2f}%</p>
                            <hr style="border-color: #2c5282; margin: 8px 0;">
                            <p style="margin: 0; font-size: 14px;">Concentrado Ingresado: {total_conc_ing:.1f} bultos | Consumido: {total_conc_cons:.1f} bultos</p>
                            <p style="margin: 0; font-size: 15px; color: #2c5282 !important;"><b>Saldo Concentrado Bodega:</b> {saldo_concentrado:.1f} bultos</p>
                            <p style="margin: 0; font-size: 14px;"><b>Conversión Alimenticia:</b> {conversion_str}</p>
                        </div>
                    """, unsafe_allow_html=True)

                    if porc_mortalidad_acum >= 5:
                        str_app.warning(f"⚠️ La mortalidad acumulada de {galpon_reg} ({porc_mortalidad_acum:.1f}%) está en un nivel que conviene revisar.")

                    if not df_reg.empty:
                        df_tendencia_galpon = df_reg[["fecha", "huevos_recolectados", "mortalidad"]].sort_values("fecha").set_index("fecha")
                        str_app.line_chart(df_tendencia_galpon)

                        c_pdf, c_xls = str_app.columns(2)
                        with c_pdf:
                            pdf_buf = generar_pdf_registro_diario(galpon_reg, config, df_reg, edad_actual_str, aves_actuales, saldo_concentrado)
                            str_app.download_button(f"📄 Descargar Reporte PDF de {galpon_reg}", data=pdf_buf, file_name=f"Registro_Diario_{galpon_reg.replace(' ', '_')}.pdf", mime="application/pdf")
                        with c_xls:
                            boton_exportar_excel(df_reg, f"Registro_Diario_{galpon_reg.replace(' ', '_')}.xlsx")

                        str_app.markdown("---")
                        str_app.markdown("#### 📑 Detalle Histórico de Registros")
                        for _, row in df_reg.iterrows():
                            r_id = row['id']
                            r_fecha = str(row['fecha'])
                            r_mort = int(row['mortalidad'])
                            r_ing = float(row['concentrado_ingresado'])
                            r_cons = float(row['concentrado_consumido'])
                            r_hue = int(row['huevos_recolectados'])
                            r_obs = row['observaciones']

                            with str_app.expander(f"📅 {r_fecha} | Mortalidad: {r_mort} | Conc. Consumido: {r_cons} bultos"):
                                str_app.write(f"**Concentrado Ingresado:** {r_ing} bultos")
                                str_app.write(f"**Huevos Recolectados:** {r_hue}")
                                str_app.write(f"**Observaciones:** {r_obs}")
                                if rol_actual == "Administrador":
                                    if confirmar_eliminacion(f"reg_{r_id}", etiqueta="🗑️ Eliminar Registro"):
                                        eliminar_registro_diario(r_id)
                                        str_app.warning("Registro diario eliminado y cálculos actualizados.")
                                        str_app.rerun()
                    else:
                        str_app.info("No hay registros diarios ingresados todavía para este galpón.")

    except psycopg2.Error as e:
        str_app.error("⚠️ Ocurrió un problema de conexión con la base de datos. Intenta de nuevo en unos segundos.")
        with str_app.expander("Detalle técnico"):
            str_app.code(str(e))
        if str_app.button("🔄 Reintentar"):
            str_app.rerun()
    except Exception as e:
        str_app.error("⚠️ Ocurrió un error inesperado al procesar esta sección.")
        with str_app.expander("Detalle técnico"):
            str_app.code(str(e))
        if str_app.button("🔄 Reintentar", key="reintentar_general"):
            str_app.rerun()
