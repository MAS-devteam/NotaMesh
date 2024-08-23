from flask import Flask, render_template, request, redirect, url_for, send_from_directory, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os

app = Flask(__name__)
app.secret_key = 'supersecretkey'

# Configurazione del database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///students.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Configurazione della directory per i file caricati
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Configurazione di Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Modello per l'utente
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)

# Modello per i file caricati (appunti)
class Note(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(150), nullable=False)
    category = db.Column(db.String(50), nullable=True)
    tags = db.Column(db.String(250), nullable=True)  # Memorizza i tag come stringa separata da virgola
    shared_with = db.Column(db.String(250), nullable=True)  # Memorizza ID utenti separati da virgola

# Modello per i commenti
class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    note_id = db.Column(db.Integer, db.ForeignKey('note.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    comment_text = db.Column(db.Text, nullable=False)
    rating = db.Column(db.Integer, nullable=True)
    user = db.relationship('User', backref=db.backref('comments', lazy=True))
    note = db.relationship('Note', backref=db.backref('comments', lazy=True))

@login_manager.user_loader
def load_user(user_id):
    try:
        return User.query.get(int(user_id))
    except ValueError:
        return None

# Creare il database e le tabelle
with app.app_context():
    db.create_all()

# Route per la registrazione
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        new_user = User(username=username, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        flash('Registrazione effettuata con successo! Puoi ora effettuare il login.')
        return redirect(url_for('login'))
    return render_template('register.html')

# Route per il login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            flash('Login effettuato con successo!')
            return redirect(url_for('index'))
        else:
            flash('Credenziali non valide. Riprova.')
    return render_template('login.html')

# Route per il logout
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logout effettuato con successo!')
    return redirect(url_for('login'))

# Route per la pagina principale (protetta)
@app.route('/')
@login_required
def index():
    search_query = request.args.get('search', '')
    user_id_str = str(current_user.id)
    
    if search_query:
        notes = Note.query.filter(
            (Note.filename.contains(search_query)) |
            (Note.category.contains(search_query)) |
            (Note.tags.contains(search_query))
        ).all()
    else:
        notes = Note.query.filter(
            (Note.shared_with.contains(user_id_str)) |
            (Note.shared_with.is_(None))  # Opzionale, mostra i file non condivisi
        ).all()
    return render_template('index.html', notes=notes, search_query=search_query)

# Route per il caricamento dei file (protetta)
@app.route('/upload', methods=['POST'])
@login_required
def upload_file():
    file = request.files['file']
    category = request.form['category']
    tags = request.form['tags']
    shared_with = request.form['shared_with']  # Usernames separati da virgola

    if file and category:
        filename = file.filename
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        new_note = Note(filename=filename, category=category, tags=tags, shared_with=shared_with)
        db.session.add(new_note)
        db.session.commit()
        flash('File caricato con successo!')
        return redirect(url_for('index'))
    else:
        flash('Tutti i campi sono obbligatori.')
        return redirect(url_for('index'))

# Route per aggiungere commenti
@app.route('/add_comment/<int:note_id>', methods=['POST'])
@login_required
def add_comment(note_id):
    comment_text = request.form['comment_text']
    rating = request.form.get('rating')

    new_comment = Comment(note_id=note_id, user_id=current_user.id, comment_text=comment_text, rating=rating)
    db.session.add(new_comment)
    db.session.commit()
    flash('Commento aggiunto con successo!')
    return redirect(url_for('index'))

# Route per scaricare i file (protetta)
@app.route('/uploads/<filename>')
@login_required
def download_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# Route per gestire l'account utente
@app.route('/account', methods=['GET', 'POST'])
@login_required
def account():
    if request.method == 'POST':
        new_username = request.form['username']
        new_password = request.form['password']
        if new_password:
            hashed_password = generate_password_hash(new_password, method='pbkdf2:sha256')
            current_user.password = hashed_password
        if new_username:
            current_user.username = new_username
        db.session.commit()
        flash('Informazioni aggiornate con successo!')
        return redirect(url_for('account'))
    
    return render_template('account.html', user=current_user)

if __name__ == '__main__':
    app.run(debug=True)



#Fine del codice
# ---------------------------------------------
# Copyright (c) 2024 Mario Pisano
#
# Questo programma è distribuito sotto la licenza EUPL, Versione 1.2 o – non appena 
# saranno approvate dalla Commissione Europea – versioni successive della EUPL 
# (la "Licenza");
# Puoi usare, modificare e/o ridistribuire il programma sotto i termini della 
# Licenza. 
# 
# Puoi trovare una copia della Licenza all'indirizzo:
# https://joinup.ec.europa.eu/collection/eupl/eupl-text-eupl-12
