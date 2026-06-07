# ── auth.py ────────────────────────────────────────────────────
# Maneja el inicio y cierre de sesión de vendedores y gerentes.
# Los clientes NO necesitan login para comprar.

from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash
from models import User

# Blueprint con prefijo vacío (rutas en la raíz: /login, /logout)
auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/')
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    # Si ya está logueado, redirigir según su rol
    if current_user.is_authenticated:
        if current_user.role == 'gerente':
            return redirect(url_for('manager.panel'))
        return redirect(url_for('sales.dashboard'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        # Buscar el usuario en la base de datos
        user = User.query.filter_by(username=username).first()

        # check_password_hash compara la contraseña con el hash guardado
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            # Redirigir según el rol del usuario
            if user.role == 'gerente':
                return redirect(url_for('manager.panel'))
            return redirect(url_for('sales.dashboard'))
        else:
            flash('Usuario o contraseña incorrectos', 'error')

    return render_template('login.html')

@auth_bp.route('/logout')
@login_required  # solo usuarios logueados pueden cerrar sesión
def logout():
    logout_user()
    flash('Sesión cerrada correctamente', 'info')
    return redirect(url_for('auth.login'))