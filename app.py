# ── app.py ─────────────────────────────────────────────────────
# Punto de entrada principal de la aplicación Flask.
# Usa el patrón Application Factory (create_app) para facilitar
# pruebas y despliegue en producción.

from flask import Flask
from flask_login import LoginManager
from dotenv import load_dotenv
from models import db, User
from werkzeug.security import generate_password_hash
import os

# Carga las variables del archivo .env (claves secretas, Stripe, etc.)
load_dotenv()

def create_app():
    app = Flask(__name__)

    # ── Configuración ──────────────────────────────────────────
    app.config['SECRET_KEY']                = os.getenv('SECRET_KEY', 'dev-secret')
    app.config['SQLALCHEMY_DATABASE_URI']   = 'sqlite:///gepictoys.db'  # base de datos local SQLite
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False                # evita warnings innecesarios
    app.config['STRIPE_PUBLIC_KEY']         = os.getenv('STRIPE_PUBLIC_KEY')   # clave pública Stripe (va al frontend)
    app.config['STRIPE_SECRET_KEY']         = os.getenv('STRIPE_SECRET_KEY')   # clave secreta Stripe (solo backend)
    app.config['STRIPE_WEBHOOK_SECRET']     = os.getenv('STRIPE_WEBHOOK_SECRET') # verifica webhooks de Stripe

    # ── Base de datos ──────────────────────────────────────────
    db.init_app(app)

    # ── Sistema de login ───────────────────────────────────────
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view    = 'auth.login'          # redirige aquí si no está autenticado
    login_manager.login_message = 'Debes iniciar sesión para acceder.'

    @login_manager.user_loader
    def load_user(user_id):
        # Flask-Login llama esto en cada request para cargar el usuario actual
        return User.query.get(int(user_id))

    # ── Filtro de precios en COP ───────────────────────────────
    @app.template_filter('cop')
    def formato_cop(valor):
        # Convierte 89900 → "$ 89.900 COP"
        return f"$ {valor:,.0f} COP"

    # ── Blueprints (módulos de rutas) ──────────────────────────
    # Cada blueprint maneja una sección de la app por separado
    from auth     import auth_bp
    from products import products_bp
    from sales    import sales_bp
    from manager  import manager_bp
    from store    import store_bp
    from payments import payments_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(products_bp)
    app.register_blueprint(sales_bp)
    app.register_blueprint(manager_bp)
    app.register_blueprint(store_bp)
    app.register_blueprint(payments_bp)

    # ── Inicialización ─────────────────────────────────────────
    with app.app_context():
        db.create_all()      # crea las tablas si no existen
        _seed_usuarios()     # crea usuarios de prueba si la BD está vacía

    return app

def _seed_usuarios():
    """
    Crea usuarios iniciales de prueba si la base de datos está vacía.
    Solo se ejecuta una vez al arrancar por primera vez.
    """
    if not User.query.first():
        db.session.add_all([
            User(
                username='gerente',
                password_hash=generate_password_hash('admin123'),
                role='gerente'
            ),
            User(
                username='vendedor1',
                password_hash=generate_password_hash('venta123'),
                role='vendedor'
            ),
        ])
        db.session.commit()
        print("✅ Usuarios creados: gerente/admin123 | vendedor1/venta123")

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)  # debug=True solo en desarrollo, nunca en producción