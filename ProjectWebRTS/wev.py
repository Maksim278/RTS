from flask import Flask, render_template, request, redirect, url_for
from flask_login import LoginManager,UserMixin,login_user,logout_user,login_required,current_user
import sqlite3

from pyexpat.errors import messages
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

connection = sqlite3.connect('sqlite.db',check_same_thread=False)
cursor = connection.cursor()

app.config['SECRET_KEY'] = ''
login_manager = LoginManager(app)
login_manager.login_view = 'login'

class User(UserMixin):
    def __init__(self, id, username, password_hash):
        self.id = id
        self.username = username
        self.password_hash = password_hash

    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

@login_manager.user_loader
def load_user(user_id):
    user = cursor.execute(''
                   'SELECT * FROM user WHERE id = ?', (user_id,)).fetchone()
    if user is not None:
        return User(user[0], user[1], user[2])
    return None

def close_db(connection=None):
    if connection is not None:
        connection.close()

@app.teardown_appcontext
def close_connection(exception):
    close_db()

@app.route('/')
def index():
    cursor.execute('''SELECT post.id, post.title,post.content,post.author_id,user.username,
                   COUNT(DISTINCT like.id) AS likes,COUNT(DISTINCT dislike.id) AS dislikes FROM post
                   JOIN user ON post.author_id = user.id
                   LEFT JOIN like ON post.id = like.post_id
                   LEFT JOIN dislike ON post.id = dislike.post_id 
                   GROUP BY post.id,post.title,post.content,post.author_id,user.username''')
    result = cursor.fetchall()
    print(result)
    posts = []
    for post in reversed(result):
        posts.append(
            {'id': post[0],'title': post[1], 'content': post[2],'author_id': post[3],'username': post[4],
             'likes': post[5],'dislikes': post[6]})
        if current_user.is_authenticated:
            cursor.execute('SELECT post_id FROM like WHERE user_id = ?', (current_user.id,))
            cursor.execute('SELECT post_id FROM dislike WHERE user_id = ?', (current_user.id,))

            likes_result = cursor.fetchall()
            liked_post = []

            dislikes_result = cursor.fetchall()
            disliked_post = []

            for like in likes_result:
                liked_post.append(like[0])
            posts[-1]['liked_post'] = liked_post

            for dislike in dislikes_result:
                disliked_post.append(dislike[0])
            posts[-1]['disliked_post'] = disliked_post

    context = {'posts': posts}
    print(context)
    return render_template('blog.html', **context)


@app.route('/add/', methods=['GET', 'POST'])
@login_required
def add():
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        cursor.execute(
        'INSERT INTO post (title,content,author_id) VALUES (?, ?, ?)',
            (title, content, current_user.id))
        connection.commit()
        return redirect(url_for('index'))
    return render_template('add_post.html')

@app.route('/post/<post_id>')
def post(post_id):
    result = cursor.execute(
        'SELECT * FROM post WHERE id = ?', (post_id,)
    ).fetchone()
    post_dict = {'id': result[0],'title': result[1],'content': result[2]}
    return render_template('post.html', post=post_dict)

@app.route('/register/', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        try:
            cursor.execute('INSERT INTO user (username'
                           ',password_hash) VALUES(?,?)',
                           (username,generate_password_hash(password))
            )
            connection.commit()
            print('Регистрация прошла успешно')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            print('Username alredy exists!')
            return render_template('registrate.html',
                                        message='Username alredy exists!!')
    return render_template('registrate.html')


@app.route('/login/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = cursor.execute(''
                'SELECT * FROM user WHERE username = ?', (username,)).fetchone()
        if user and User(user[0],user[1],user[2]).check_password(password):
            login_user(User(user[0],user[1],user[2]))
            return redirect(url_for('index'))
        else:
            return render_template('login.html',
                                   messages= 'Invalid username or password')
    return render_template('login.html')

@app.route('/logout/')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/delete/<int:post_id>', methods=['POST'])
@login_required
def delete_post(post_id):
    post = cursor.execute('SELECT * FROM post WHERE id = ?',
                           (post_id,)).fetchone()

    if post and post[3] == current_user.id:
        cursor.execute('DELETE FROM post WHERE id = ?', (post_id,))
        return redirect(url_for('index'))
    else:
        return redirect(url_for('index'))

def user_liking(user_id,post_id):
    like = cursor.execute('SELECT * FROM like WHERE user_id = ? AND post_id = ?',
                          (user_id,post_id)).fetchone()
    return bool(like)


@app.route('/like/<int:post_id>')
@login_required
def like_post(post_id):
    post = cursor.execute('SELECT * FROM post WHERE id = ?', (post_id,)).fetchone()
    if post:
        if user_liking(current_user.id, post_id):
            cursor.execute('DELETE FROM like WHERE user_id = ? AND post_id = ?',
                           (current_user.id, post_id))
            connection.commit()
            print('You unliked post')
        else:
            cursor.execute('INSERT INTO like (user_id, post_id) VALUES (?, ?)',
                           (current_user.id, post_id))
            connection.commit()
            print('You like post')
        return redirect(url_for('index'))
    return 'Post not found', 404

def user_disliking(user_id,post_id):
    dislike = cursor.execute('SELECT * FROM dislike WHERE user_id = ? AND post_id = ?',
                          (user_id,post_id)).fetchone()
    return bool(dislike)

@app.route('/dislike/<int:post_id>')
@login_required
def dislike_post(post_id):
    post = cursor.execute('SELECT * FROM post WHERE id = ?', (post_id,)).fetchone()
    if post:
        if user_disliking(current_user.id, post_id):
            cursor.execute('DELETE FROM dislike WHERE user_id = ? AND post_id = ?',
                           (current_user.id, post_id))
            connection.commit()
            print('You undisliked post')
        else:
            cursor.execute('INSERT INTO dislike (user_id, post_id) VALUES (?, ?)',
                           (current_user.id, post_id))
            connection.commit()
            print('You dislike post')
        return redirect(url_for('index'))
    return 'Post not found', 404


if __name__ == '__main__':
    app.run()



