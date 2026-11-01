import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def obtener_conexion():

    """
    Establece conexión con la base de datos PostgreSQL en Supabase.
    Retorna la conexión activa o None si no hay credenciales configuradas.
    """
    host = os.getenv("DB_HOST", "localhost")
    database = os.getenv("DB_NAME", "postgres")
    if database == "post":
        database = "postgres"
    user = os.getenv("DB_USER", "postgres")
    password = os.getenv("DB_PASSWORD", "")
    port = os.getenv("DB_PORT", "5432")


    if not password and host == "localhost":
        return None

    try:
        conexion = psycopg2.connect(
            host=host,
            database=database,
            user=user,
            password=password,
            port=port,
            connect_timeout=3
        )
        return conexion
    except Exception as e:
        print(f"[con_db] No se pudo conectar a PostgreSQL ({e}). Usando almacén en memoria.")
        return None
