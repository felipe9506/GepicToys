from flask import Blueprint, render_template
from flask_login import login_required, current_user
from models import OrderItem, Order, db
from sqlalchemy import func
from datetime import date

sales_bp = Blueprint('sales', __name__, url_prefix='/sales')

@sales_bp.route('/dashboard')
@login_required
def dashboard():
    my_sales = (db.session.query(OrderItem)
                .join(Order, Order.id == OrderItem.order_id)
                .filter(OrderItem.seller_id == current_user.id)
                .order_by(Order.date.desc())
                .all())

    total = (db.session.query(func.sum(OrderItem.subtotal))
             .filter_by(seller_id=current_user.id)
             .scalar() or 0)

    ventas_hoy = (db.session.query(func.count(OrderItem.id))
                  .join(Order, Order.id == OrderItem.order_id)
                  .filter(
                      OrderItem.seller_id == current_user.id,
                      func.date(Order.date) == date.today()
                  ).scalar() or 0)

    return render_template('dashboard.html',
                           sales=my_sales,
                           total=total,
                           ventas_hoy=ventas_hoy)