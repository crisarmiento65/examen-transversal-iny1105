import os
import datetime
from flask import Flask
import psycopg2

app = Flask(__name__)

def get_db_connection():
    conn = psycopg2.connect(
        host=os.environ.get("DB_HOST", "db"),
        database=os.environ.get("DB_NAME", "vzeta"),
        user=os.environ.get("DB_USER", "vzeta_user"),
        password=os.environ.get("DB_PASSWORD", "vzeta_pass")
    )
    return conn

def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS visitas (
            id SERIAL PRIMARY KEY,
            fecha TIMESTAMP NOT NULL DEFAULT NOW()
        );
    """)
    conn.commit()
    cur.close()
    conn.close()

@app.route("/")
def index():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO visitas (fecha) VALUES (%s);", (datetime.datetime.now(),))
    conn.commit()
    cur.execute("SELECT COUNT(*) FROM visitas;")
    total = cur.fetchone()[0]
    cur.close()
    conn.close()
    return f"""
    <html>
    <head><title>VZeta - Contador de Visitas</title></head>
    <body style="font-family: Arial, sans-serif; text-align: center; margin-top: 50px;">
        <h1>VZeta - Aplicacion Web</h1>
        <h2>Contador de visitas: {total}</h2>
        <p>Ultima visita registrada: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        <hr>
        <p><small>Infraestructura de Aplicaciones I - INY1105 | Examen Transversal</small></p>
    </body>
    </html>
    """

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000)
