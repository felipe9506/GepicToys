from functools import wraps
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash
from models import db, User, Order, OrderItem, Product
from sqlalchemy import func

manager_bp = Blueprint('manager', __name__, url_prefix='/manager')

def gerente_required(f):
    """Decorador que bloquea el acceso a no-gerentes"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if current_user.role != 'gerente':
            flash('Acceso restringido al gerente', 'error')
            return redirect(url_for('sales.dashboard'))
        return f(*args, **kwargs)
    return decorated

@manager_bp.route('/panel')
@login_required
@gerente_required
def panel():
    # Resumen de ventas por vendedor
    resumen = (db.session.query(
        User.username,
        func.count(OrderItem.id).label('num_ventas'),
        func.sum(OrderItem.subtotal).label('total')
    ).join(OrderItem, OrderItem.seller_id == User.id)
     .group_by(User.id)
     .all())

    # Total global de todas las ventas
    total_global = db.session.query(
        func.sum(OrderItem.subtotal)
    ).scalar() or 0

    # Producto más vendido
    top_producto = (db.session.query(
        Product.name,
        func.sum(OrderItem.quantity).label('vendidos')
    ).join(OrderItem, OrderItem.product_id == Product.id)
     .group_by(Product.id)
     .order_by(func.sum(OrderItem.quantity).desc())
     .first())

    # Todos los pedidos
    orders = Order.query.order_by(Order.date.desc()).all()

    return render_template('manager_panel.html',
                           resumen=resumen,
                           total_global=total_global,
                           top_producto=top_producto,
                           orders=orders)

@manager_bp.route('/vendedor/<int:user_id>')
@login_required
@gerente_required
def ver_vendedor(user_id):
    vendedor = User.query.get_or_404(user_id)
    items = (OrderItem.query
             .filter_by(seller_id=user_id)
             .order_by(OrderItem.id.desc())
             .all())
    total = sum(i.subtotal for i in items)
    return render_template('ver_vendedor.html',
                           vendedor=vendedor,
                           items=items,
                           total=total)

@manager_bp.route('/orders/<int:order_id>/status', methods=['POST'])
@login_required
@gerente_required
def cambiar_estado(order_id):
    order = Order.query.get_or_404(order_id)
    order.status = request.form.get('status')
    db.session.commit()
    flash(f'Pedido #{order_id} actualizado a "{order.status}" ✅', 'success')
    return redirect(url_for('manager.panel'))

@manager_bp.route('/crear-vendedor', methods=['GET', 'POST'])
@login_required
@gerente_required
def crear_vendedor():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if User.query.filter_by(username=username).first():
            flash('Ese nombre de usuario ya existe', 'error')
        else:
            nuevo = User(
                username=username,
                password_hash=generate_password_hash(password),
                role='vendedor'
            )
            db.session.add(nuevo)
            db.session.commit()
            flash(f'Vendedor "{username}" creado ✅', 'success')
            return redirect(url_for('manager.panel'))

    return render_template('crear_vendedor.html')