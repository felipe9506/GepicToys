from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    """
    Tabla de usuarios internos (vendedores y gerentes).
    Los clientes NO se registran, compran como invitados.
    """
    id            = db.Column(db.Integer, primary_key=True)
    username      = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role          = db.Column(db.String(20), nullable=False, default='vendedor')

class Product(db.Model):
    """
    Tabla de productos (muñecos anime).
    active=False oculta el producto sin eliminarlo.
    """
    id          = db.Column(db.Integer, primary_key=True)
    name        = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text)
    price       = db.Column(db.Float, nullable=False)
    stock       = db.Column(db.Integer, default=0)
    image_url   = db.Column(db.String(300))
    created_by  = db.Column(db.Integer, db.ForeignKey('user.id'))
    active      = db.Column(db.Boolean, default=True)

class Order(db.Model):
    """
    Tabla de pedidos de clientes invitados.
    Soporta pago con Stripe o contra entrega.
    """
    id                    = db.Column(db.Integer, primary_key=True)
    customer_name         = db.Column(db.String(120), nullable=False)
    customer_email        = db.Column(db.String(120), nullable=False)
    customer_phone        = db.Column(db.String(30))
    customer_address      = db.Column(db.Text)
    stripe_payment_intent = db.Column(db.String(200))
    payment_method        = db.Column(db.String(30), default='stripe')
    # Valores posibles: 'stripe' o 'contra_entrega'
    status                = db.Column(db.String(30), default='pendiente')
    # Estados: pendiente → pagado → enviado → cancelado
    total                 = db.Column(db.Float, nullable=False)
    date                  = db.Column(db.DateTime, default=datetime.utcnow)
    items                 = db.relationship('OrderItem', backref='order', lazy=True)

class OrderItem(db.Model):
    """
    Cada producto dentro de un pedido.
    Permite saber qué vendió cada vendedor.
    """
    id         = db.Column(db.Integer, primary_key=True)
    order_id   = db.Column(db.Integer, db.ForeignKey('order.id'),   nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    seller_id  = db.Column(db.Integer, db.ForeignKey('user.id'))
    quantity   = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Float,   nullable=False)
    subtotal   = db.Column(db.Float,   nullable=False)
    product    = db.relationship('Product')