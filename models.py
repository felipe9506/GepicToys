# ── models.py ──────────────────────────────────────────────────
# Define la estructura de la base de datos usando SQLAlchemy.
# Cada clase representa una tabla en la base de datos.

from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    """
    Tabla de usuarios internos (vendedores y gerentes).
    Los clientes NO se registran, compran como invitados.
    UserMixin agrega métodos necesarios para Flask-Login.
    """
    id            = db.Column(db.Integer, primary_key=True)
    username      = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)  # contraseña encriptada, nunca en texto plano
    role          = db.Column(db.String(20), nullable=False, default='vendedor')  # 'gerente' o 'vendedor'

class Product(db.Model):
    """
    Tabla de productos (muñecos anime).
    El campo active permite ocultar productos sin eliminarlos.
    """
    id          = db.Column(db.Integer, primary_key=True)
    name        = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text)
    price       = db.Column(db.Float, nullable=False)           # precio en pesos colombianos
    stock       = db.Column(db.Integer, default=0)              # unidades disponibles
    image_url   = db.Column(db.String(300))                     # ruta local o URL externa
    created_by  = db.Column(db.Integer, db.ForeignKey('user.id'))  # vendedor que creó el producto
    active      = db.Column(db.Boolean, default=True)           # False = oculto en la tienda

class Order(db.Model):
    """
    Tabla de pedidos de clientes invitados.
    Un pedido agrupa varios productos comprados en una sola transacción.
    """
    id                     = db.Column(db.Integer, primary_key=True)
    # Datos del cliente recogidos en el formulario de checkout
    customer_name          = db.Column(db.String(120), nullable=False)
    customer_email         = db.Column(db.String(120), nullable=False)
    customer_phone         = db.Column(db.String(30))
    customer_address       = db.Column(db.Text)
    # Datos del pago procesado por Stripe
    stripe_payment_intent  = db.Column(db.String(200))          # ID único del pago en Stripe
    status                 = db.Column(db.String(30), default='pendiente')
    # Estados posibles: pendiente → pagado → enviado → cancelado
    total                  = db.Column(db.Float, nullable=False) # total en COP
    date                   = db.Column(db.DateTime, default=datetime.utcnow)
    # Relación: un pedido tiene muchos items
    items                  = db.relationship('OrderItem', backref='order', lazy=True)

class OrderItem(db.Model):
    """
    Tabla de items dentro de un pedido.
    Separa los productos para saber qué vendió cada vendedor.
    Ejemplo: un pedido puede tener Naruto (vendedor1) y Goku (vendedor2).
    """
    id         = db.Column(db.Integer, primary_key=True)
    order_id   = db.Column(db.Integer, db.ForeignKey('order.id'),   nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    seller_id  = db.Column(db.Integer, db.ForeignKey('user.id'))    # vendedor dueño del producto
    quantity   = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Float,   nullable=False)  # precio al momento de comprar (puede cambiar después)
    subtotal   = db.Column(db.Float,   nullable=False)  # unit_price × quantity
    product    = db.relationship('Product')             # acceso directo al producto desde el item