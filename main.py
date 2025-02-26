from flask import Flask, render_template, redirect, url_for, request
from models import User, db

app = Flask(__name__, static_folder='static')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/login')
def login():
    return render_template('login.html')


@app.route('/login_handler', methods=['POST'])
def login_handler():
    username = request.form.get('login-form-username')
    password = request.form.get('login-form-password')
    if username == 'admin' and password == 'admin':
        return redirect(url_for('index'))
    return redirect(url_for('login'))

@app.route('/register')
def register():
    return render_template('register.html')

@app.route('/register_handler', methods=['POST'])
def register_handler():
    name = request.form.get('register-form-name')
    username = request.form.get('register-form-username')
    email = request.form.get('register-form-email')
    password = request.form.get('register-form-password')
    
    # Verifique se o usuário já existe
    existing_user = User.query.filter_by(username=username).first()
    if existing_user:
        return redirect(url_for('register'))  # Redireciona se o usuário já existir

    # Crie um novo usuário
    new_user = User(name=name, username=username, email=email, password=password)
    db.session.add(new_user)
    db.session.commit()
    
    return redirect(url_for('login'))  # Redireciona para a página de login após o registro

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'),404

if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Isso cria as tabelas se não existirem
    app.run(debug=True)
