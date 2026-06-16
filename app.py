from flask import Flask
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_mail import Mail
from dotenv import load_dotenv
from models import db, User
from werkzeug.security import generate_password_hash
import os

load_dotenv()

mail = Mail()

def create_app():
    app = Flask(__name__)

    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret')

    # ── Base de datos ──────────────────────────────────────────
    database_url = os.getenv('DATABASE_URL', 'sqlite:///gepictoys.db')
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)

    app.config['SQLALCHEMY_DATABASE_URI']        = database_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # ── Opciones de conexión para Supabase ─────────────────────
    # pool_pre_ping verifica la conexión antes de usarla
    # pool_recycle reconecta cada 5 minutos para evitar cortes SSL
    if 'supabase' in database_url:
        app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
            'pool_pre_ping':  True,
            'pool_recycle':   300,
            'pool_size':      5,
            'max_overflow':   2,
            'connect_args': {
                'sslmode':         'require',
                'connect_timeout': 10,
                'keepalives':      1,
                'keepalives_idle': 30,
                'keepalives_interval': 10,
                'keepalives_count': 5,
            }
        }
    else:
        app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
            'pool_pre_ping': True,
            'pool_recycle':  300,
        }

    # ── Stripe ─────────────────────────────────────────────────
    app.config['STRIPE_PUBLIC_KEY']   = os.getenv('STRIPE_PUBLIC_KEY')
    app.config['STRIPE_SECRET_KEY']   = os.getenv('STRIPE_SECRET_KEY')
    app.config['STRIPE_WEBHOOK_SECRET'] = os.getenv('STRIPE_WEBHOOK_SECRET')

    # ── Flask-Mail ─────────────────────────────────────────────
    app.config['MAIL_SERVER']         = 'smtp.gmail.com'
    app.config['MAIL_PORT']           = 587
    app.config['MAIL_USE_TLS']        = True
    app.config['MAIL_USERNAME']       = os.getenv('MAIL_USERNAME')
    app.config['MAIL_PASSWORD']       = os.getenv('MAIL_PASSWORD')
    app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_USERNAME')

    db.init_app(app)
    Migrate(app, db)
    mail.init_app(app)

    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view    = 'auth.login'
    login_manager.login_message = 'Debes iniciar sesión para acceder.'

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    @app.template_filter('cop')
    def formato_cop(valor):
        return f"$ {valor:,.0f} COP"

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

    with app.app_context():
        db.create_all()
        _seed_usuarios()

    return app

def _seed_usuarios():
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
    app.run(debug=True)