from flask import Flask, render_template, redirect, url_for, request, session, flash
import os
from models import *
from datetime import timedelta

app = Flask(__name__, static_folder='static')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'sua_chave_secreta_aqui'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=1)
app.config['UPLOAD_FOLDER'] = 'static/uploads'  # Pasta para armazenar imagens
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # Limite de 16 MB por imagem

db.init_app(app)

@app.route('/')
def index():
    produtos = Produto.query.all()
    return render_template('index.html', produtos=produtos, username=session.get('username'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('login-form-username')
        password = request.form.get('login-form-password')
        user = User.query.filter_by(username=username, password=password).first()

        if user:
            session['username'] = user.username
            session['user_id'] = user.id  # Armazena o ID do usuário na sessão
            session.permanent = True
            return redirect(url_for('index'))
        else:
            return render_template('login.html', error='Usuário ou senha incorretos.')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('register-form-username')
        email = request.form.get('register-form-email')
        password = request.form.get('register-form-password')

        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            return redirect(url_for('register', error='Email já registrado'))

        user = User(username=username, email=email, password=password)
        db.session.add(user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/profile')
def profile():
    if 'username' not in session or 'user_id' not in session:
        return redirect(url_for('login'))  # Redireciona para o login se não tiver usuário na sessão
    
    user_id = session.get('user_id')  # ID do usuário armazenado na sessão
    user = User.query.get(user_id)  # Recuperando o usuário pelo ID, usando SQLAlchemy
    
    if user is None:
        # Caso não encontre o usuário no banco de dados (talvez por um erro)
        return redirect(url_for('login'))  # Redireciona novamente para o login
    
    return render_template('profile.html', username=session['username'], user=user)

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('index'))

@app.route('/criar_produto', methods=['GET', 'POST'])
def criar_produto():
    if request.method == 'POST':
        nome = request.form.get('nome')
        descricao = request.form.get('descricao')
        preco = request.form.get('preco')
        categoria_nome = request.form.get('categoria')
        imagem = request.files['imagem']

        # Verificar categoria
        categoria = Categoria.query.filter_by(nome=categoria_nome).first()
        if not categoria:
            categoria = Categoria(nome=categoria_nome)
            db.session.add(categoria)
            db.session.commit()

        # Criar o produto
        novo_produto = Produto(nome=nome, descricao=descricao, preco=preco, categoria=categoria)

        # Salvar imagem
        if imagem:
            imagem_filename = os.path.join(app.config['UPLOAD_FOLDER'], imagem.filename)
            imagem.save(imagem_filename)

            # Adicionar imagem ao produto
            nova_imagem = Imagem(name=imagem.filename, produto=novo_produto)
            db.session.add(nova_imagem)

        db.session.add(novo_produto)
        db.session.commit()
        flash('Produto criado com sucesso!', 'success')
        return redirect(url_for('index'))

    return render_template('criar_produto.html')


@app.errorhandler(404)
def page_not_found(error):
    return render_template('404.html')


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
