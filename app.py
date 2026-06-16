from flask import Flask
from flask_login import LoginManager
from flask_migrate import Migrate
from dotenv import load_dotenv
from models import db, User
from werkzeug.security import generate_password_hash
import os

load_dotenv()

def create_app():
    app = Flask(__name__)

    app.config['SECRET_KEY']                     = os.getenv('SECRET_KEY', 'dev-secret')
    app.config['SQLALCHEMY_DATABASE_URI']        = os.getenv('DATABASE_URL', 'sqlite:///gepictoys.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['STRIPE_PUBLIC_KEY']              = os.getenv('STRIPE_PUBLIC_KEY')
    app.config['STRIPE_SECRET_KEY']              = os.getenv('STRIPE_SECRET_KEY')
    app.config['STRIPE_WEBHOOK_SECRET']          = os.getenv('STRIPE_WEBHOOK_SECRET')

    db.init_app(app)
    Migrate(app, db)

    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view    = 'auth.login'
    login_manager.login_message = 'Debes iniciar sesión para acceder.'

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # ── Filtro para precios en pesos colombianos ───────────────
    @app.template_filter('cop')
    def formato_cop(valor):
        # Ejemplo: 89900 → "$ 89.900 COP"
        return f"$ {valor:,.0f} COP"

    # ── Blueprints ─────────────────────────────────────────────
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