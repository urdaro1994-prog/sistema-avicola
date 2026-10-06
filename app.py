import streamlit as str_app
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
CLASIFICACIONES = ["yumbo", "extra", "aa", "a", "b", "c", "sucio", "roto", "palido"]
COLUMNAS_INVENTARIO = set(CLASIFICACIONES)
MESES_NOMBRES = {1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril', 5: 'Mayo', 6: 'Junio',
                  7: 'Julio', 8: 'Agosto', 9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'}
CATEGORIAS_GASTO_GALPON = ["Alimento", "Medicamentos / Sanidad", "Personal / Mano de Obra",
                            "Mantenimiento / Reparaciones", "Servicios Públicos", "Otros"]
CATEGORIAS_GASTO_VARIO = ["Personal", "Hogar", "Vehículo", "Impuestos", "Varios"]
CATEGORIAS_GASTO_CAMION = ["Combustible", "Mantenimiento / Repuestos", "Llantas", "Peajes",
                           "Seguro / SOAT / Tecnomecánica", "Lavado / Parqueadero", "Viáticos", "Otros"]

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
            galpon TEXT PRIMARY KEY
        );
    """)
    # Si la tabla ya existía de una versión anterior (por ejemplo, antes de
    # agregar la clasificación "palido"), CREATE TABLE IF NOT EXISTS no la
    # modifica. Este bucle agrega cualquier columna de clasificación que
    # falte, para que nunca vuelva a pasar el error de "columna no existe".
    for col_clasif in CLASIFICACIONES:
        ejecutar(f"ALTER TABLE inventario ADD COLUMN IF NOT EXISTS {col_clasif} INT DEFAULT 0;")
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
            comprobante BYTEA, nombre_comprobante TEXT, observacion TEXT
        );
    """)
    ejecutar("ALTER TABLE abonos_cartera ADD COLUMN IF NOT EXISTS observacion TEXT;")
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
        CREATE TABLE IF NOT EXISTS gastos_camion (
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


@operacion_segura
def actualizar_historial_entrada(id_entrada, nuevo_galpon, nueva_clasificacion, nueva_cantidad, nueva_fecha):
    with get_conn() as conn:
        with conn:
            with conn.cursor() as cur:
                cur.execute("SELECT galpon, clasificacion, cantidad FROM historial_entradas WHERE id = %s", (id_entrada,))
                res = cur.fetchone()
                if not res:
                    raise ValueError("La entrada de stock no existe.")
                old_galpon, old_clasif, old_cant = res[0], res[1].lower(), res[2]
                if old_clasif not in COLUMNAS_INVENTARIO:
                    raise ValueError(f"La entrada tiene una clasificación inválida guardada: {old_clasif}")

                # Antes de revertir el stock de la entrada original, verificamos que
                # esa cantidad siga disponible: si ya se vendió parte de ese stock,
                # restarlo dejaría el inventario en negativo. En ese caso se bloquea
                # la edición con un mensaje claro en vez de corromper el inventario.
                cur.execute(f"SELECT {old_clasif} FROM inventario WHERE galpon = %s", (old_galpon,))
                res_stock = cur.fetchone()
                stock_actual = res_stock[0] if res_stock else 0
                if stock_actual < old_cant:
                    raise ValueError(
                        f"No se puede editar esta entrada: parte de ese stock de '{old_clasif.upper()}' en {old_galpon} "
                        f"ya fue vendido o movido (stock actual: {stock_actual:,}, cantidad original: {old_cant:,}). "
                        f"Ajusta primero las remisiones o el inventario físico antes de editar esta entrada.".replace(",", ".")
                    )

                # Revertir stock anterior
                cur.execute(f"UPDATE inventario SET {old_clasif} = {old_clasif} - %s WHERE galpon = %s", (old_cant, old_galpon))

                # Aplicar nuevo stock
                nueva_clasificacion = nueva_clasificacion.lower()
                if nueva_clasificacion not in COLUMNAS_INVENTARIO:
                    raise ValueError(f"Clasificación inválida: {nueva_clasificacion}")
                cur.execute(f"UPDATE inventario SET {nueva_clasificacion} = {nueva_clasificacion} + %s WHERE galpon = %s", (nueva_cantidad, nuevo_galpon))

                # Actualizar registro en historial_entradas
                cur.execute("""
                    UPDATE historial_entradas 
                    SET fecha = %s, galpon = %s, clasificacion = %s, cantidad = %s 
                    WHERE id = %s
                """, (nueva_fecha, nuevo_galpon, nueva_clasificacion, nueva_cantidad, id_entrada))


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
    # Generado dinámicamente a partir de CLASIFICACIONES, para que agregar o quitar
    # una clasificación en el futuro no requiera recordar actualizar esta consulta.
    set_columnas = ", ".join([f"{c} = %s" for c in CLASIFICACIONES])
    valores = [nuevo_stock_dict.get(c, 0) for c in CLASIFICACIONES] + [galpon]
    ejecutar(f"UPDATE inventario SET {set_columnas} WHERE galpon = %s", tuple(valores))


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


@operacion_segura
def actualizar_remision(num_remision, cliente, cedula, direccion, telefono, email, conductor, fecha_remision, nuevos_items):
    requerido = {}
    for item in nuevos_items:
        clasificacion = item['Clasificación'].lower()
        if clasificacion not in COLUMNAS_INVENTARIO:
            raise ValueError(f"Clasificación inválida: {clasificacion}")
        galp_origen = item.get('Galpón', GALPONES[0])
        clave = (galp_origen, clasificacion)
        requerido[clave] = requerido.get(clave, 0) + int(item['Cantidad (Huevos)'])

    with get_conn() as conn:
        with conn:
            with conn.cursor() as cur:
                # 1. Revertir inventario de la remisión anterior
                cur.execute("SELECT galpon, tipo_huevo, cantidad FROM remisiones WHERE num_remision = %s", (num_remision,))
                old_rows = cur.fetchall()
                for galp, clasif, cant in old_rows:
                    clasif = clasif.lower()
                    if clasif not in COLUMNAS_INVENTARIO:
                        raise ValueError(f"La remisión original contiene una clasificación inválida: {clasif}")
                    cur.execute(f"UPDATE inventario SET {clasif} = {clasif} + %s WHERE galpon = %s", (cant, galp))

                # 2. Validar stock para los nuevos ítems
                for (galp_origen, clasificacion), cantidad_total in requerido.items():
                    cur.execute(f"SELECT {clasificacion} FROM inventario WHERE galpon = %s", (galp_origen,))
                    res = cur.fetchone()
                    stock_actual = res[0] if res else 0
                    if cantidad_total > stock_actual:
                        raise ValueError(
                            f"Stock insuficiente de '{clasificacion.upper()}' en {galp_origen}. "
                            f"Stock actual: {stock_actual:,}, solicitado: {cantidad_total:,}".replace(",", ".")
                        )

                # 3. Eliminar registros antiguos de la remisión
                cur.execute("DELETE FROM remisiones WHERE num_remision = %s", (num_remision,))

                # 3.1 Detectar qué columnas admiten inserción directa (algunas, como
                # "total", pueden estar definidas como columna generada/calculada en
                # la base de datos, y no se les puede insertar un valor a mano).
                cur.execute("""
                    SELECT column_name, is_generated, identity_generation
                    FROM information_schema.columns WHERE table_name = 'remisiones';
                """)
                columnas_validas = {c for c, is_gen, id_gen in cur.fetchall() if is_gen != 'ALWAYS' and id_gen != 'ALWAYS'}

                # 4. Insertar nuevos registros y descontar inventario
                total_venta_acumulado = 0.0
                for item in nuevos_items:
                    clasificacion = item['Clasificación'].lower()
                    cantidad = int(item['Cantidad (Huevos)'])
                    subtotal = float(item['Subtotal ($)'])
                    precio_u = float(item['Precio Unitario ($)'])
                    galp_origen = item.get('Galpón', GALPONES[0])
                    total_venta_acumulado += subtotal

                    datos_insert = {
                        "num_remision": num_remision, "fecha_emision": fecha_remision,
                        "cliente": cliente.strip().upper(), "cedula_nit": cedula, "telefono": telefono,
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

                # 5. Actualizar cartera
                cur.execute("SELECT COALESCE(SUM(monto), 0) FROM abonos_cartera WHERE num_remision = %s", (num_remision,))
                total_abonos = float(cur.fetchone()[0])
                nuevo_saldo = max(0.0, total_venta_acumulado - total_abonos)
                nuevo_estado = 'PAGADA' if nuevo_saldo <= 0 else 'PENDIENTE'

                cur.execute("""
                    INSERT INTO cartera (num_remision, cliente, total, saldo, estado)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (num_remision) DO UPDATE SET
                        cliente = EXCLUDED.cliente, total = EXCLUDED.total, saldo = EXCLUDED.saldo, estado = EXCLUDED.estado;
                """, (num_remision, cliente.strip().upper(), total_venta_acumulado, nuevo_saldo, nuevo_estado))


# --- CARTERA ---
@lectura_segura
def cargar_cartera():
    return leer_df("SELECT * FROM cartera ORDER BY num_remision DESC")


@lectura_segura
def cargar_abonos_remision(num_remision):
    return leer_df("SELECT * FROM abonos_cartera WHERE num_remision = %s ORDER BY fecha_abono DESC", (num_remision,))


@operacion_segura
def registrar_abono(num_remision, monto_abono, comprobante_bytes=None, nombre_comprobante=None, observacion=None):
    with get_conn() as conn:
        with conn:
            with conn.cursor() as cur:
                fecha_actual = datetime.now()
                comp_binary = psycopg2.Binary(comprobante_bytes) if comprobante_bytes else None
                cur.execute("""
                    INSERT INTO abonos_cartera (num_remision, fecha_abono, monto, comprobante, nombre_comprobante, observacion)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (num_remision, fecha_actual, monto_abono, comp_binary, nombre_comprobante, observacion))

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


@operacion_segura
def registrar_gasto_camion(fecha, categoria, descripcion, valor):
    ejecutar("INSERT INTO gastos_camion (fecha, categoria, descripcion, valor) VALUES (%s, %s, %s, %s)",
              (fecha, categoria, descripcion, valor))


@lectura_segura
def cargar_gastos_camion():
    df = leer_df("SELECT * FROM gastos_camion ORDER BY fecha DESC, id DESC")
    if not df.empty:
        df['fecha'] = pd.to_datetime(df['fecha']).dt.date
    return df


@operacion_segura
def eliminar_gasto_camion(gasto_id):
    ejecutar("DELETE FROM gastos_camion WHERE id = %s", (gasto_id,))


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
                         "gastos_varios", "gastos_camion", "registros_diarios", "galpon_config", "historial_entradas"]
    for tabla in tablas_a_limpiar:
        try:
            ejecutar(f"TRUNCATE TABLE {tabla} RESTART IDENTITY CASCADE;")
        except psycopg2.Error:
            ejecutar(f"DELETE FROM {tabla};")
    # Se genera dinámicamente a partir de CLASIFICACIONES para que, si en el futuro
    # se agrega o quita una clasificación, el reinicio no quede desactualizado.
    set_columnas = ", ".join([f"{c} = 0" for c in CLASIFICACIONES])
    ejecutar(f"UPDATE inventario SET {set_columnas};")


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
        "aves_actuales_por_galpon": {g: 0 for g in GALPONES},
        "porcentaje_produccion_hoy_por_galpon": {g: 0.0 for g in GALPONES},
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
    
    for g in GALPONES:
        config_g = cargar_config_galpon(g)
        aves_ini = config_g['aves_iniciales'] if config_g else 0
        if not df_reg.empty and "galpon" in df_reg.columns:
            df_g_reg = df_reg[df_reg["galpon"] == g]
            mort_total = int(df_g_reg["mortalidad"].sum()) if not df_g_reg.empty else 0
            aves_vivas = max(0, aves_ini - mort_total)
        else:
            aves_vivas = aves_ini
        resumen["aves_actuales_por_galpon"][g] = aves_vivas

    if not df_reg.empty:
        df_hoy = df_reg[df_reg["fecha"] == hoy]
        resumen["produccion_hoy"] = int(df_hoy["huevos_recolectados"].sum())
        if "galpon" in df_hoy.columns:
            for g in GALPONES:
                huevos_hoy_g = int(df_hoy[df_hoy["galpon"] == g]["huevos_recolectados"].sum())
                resumen["produccion_por_galpon"][g] = huevos_hoy_g
                aves_g = resumen["aves_actuales_por_galpon"][g]
                if aves_g > 0:
                    resumen["porcentaje_produccion_hoy_por_galpon"][g] = (huevos_hoy_g / aves_g) * 100
                else:
                    resumen["porcentaje_produccion_hoy_por_galpon"][g] = 0.0

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
    df_gastos_c = cargar_gastos_camion()
    if not df_gastos_c.empty:
        total_gastos_mes += float(df_gastos_c[pd.to_datetime(df_gastos_c["fecha"]) >= inicio_mes]["valor"].sum())
    resumen["gastos_mes"] = total_gastos_mes

    df_rem = cargar_remisiones()
    if not df_rem.empty and "fecha_emision" in df_rem.columns and "total" in df_rem.columns:
        df_rem_mes = df_rem[pd.to_datetime(df_rem["fecha_emision"]) >= inicio_mes]
        resumen["ventas_mes"] = float(df_rem_mes["total"].sum())

    return resumen


def _fila_metrica_con_desglose(icono, titulo, valor_total, valores_por_galpon, es_moneda=False, porcentajes_por_galpon=None):
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
        if porcentajes_por_galpon is not None and g in porcentajes_por_galpon:
            porc_g = porcentajes_por_galpon[g]
            texto_g += f" <span style='font-size:11px; color:#f26822;'>({porc_g:.1f}%)</span>"
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
    total_aves_vivas = sum(resumen["aves_actuales_por_galpon"].values())

    _fila_metrica_con_desglose("📦", "Stock Total", resumen["stock_total"], resumen["stock_por_galpon"])
    _fila_metrica_con_desglose("🐔", "Aves Actuales", total_aves_vivas, resumen["aves_actuales_por_galpon"])
    _fila_metrica_con_desglose("🥚", "Producción Hoy", resumen["produccion_hoy"], resumen["produccion_por_galpon"], porcentajes_por_galpon=resumen["porcentaje_produccion_hoy_por_galpon"])
    _fila_metrica_con_desglose("💀", "Mortalidad del Mes", resumen["mortalidad_mes"], resumen["mortalidad_por_galpon"])

    str_app.markdown("---")
    str_app.metric("💰 Cartera Pendiente", f"${resumen['cartera_pendiente']:,.0f}".replace(",", "."))
    str_app.markdown("<div style='margin-bottom:10px;'></div>", unsafe_allow_html=True)
    str_app.metric("💸 Gastos del Mes", f"${resumen['gastos_mes']:,.0f}".replace(",", "."))
    str_app.markdown("<div style='margin-bottom:10px;'></div>", unsafe_allow_html=True)
    str_app.metric("📈 Ventas del Mes", f"${resumen['ventas_mes']:,.0f}".replace(",", "."))

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

                        # Contador usado para "reiniciar" los campos tras guardar: al cambiar,
                        # Streamlit crea widgets nuevos (con sus valores por defecto) en vez de
                        # reutilizar lo que había quedado escrito.
                        if "reset_ctr_entrada_stock" not in str_app.session_state:
                            str_app.session_state["reset_ctr_entrada_stock"] = 0
                        ctr_es = str_app.session_state["reset_ctr_entrada_stock"]

                        galpon_destino = str_app.selectbox("Seleccione el Galpón de Destino", GALPONES, key=f"galpon_destino_entrada_{ctr_es}")
                        fecha_entrada = str_app.date_input("Fecha de la Entrada", value=date.today(), key=f"fecha_entrada_stock_{ctr_es}")

                        df_base_entrada = pd.DataFrame([{"Clasificación": "a", "Cantidad": 0}])
                        df_entrada_editado = str_app.data_editor(
                            df_base_entrada, num_rows="dynamic",
                            column_config={
                                "Clasificación": str_app.column_config.SelectboxColumn("Clasificación", options=CLASIFICACIONES, required=True),
                                "Cantidad": str_app.column_config.NumberColumn("Cantidad (Huevos)", min_value=1, step=1, format="%d", required=True)
                            },
                            use_container_width=True, key=f"editor_entradas_stock_{ctr_es}"
                        )

                        if str_app.button("➕ Registrar Entrada al Inventario", key=f"btn_registrar_entrada_{ctr_es}"):
                            entradas_validas = df_entrada_editado[df_entrada_editado["Cantidad"] > 0].copy()
                            if entradas_validas.empty:
                                str_app.warning("Debe ingresar al menos un ítem con cantidad mayor a 0.")
                            else:
                                lista_items_entrada = [{"Clasificación": r["Clasificación"], "Cantidad": int(r["Cantidad"])} for _, r in entradas_validas.iterrows()]
                                if registrar_entrada_inventario(galpon_destino, lista_items_entrada, fecha_entrada):
                                    str_app.toast("¡Registrado con éxito! 🎉", icon="✅")
                                    str_app.success(f"¡Entrada de inventario registrada correctamente en {galpon_destino} el {fecha_entrada}!")
                                    str_app.session_state["reset_ctr_entrada_stock"] += 1
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
                            
                            str_app.markdown("---")
                            str_app.markdown("#### ✏️ Editar una Entrada de Stock Registrada")
                            for _, row_he in df_hist_filtrado.iterrows():
                                with str_app.expander(f"📅 {row_he['fecha']} | {row_he['galpon']} | {row_he['clasificacion'].upper()} | Cantidad: {row_he['cantidad']:,}".replace(",", ".")):
                                    if rol_actual == "Administrador":
                                        with str_app.form(f"form_edit_he_{row_he['id']}", clear_on_submit=True):
                                            e_fecha = str_app.date_input("Fecha", value=row_he['fecha'], key=f"ef_{row_he['id']}")
                                            e_galpon = str_app.selectbox("Galpón", GALPONES, index=GALPONES.index(row_he['galpon']) if row_he['galpon'] in GALPONES else 0, key=f"eg_{row_he['id']}")
                                            e_clasif = str_app.selectbox("Clasificación", CLASIFICACIONES, index=CLASIFICACIONES.index(row_he['clasificacion'].lower()) if row_he['clasificacion'].lower() in CLASIFICACIONES else 0, key=f"ec_{row_he['id']}")
                                            e_cant = str_app.number_input("Cantidad", min_value=1, value=int(row_he['cantidad']), step=1, key=f"ecan_{row_he['id']}")
                                            if str_app.form_submit_button("💾 Guardar Cambios de Entrada"):
                                                try:
                                                    if actualizar_historial_entrada(int(row_he['id']), e_galpon, e_clasif, int(e_cant), e_fecha):
                                                        str_app.toast("¡Entrada actualizada con éxito! 🎉", icon="✅")
                                                        str_app.success("¡Modificación guardada y stock ajustado correctamente!")
                                                        str_app.rerun()
                                                except ValueError as ve:
                                                    str_app.error(str(ve))
                                    else:
                                        str_app.warning("👀 Modo Invitado: No tienes permisos para editar.")
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
                    str_app.subheader("💸 Control de Gastos")
                    tab_g_galpones, tab_g_camion = str_app.tabs(["🐔 Gastos de Galpones", "🚚 Gastos del Camión"])

                    with tab_g_galpones:
                        if rol_actual == "Invitado":
                            str_app.warning("👀 Modo Invitado: Solo lectura.")
                        else:
                            with str_app.form(key="form_registrar_gasto", clear_on_submit=True):
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
                                    str_app.download_button("📄 PDF de todos los galpones", data=pdf_gastos_buf, file_name=f"Gastos_{mes_nombre_sel}_{anio_sel_g}.pdf", mime="application/pdf")
                                with c_xls:
                                    boton_exportar_excel(df_gf[["fecha", "galpon", "categoria", "descripcion", "valor"]], f"Gastos_{mes_nombre_sel}_{anio_sel_g}.xlsx")

                                # --- PDF SEPARADO POR GALPÓN ---
                                str_app.markdown("##### 📄 PDF separado por galpón")
                                galpones_con_gastos = [g for g in GALPONES_GASTOS if g in df_gf["galpon"].values]
                                cols_pdf_galpon = str_app.columns(2)
                                for i, g in enumerate(galpones_con_gastos):
                                    df_g = df_gf[df_gf["galpon"] == g]
                                    pdf_g_buf = generar_pdf_gastos(df_g, f"Gastos {g} - {mes_nombre_sel} {anio_sel_g}")
                                    nombre_g = g.replace(" / ", "_").replace(" ", "_")
                                    cols_pdf_galpon[i % 2].download_button(
                                        f"📄 {g}", data=pdf_g_buf,
                                        file_name=f"Gastos_{nombre_g}_{mes_nombre_sel}_{anio_sel_g}.pdf",
                                        mime="application/pdf",
                                        key=f"dl_gastos_{nombre_g}_{anio_sel_g}_{mes_num_sel}"
                                    )
                                str_app.markdown("---")

                            for _, row_g in df_gf.iterrows():
                                with str_app.expander(f"📅 {row_g['fecha']} — [{row_g['galpon']}] {row_g['categoria']}: ${float(row_g['valor']):,.0f}".replace(",", ".")):
                                    str_app.write(f"**Desc:** {row_g['descripcion']}")
                                    if rol_actual == "Administrador":
                                        if confirmar_eliminacion(f"gasto_{row_g['id']}", etiqueta="🗑️ Eliminar Gasto"):
                                            eliminar_gasto(row_g['id'])
                                            str_app.rerun()

                    with tab_g_camion:
                        str_app.markdown("#### 🚚 Gastos del Camión")
                        if rol_actual == "Invitado":
                            str_app.warning("👀 Modo Invitado: Solo lectura.")
                        else:
                            with str_app.form(key="form_registrar_gasto_camion", clear_on_submit=True):
                                c_fecha_gc = str_app.date_input("Fecha del Gasto", value=date.today(), key="fecha_gasto_camion")
                                c_cat_gc = str_app.selectbox("Categoría de Gasto", CATEGORIAS_GASTO_CAMION, key="cat_gasto_camion")
                                c_desc_gc = str_app.text_input("Descripción del Gasto", placeholder="Ej. Tanqueada ACPM, cambio de aceite, peaje Chiquinquirá", key="desc_gasto_camion")
                                c_valor_gc = str_app.number_input("Valor ($)", min_value=0.0, step=1000.0, format="%.0f", key="valor_gasto_camion")

                                if str_app.form_submit_button("💾 Guardar Gasto del Camión"):
                                    if c_valor_gc <= 0:
                                        str_app.error("El valor del gasto debe ser mayor a 0.")
                                    elif not c_desc_gc.strip():
                                        str_app.error("Debes escribir una descripción del gasto.")
                                    else:
                                        if registrar_gasto_camion(c_fecha_gc, c_cat_gc, c_desc_gc, c_valor_gc):
                                            str_app.toast("¡Registrado con éxito! 🎉", icon="✅")
                                            str_app.success("¡Gasto del camión registrado con éxito!")
                                            str_app.rerun()

                        str_app.markdown("---")
                        df_gastos_camion = cargar_gastos_camion()
                        if not df_gastos_camion.empty:
                            df_gastos_camion['dt_fecha'] = pd.to_datetime(df_gastos_camion['fecha'])
                            df_gastos_camion['Año'] = df_gastos_camion['dt_fecha'].dt.year
                            df_gastos_camion['Mes_Num'] = df_gastos_camion['dt_fecha'].dt.month

                            c_fc1, c_fc2 = str_app.columns(2)
                            anio_sel_gc = c_fc1.selectbox("📅 Año (Camión)", sorted(df_gastos_camion['Año'].unique().tolist(), reverse=True), key="anio_gasto_camion")
                            mes_nombre_sel_gc = c_fc2.selectbox("📅 Mes (Camión)", list(MESES_NOMBRES.values()), index=date.today().month - 1, key="mes_gasto_camion")
                            mes_num_sel_gc = [k for k, v in MESES_NOMBRES.items() if v == mes_nombre_sel_gc][0]

                            df_gcf = df_gastos_camion[(df_gastos_camion['Año'] == anio_sel_gc) & (df_gastos_camion['Mes_Num'] == mes_num_sel_gc)]
                            str_app.markdown(f"**Total Gastos Camión del Mes:** ${df_gcf['valor'].sum():,.0f}".replace(",", "."))

                            if not df_gcf.empty:
                                c_pdf_gc, c_xls_gc = str_app.columns(2)
                                with c_pdf_gc:
                                    pdf_gc_buf = generar_pdf_gastos(df_gcf, f"Gastos del Camión - {mes_nombre_sel_gc} {anio_sel_gc}")
                                    str_app.download_button("📄 Descargar en PDF", data=pdf_gc_buf, file_name=f"Gastos_Camion_{mes_nombre_sel_gc}_{anio_sel_gc}.pdf", mime="application/pdf", key="dl_pdf_gastos_camion")
                                with c_xls_gc:
                                    boton_exportar_excel(df_gcf[["fecha", "categoria", "descripcion", "valor"]], f"Gastos_Camion_{mes_nombre_sel_gc}_{anio_sel_gc}.xlsx", key="dl_xls_gastos_camion")

                                str_app.markdown("##### 📋 Resumen por categoría")
                                df_resumen_gc = df_gcf.groupby("categoria", as_index=False)["valor"].sum().sort_values("valor", ascending=False)
                                df_resumen_gc["valor"] = df_resumen_gc["valor"].apply(lambda x: f"$ {float(x):,.0f}".replace(",", "."))
                                df_resumen_gc.columns = ["Categoría", "Total ($)"]
                                str_app.dataframe(df_resumen_gc, use_container_width=True, hide_index=True)
                                str_app.markdown("---")

                            for _, row_gc in df_gcf.iterrows():
                                with str_app.expander(f"📅 {row_gc['fecha']} — {row_gc['categoria']}: ${float(row_gc['valor']):,.0f}".replace(",", ".")):
                                    str_app.write(f"**Desc:** {row_gc['descripcion']}")
                                    if rol_actual == "Administrador":
                                        if confirmar_eliminacion(f"gasto_camion_{row_gc['id']}", etiqueta="🗑️ Eliminar Gasto del Camión"):
                                            eliminar_gasto_camion(row_gc['id'])
                                            str_app.rerun()
                        else:
                            str_app.info("Aún no hay gastos del camión registrados.")

                # ---------------- GASTOS VARIOS ----------------
                elif str_app.session_state.seccion_activa == "🏷️ Gastos Varios":
                    str_app.subheader("🏷️ Control de Gastos Varios y Personales")
                    if rol_actual == "Invitado":
                        str_app.warning("👀 Modo Invitado: Solo lectura.")
                    else:
                        with str_app.form(key="form_registrar_gv", clear_on_submit=True):
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
                            with str_app.form("form_cli_nuevo", clear_on_submit=True):
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
                                with str_app.form("form_cli_editar", clear_on_submit=True):
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
                                    cols_abono = ['fecha_abono', 'monto', 'nombre_comprobante']
                                    nombres_cols = ['Fecha y Hora', 'Monto ($)', 'Comprobante']
                                    if 'observacion' in df_abonos.columns:
                                        cols_abono.append('observacion')
                                        nombres_cols.append('Observación')

                                    df_abonos_mostrar = df_abonos[cols_abono].copy()
                                    df_abonos_mostrar.columns = nombres_cols
                                    df_abonos_mostrar['Monto ($)'] = df_abonos_mostrar['Monto ($)'].apply(lambda x: f"${float(x):,.0f}".replace(",", "."))
                                    str_app.dataframe(df_abonos_mostrar, use_container_width=True, hide_index=True)
                                else:
                                    str_app.info("No hay abonos registrados para esta remisión.")

                                str_app.markdown("---")
                                if rol_actual == "Administrador" and float(row['saldo']) > 0:
                                    with str_app.form(key=f"ab_{row['num_remision']}", clear_on_submit=True):
                                        str_app.markdown("#### ➕ Registrar Nuevo Abono")
                                        monto = str_app.number_input("Abono ($)", min_value=0.0, max_value=float(row['saldo']), step=1000.0, format="%.0f")
                                        obs_abono = str_app.text_input("Observación / Nota (Opcional)", key=f"obs_{row['num_remision']}")
                                        arch = str_app.file_uploader("Comprobante (Opcional)", type=["png", "jpg", "jpeg", "pdf"], key=f"f_{row['num_remision']}")
                                        if str_app.form_submit_button("Registrar Abono"):
                                            if monto <= 0:
                                                str_app.error("El monto del abono debe ser mayor a 0.")
                                            else:
                                                if registrar_abono(int(row['num_remision']), monto, arch.read() if arch else None, arch.name if arch else None, obs_abono):
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
                                    conductor = str(f_sel.get('conductor', 'Ivan Herrera'))

                                    pdf_buf = generar_pdf_remision(int(num_sel), fecha_str, conductor, cliente_datos, items_pdf, total_factura)
                                    str_app.download_button(f"📄 Descargar Remisión #{int(num_sel):06d}", data=pdf_buf, file_name=f"Remision_{int(num_sel):06d}.pdf", mime="application/pdf", key=f"dl_rem_{int(num_sel)}")

                                    if rol_actual == "Administrador":
                                        str_app.markdown("---")
                                        with str_app.expander("✏️ Editar esta Remisión"):
                                            with str_app.form(key=f"form_edit_rem_{int(num_sel)}"):
                                                e_fecha_rem = str_app.date_input("Fecha", value=pd.to_datetime(f_sel.get('fecha_emision', date.today())).date(), key=f"ef_rem_{int(num_sel)}")
                                                e_cliente = str_app.text_input("Cliente", value=cliente_nombre, key=f"ec_rem_{int(num_sel)}")
                                                e_cedula = str_app.text_input("Cédula/NIT", value=str(f_sel.get('cedula_nit', '')), key=f"eced_rem_{int(num_sel)}")
                                                e_direccion = str_app.text_input("Dirección", value=str(f_sel.get('destino', 'CHOACHI')), key=f"edir_rem_{int(num_sel)}")
                                                e_telefono = str_app.text_input("Teléfono", value=str(f_sel.get('telefono', '')), key=f"etel_rem_{int(num_sel)}")
                                                e_email = str_app.text_input("Email", value=str(f_sel.get('email', '')), key=f"eem_rem_{int(num_sel)}")
                                                e_conductor = str_app.text_input("Conductor", value=conductor, key=f"econd_rem_{int(num_sel)}")

                                                items_existentes = []
                                                for _, row_item in df_r.iterrows():
                                                    items_existentes.append({
                                                        "Clasificación": str(row_item.get('tipo_huevo', 'a')).lower(),
                                                        "Cantidad (Huevos)": int(row_item.get('cantidad', 0)),
                                                        "Precio Unitario ($)": float(row_item.get('precio_unitario', 0)),
                                                        "Galpón Origen": str(row_item.get('galpon', GALPONES[0]))
                                                    })

                                                df_edit_base = pd.DataFrame(items_existentes)
                                                df_edit_rem = str_app.data_editor(
                                                    df_edit_base, num_rows="dynamic",
                                                    column_config={
                                                        "Clasificación": str_app.column_config.SelectboxColumn("Clasificación", options=CLASIFICACIONES, required=True),
                                                        "Cantidad (Huevos)": str_app.column_config.NumberColumn("Cantidad (Huevos)", min_value=1, step=1, format="%d", required=True),
                                                        "Precio Unitario ($)": str_app.column_config.NumberColumn("Precio Unitario ($)", min_value=0, format="$%d", required=True),
                                                        "Galpón Origen": str_app.column_config.SelectboxColumn("Galpón Origen", options=GALPONES, required=True)
                                                    },
                                                    use_container_width=True, key=f"editor_edit_rem_{int(num_sel)}"
                                                )

                                                if str_app.form_submit_button("💾 Guardar Cambios de Remisión"):
                                                    nuevos_items_validos = df_edit_rem[df_edit_rem["Cantidad (Huevos)"] > 0].copy()
                                                    if nuevos_items_validos.empty:
                                                        str_app.error("La remisión debe incluir al menos un ítem con cantidad mayor a 0.")
                                                    elif not e_cliente.strip():
                                                        str_app.error("El nombre del cliente es obligatorio.")
                                                    else:
                                                        nuevos_items_validos["Subtotal ($)"] = nuevos_items_validos["Cantidad (Huevos)"] * nuevos_items_validos["Precio Unitario ($)"]
                                                        lista_nuevos_items = [{
                                                            'Clasificación': r['Clasificación'],
                                                            'Cantidad (Huevos)': int(r['Cantidad (Huevos)']),
                                                            'Precio Unitario ($)': float(r['Precio Unitario ($)']),
                                                            'Subtotal ($)': float(r['Subtotal ($)']),
                                                            'Galpón': r['Galpón Origen']
                                                        } for _, r in nuevos_items_validos.iterrows()]

                                                        try:
                                                            if actualizar_remision(
                                                                int(num_sel), e_cliente, e_cedula, e_direccion,
                                                                e_telefono, e_email, e_conductor, e_fecha_rem, lista_nuevos_items
                                                            ):
                                                                str_app.toast("¡Remisión actualizada con éxito! 🎉", icon="✅")
                                                                str_app.success("¡Remisión y cartera actualizadas correctamente!")
                                                                str_app.rerun()
                                                        except ValueError as ve:
                                                            str_app.error(str(ve))

                    else:
                        str_app.info("No hay remisiones registradas.")

                # ---------------- UTILIDADES ----------------
                elif str_app.session_state.seccion_activa == "📈 Utilidades":
                    str_app.subheader("📈 Utilidades por Galpón")
                    df_rem_u = cargar_remisiones()
                    df_gas_u = cargar_gastos()

                    if df_rem_u.empty and df_gas_u.empty:
                        str_app.info("Aún no hay suficientes datos de ventas o gastos registrados.")
                    else:
                        datos_utilidad = []
                        for g in GALPONES:
                            ventas_g = float(df_rem_u[df_rem_u["galpon"] == g]["total"].sum()) if not df_rem_u.empty and "galpon" in df_rem_u.columns else 0.0
                            gastos_g = float(df_gas_u[df_gas_u["galpon"] == g]["valor"].sum()) if not df_gas_u.empty and "galpon" in df_gas_u.columns else 0.0
                            utilidad_g = ventas_g - gastos_g
                            datos_utilidad.append({
                                "Galpón": g,
                                "Ventas ($)": ventas_g,
                                "Gastos ($)": gastos_g,
                                "Utilidad ($)": utilidad_g
                            })

                        df_utilidad = pd.DataFrame(datos_utilidad)
                        
                        df_utilidad_mostrar = df_utilidad.copy()
                        for col_m in ["Ventas ($)", "Gastos ($)", "Utilidad ($)"]:
                            df_utilidad_mostrar[col_m] = df_utilidad_mostrar[col_m].apply(lambda x: f"${x:,.0f}".replace(",", "."))

                        str_app.dataframe(df_utilidad_mostrar, use_container_width=True, hide_index=True)
                        boton_exportar_excel(df_utilidad, "Utilidades_por_Galpon.xlsx")

        # ---------------- REGISTRO DIARIO ----------------
        elif str_app.session_state.sesion_principal == "📝 Registro Diario":
            str_app.subheader("📝 Registro Diario de Galpones")

            galpon_reg_sel = str_app.selectbox("Seleccione el Galpón", GALPONES)
            config_actual = cargar_config_galpon(galpon_reg_sel)

            if rol_actual == "Administrador":
                with str_app.expander("⚙️ Configuración Inicial del Galpón"):
                    with str_app.form("form_config_galpon"):
                        sem_ini = str_app.number_input("Edad Inicial (Semanas)", min_value=0, value=config_actual['edad_semanas'] if config_actual else 0)
                        dias_ini = str_app.number_input("Edad Inicial (Días extra)", min_value=0, max_value=6, value=config_actual['edad_dias'] if config_actual else 0)
                        aves_ini = str_app.number_input("Aves Iniciales", min_value=0, value=config_actual['aves_iniciales'] if config_actual else 0)
                        if str_app.form_submit_button("💾 Guardar Configuración"):
                            if guardar_config_galpon(galpon_reg_sel, sem_ini, dias_ini, aves_ini):
                                str_app.toast("¡Configuración guardada! 🎉", icon="✅")
                                str_app.success("Configuración actualizada.")
                                str_app.rerun()

            df_reg_galpon = cargar_registros_diarios(galpon_reg_sel)

            mortalidad_acumulada = df_reg_galpon["mortalidad"].sum() if not df_reg_galpon.empty else 0
            aves_iniciales_val = config_actual['aves_iniciales'] if config_actual else 0
            aves_actuales = max(0, aves_iniciales_val - mortalidad_acumulada)

            conc_ingresado_tot = df_reg_galpon["concentrado_ingresado"].sum() if not df_reg_galpon.empty else 0.0
            conc_consumido_tot = df_reg_galpon["concentrado_consumido"].sum() if not df_reg_galpon.empty else 0.0
            saldo_concentrado = conc_ingresado_tot - conc_consumido_tot

            if not df_reg_galpon.empty and config_actual:
                dias_transcurridos = len(df_reg_galpon['fecha'].unique())
                dias_totales = (config_actual['edad_semanas'] * 7) + config_actual['edad_dias'] + dias_transcurridos
                semanas_act = dias_totales // 7
                dias_act = dias_totales % 7
                edad_str = f"{semanas_act} semanas y {dias_act} días"
            elif config_actual:
                edad_str = f"{config_actual['edad_semanas']} semanas y {config_actual['edad_dias']} días"
            else:
                edad_str = "Sin configurar"

            c_met1, c_met2 = str_app.columns(2)
            c_met1.metric("🐔 Aves Actuales", f"{aves_actuales:,}".replace(",", "."))
            c_met2.metric("📦 Saldo Concentrado", f"{saldo_concentrado:,.1f} bultos".replace(",", "."))
            str_app.caption(f"<b>Edad Actual Estimada:</b> {edad_str}", unsafe_allow_html=True)

            str_app.markdown("---")
            if rol_actual == "Invitado":
                str_app.warning("👀 Modo Invitado: Solo lectura.")
            else:
                str_app.markdown("#### ➕ Registrar Día")
                with str_app.form("form_reg_diario", clear_on_submit=True):
                    f_diario = str_app.date_input("Fecha", value=date.today())
                    mort_d = str_app.number_input("Mortalidad (Aves)", min_value=0, step=1)
                    c_ing_d = str_app.number_input("Ingreso Concentrado (Bultos)", min_value=0.0, step=0.5)
                    c_con_d = str_app.number_input("Consumo Concentrado (Bultos)", min_value=0.0, step=0.5)
                    huev_d = str_app.number_input("Huevos Recolectados", min_value=0, step=1)
                    obs_d = str_app.text_input("Observaciones (Opcional)")

                    if str_app.form_submit_button("💾 Guardar Registro Diario"):
                        if registrar_dia_galpon(f_diario, galpon_reg_sel, mort_d, c_ing_d, c_con_d, huev_d, obs_d):
                            str_app.toast("¡Registrado con éxito! 🎉", icon="✅")
                            str_app.success("Día registrado con éxito!")
                            str_app.rerun()

            str_app.markdown("---")
            str_app.markdown("#### 📜 Historial del Galpón")
            if not df_reg_galpon.empty:
                c_pdf_r, c_xls_r = str_app.columns(2)
                with c_pdf_r:
                    pdf_reg_buf = generar_pdf_registro_diario(galpon_reg_sel, config_actual, df_reg_galpon, edad_str, aves_actuales, saldo_concentrado)
                    str_app.download_button("📄 Descargar Reporte PDF", data=pdf_reg_buf, file_name=f"Registro_{galpon_reg_sel}.pdf", mime="application/pdf")
                with c_xls_r:
                    boton_exportar_excel(df_reg_galpon[["fecha", "mortalidad", "concentrado_ingresado", "concentrado_consumido", "huevos_recolectados", "observaciones"]], f"Registro_{galpon_reg_sel}.xlsx")

                for _, r_d in df_reg_galpon.iterrows():
                    with str_app.expander(f"📅 {r_d['fecha']} — Huevos: {int(r_d['huevos_recolectados']):,} | Mort: {int(r_d['mortalidad'])}".replace(",", ".")):
                        str_app.write(f"Ingreso Conc: {r_d['concentrado_ingresado']} bultos | Consumo Conc: {r_d['concentrado_consumido']} bultos")
                        if r_d.get('observaciones'):
                            str_app.write(f"**Obs:** {r_d['observaciones']}")
                        if rol_actual == "Administrador":
                            if confirmar_eliminacion(f"reg_d_{r_d['id']}", etiqueta="🗑️ Eliminar Registro"):
                                eliminar_registro_diario(r_d['id'])
                                str_app.rerun()
            else:
                str_app.info("No hay registros diarios para este galpón.")

    except Exception as e:
        str_app.error(f"⚠️ Ha ocurrido un error inesperado en la aplicación.\n\nDetalle: {e}")
