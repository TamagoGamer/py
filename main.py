from flask import Flask, render_template, redirect, url_for, request, session, flash
import os
from models import *
from datetime import timedelta
from werkzeug.utils import secure_filename

app = Flask(__name__, static_folder='static')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'sua_chave_secreta_aqui'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=1)
app.config['UPLOAD_FOLDER'] = 'static/uploads'  # Pasta para armazenar imagens
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # Limite de 16 MB por imagem
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}

db.init_app(app)

@app.context_processor
def cart_count_processor():
    user_id = session.get('user_id')
    if user_id:
        cart_count = CartItem.query.filter_by(user_id=user_id).count()
    else:
        cart_count = 0
    return {'cart_count': cart_count}

@app.route('/')
def index():
    produtos = Produto.query.all()
    logged_in = 'user_id' in session  # Verifica se há um usuário logado
    return render_template('index.html', produtos=produtos, username=session.get('username'), logged_in=logged_in)

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

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'username' not in session or 'user_id' not in session:
        return redirect(url_for('login'))  # Redireciona para o login se não estiver logado
    
    user_id = session.get('user_id')  
    user = User.query.get(user_id)  # Busca o usuário pelo ID
    logged_in = 'user_id' in session
    produtos = Produto.query.all()

    if user is None:
        return redirect(url_for('login'))  # Redireciona se o usuário não for encontrado

    # Se for um POST (upload de avatar)
    if request.method == 'POST':
        if 'avatar' not in request.files:
            flash('Nenhum arquivo selecionado.', 'danger')
            return redirect(request.url)
        
        file = request.files['avatar']
        if file.filename == '':
            flash('Nenhum arquivo selecionado.', 'danger')
            return redirect(request.url)
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            # Salva o caminho do avatar no banco de dados
            user.avatar = f"uploads/{filename}"
            db.session.commit()
            flash('Avatar atualizado com sucesso!', 'success')
            return redirect(url_for('profile'))

    # Verifica se o usuário já tem um avatar, caso contrário usa um padrão
    avatar = user.avatar if user.avatar else "default-avatar.jpg"
    
    return render_template('profile.html', username=session['username'], user=user, avatar=avatar, logged_in=logged_in, produtos=produtos)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

@app.route('/upload_avatar', methods=['POST'])
def upload_avatar():
    if 'avatar' not in request.files:
        return redirect(url_for('profile'))
    
    file = request.files['avatar']
    if file.filename == '':
        return redirect(url_for('profile'))
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        return redirect(url_for('profile', avatar=filename))
    
    return redirect(url_for('profile'))

@app.route('/logout')
def logout():
    session.pop('username', None)
    session.pop('user_id', None)  # Remove o ID do usuário também
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

@app.route('/produto/<int:produto_id>/deletar', methods=['POST'])
def delete_product(produto_id):
    produto = Produto.query.get_or_404(produto_id)
    try:
        # Deletar as imagens associadas ao produto
        for imagem in produto.imagens:
            db.session.delete(imagem)
        db.session.commit()

        # Deletar itens do carrinho associados ao produto
        CartItem.query.filter_by(produto_id=produto.id).delete()
        db.session.commit()

        # Deletar o produto
        db.session.delete(produto)
        db.session.commit()
        flash('Produto deletado com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Erro ao deletar o produto.', 'danger')
        print(f"Erro ao deletar o produto: {e}")
    
    return redirect(url_for('index'))


@app.route('/produto/<int:produto_id>')
def produto_single(produto_id):
    produto = Produto.query.get_or_404(produto_id)  # Busca o produto
    return render_template('product_single.html', produto=produto)

@app.route('/add_to_cart/<int:produto_id>', methods=['POST'])
def add_to_cart(produto_id):
    quantity = request.form.get('quantity', type=int, default=1)
    produto = Produto.query.get_or_404(produto_id)

    if 'user_id' not in session:
        return redirect(url_for('login'))  # Redireciona para o login caso o usuário não esteja logado
    
    user_id = session.get('user_id')

    # Verifica se o item já está no carrinho
    cart_item = CartItem.query.filter_by(produto_id=produto.id, user_id=user_id).first()
    
    if cart_item:
        cart_item.quantity += quantity  # Atualiza a quantidade se já existir no carrinho
    else:
        cart_item = CartItem(produto_id=produto.id, quantity=quantity, user_id=user_id)
        db.session.add(cart_item)

    db.session.commit()
    return redirect(url_for('cart'))

@app.route('/update_quantity/<int:item_id>', methods=['POST'])
def update_quantity(item_id):
    cart_item = CartItem.query.get_or_404(item_id)
    quantity = request.form.get('quantity', type=int)

    # Atualiza a quantidade do item no carrinho
    if quantity > 0:
        cart_item.quantity = quantity
        db.session.commit()

    return redirect(url_for('cart'))

@app.route('/remove_from_cart/<int:cart_item_id>', methods=['POST'])
def remove_from_cart(cart_item_id):
    cart_item = CartItem.query.get_or_404(cart_item_id)

    if 'user_id' not in session:
        return redirect(url_for('login'))  # Redireciona para o login caso o usuário não esteja logado
    
    user_id = session.get('user_id')

    # Verifica se o item pertence ao usuário logado
    if cart_item.user_id == user_id:
        db.session.delete(cart_item)
        db.session.commit()
        flash('Item removido do carrinho com sucesso!', 'success')
    else:
        flash('Este item não pertence a você!', 'danger')

    return redirect(url_for('cart'))

@app.route('/cart')
def cart():
    if 'user_id' not in session:
        return redirect(url_for('login'))  # Redireciona para o login caso o usuário não esteja logado
    
    user_id = session.get('user_id')
    cart_items = CartItem.query.filter_by(user_id=user_id).all()  # Filtra os itens do carrinho pelo usuário
    total = sum(item.produto.preco * item.quantity for item in cart_items)
    logged_in = 'user_id' in session  # Verifica se há um usuário logado
    
    return render_template('cart.html', cart_items=cart_items, total=total, logged_in=logged_in)

def get_cart_items():
    # Verifica se o carrinho existe na sessão, caso contrário, retorna uma lista vazia
    return session.get('cart', [])

@app.route('/checkout')
def checkout():
    if 'user_id' not in session:
        return redirect(url_for('login'))  # Redireciona para o login caso o usuário não esteja logado
    
    user_id = session.get('user_id')
    
    # Recupera os itens do carrinho do banco de dados
    cart_items = CartItem.query.filter_by(user_id=user_id).all()  # Filtra os itens do carrinho pelo ID do usuário
    
    # Calcula o subtotal do carrinho
    cart_subtotal = sum(item.produto.preco * item.quantity for item in cart_items)
    cart_total = cart_subtotal  # Se necessário, adicione outros custos (ex: envio)
    logged_in = 'user_id' in session  # Verifica se há um usuário logado
    
    return render_template('checkout.html', cart_items=cart_items, cart_subtotal=cart_subtotal, cart_total=cart_total, logged_in=logged_in)

@app.errorhandler(404)
def page_not_found(error):
    return render_template('404.html')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
