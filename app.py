from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import os
from elasticsearch import Elasticsearch
from sqlalchemy import func
from datetime import datetime


# ============================================================
# ЗАДАЧА 1: Создание Flask-проекта с подключением к БД
# ============================================================
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'supersecretkey'

# ============================================================
# ЗАДАЧА 2: Установка и настройка SQLAlchemy
# ============================================================
db = SQLAlchemy(app)

# ============================================================
# ЗАДАЧА 15: Flask-Migrate для миграций
# ============================================================
migrate = Migrate(app, db)

# Подключение к Elasticsearch
es = Elasticsearch("http://localhost:9200")

# ============================================================
# ЗАДАЧА 3: Создание модели User
# ============================================================
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    posts = db.relationship('Post', backref='author', lazy=True)

# ============================================================
# ЗАДАЧА 13: Вторая модель Post (One-to-Many)
# ============================================================
class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

# ============================================================
# Модель Transaction — сумма введённая пользователем
# ============================================================
class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# ============================================================
# ЗАДАЧА 4: Создание таблиц в БД
# ============================================================
with app.app_context():
    db.create_all()

# ============================================================
# ЗАДАЧА 1 (проверка соединения): маршрут /
# ============================================================
@app.route('/')
def index():
    try:
        db.session.execute(db.text('SELECT 1'))
        msg = "Connexiunea la baza de date a reusit!"
    except Exception as e:
        msg = f"Eroare: {e}"
    return render_template('index.html', message=msg)

# ============================================================
# ЗАДАЧА 5: Сохранение пользователя в БД (регистрация)
# ============================================================
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']

        existing = User.query.filter_by(email=email).first()
        if existing:
            flash('Email-ul este deja inregistrat!', 'danger')
            return redirect(url_for('register'))

        new_user = User(name=name, email=email, password=password)
        db.session.add(new_user)
        db.session.commit()

        es.index(index="users", document={
            "id": new_user.id,
            "name": new_user.name,
            "email": new_user.email,
            "created_at": datetime.utcnow().isoformat()
        })

        flash('Cont creat cu succes! Te poti autentifica.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')

# ============================================================
# ЗАДАЧА 6: Функция проверки пользователя
# ============================================================
def check_user(email, password):
    user = User.query.filter_by(email=email, password=password).first()
    return user

# ============================================================
# ЗАДАЧА 8: Маршрут для логина
# ============================================================
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = check_user(email, password)
        if user:
            session['user_id'] = user.id
            session['user_name'] = user.name
            flash(f'Bun venit, {user.name}!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Email sau parola incorecta!', 'danger')
    return render_template('login.html')

# ============================================================
# ЗАДАЧА 7: Dashboard — только для авторизованных
# ============================================================
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        flash('Trebuie sa te autentifici mai intai!', 'warning')
        return redirect(url_for('login'))
    return render_template('dashboard.html', name=session['user_name'])

# ============================================================
# ЗАДАЧА 9: Логаут
# ============================================================
@app.route('/logout')
def logout():
    session.clear()
    flash('Ai fost deconectat.', 'info')
    return redirect(url_for('login'))

# ============================================================
# ЗАДАЧА 10: Показать всех пользователей
# ============================================================
@app.route('/users')
def users():
    all_users = User.query.all()
    return render_template('users.html', users=all_users)

# ============================================================
# ЗАДАЧА 11: Обновление пользователя
# ============================================================
@app.route('/edit/<int:user_id>', methods=['GET', 'POST'])
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    if request.method == 'POST':
        user.name = request.form['name']
        user.email = request.form['email']
        db.session.commit()
        flash('Datele au fost actualizate!', 'success')
        return redirect(url_for('users'))
    return render_template('edit_user.html', user=user)

# ============================================================
# ЗАДАЧА 12: Удаление пользователя
# ============================================================
@app.route('/delete/<int:user_id>')
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    flash('Utilizatorul a fost sters.', 'info')
    return redirect(url_for('users'))

# ============================================================
# ЗАДАЧА 13: Добавление поста (One-to-Many)
# ============================================================
@app.route('/add_post', methods=['GET', 'POST'])
def add_post():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        new_post = Post(title=title, content=content, user_id=session['user_id'])
        db.session.add(new_post)
        db.session.commit()
        flash('Postarea a fost adaugata!', 'success')
        return redirect(url_for('dashboard'))
    return render_template('add_post.html')

# ============================================================
# ЗАДАЧА 14: Поиск пользователей
# ============================================================
@app.route('/search', methods=['GET', 'POST'])
def search():
    results = []
    query = ''
    if request.method == 'POST':
        query = request.form['query']
        results = User.query.filter(
            (User.name.ilike(f'%{query}%')) | (User.email.ilike(f'%{query}%'))
        ).all()
    return render_template('search.html', results=results, query=query)

# ============================================================
# Ввод суммы пользователем -> БД + Elasticsearch
# ============================================================
@app.route('/add_amount', methods=['GET', 'POST'])
def add_amount():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        amount = float(request.form['amount'])

        transaction = Transaction(amount=amount, user_id=session['user_id'])
        db.session.add(transaction)
        db.session.commit()

        es.index(index="transactions", document={
            "user_id": session['user_id'],
            "user_name": session['user_name'],
            "amount": amount,
            "created_at": datetime.utcnow().isoformat()
        })

        flash(f'Suma ${amount} a fost salvata!', 'success')
        return redirect(url_for('add_amount'))

    return render_template('add_amount.html')

@app.route('/leaderboard')
def leaderboard():
    results = db.session.query(
        User.name.label('user_name'),
        func.sum(Transaction.amount).label('total')
    ).join(Transaction, Transaction.user_id == User.id)\
     .group_by(User.id)\
     .order_by(func.sum(Transaction.amount).desc())\
     .all()

    return render_template('leaderboard.html', leaderboard=results)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))