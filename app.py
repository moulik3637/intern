from flask import Flask, render_template, request, redirect, session, url_for
from flask_mysqldb import MySQL
import MySQLdb.cursors
import os

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'supersecretkey')  # fallback if not set

# MySQL Configuration using environment variables
app.config['MYSQL_HOST'] = os.environ.get('MYSQL_HOST')
app.config['MYSQL_PORT'] = int(os.environ.get('MYSQL_PORT', 3306))  # fallback to 3306 if not set
app.config['MYSQL_USER'] = os.environ.get('MYSQL_USER')
app.config['MYSQL_PASSWORD'] = os.environ.get('MYSQL_PASSWORD')
app.config['MYSQL_DB'] = os.environ.get('MYSQL_DB')

mysql = MySQL(app)

# Home - Public Dashboard with Sidebar and Update Option
@app.route('/')
def index():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT * FROM interns')
    interns = cursor.fetchall()
    cursor.execute('SELECT t.id, i.name, t.task, t.status, t.points, t.intern_id FROM tasks t JOIN interns i ON t.intern_id = i.id')
    tasks = cursor.fetchall()
    cursor.close()
    return render_template('index.html', interns=interns, tasks=tasks)

# Public Intern Detail View (Sidebar needs all interns)
@app.route('/public_intern/<int:intern_id>')
def public_intern_detail(intern_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT * FROM interns')
    interns = cursor.fetchall()
    cursor.execute('SELECT * FROM interns WHERE id = %s', (intern_id,))
    intern = cursor.fetchone()
    cursor.execute('SELECT * FROM tasks WHERE intern_id = %s', (intern_id,))
    tasks = cursor.fetchall()
    cursor.execute('SELECT SUM(points) as total_points FROM tasks WHERE intern_id = %s', (intern_id,))
    total_points = cursor.fetchone()['total_points'] or 0
    cursor.close()
    return render_template('public_intern_detail.html', intern=intern, tasks=tasks, total_points=total_points, interns=interns)

# Admin Login (supports ?next= redirect)
@app.route('/login', methods=['GET', 'POST'])
def login():
    msg = ''
    next_page = request.args.get('next')
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM admins WHERE username = %s AND password = %s', (username, password))
        account = cursor.fetchone()
        cursor.close()
        if account:
            session['loggedin'] = True
            session['username'] = username
            return redirect(next_page or url_for('admin_dashboard'))
        else:
            msg = 'Invalid username or password!'
    return render_template('login.html', msg=msg)

# Admin Dashboard
@app.route('/admin', methods=['GET', 'POST'])
def admin_dashboard():
    if 'loggedin' not in session:
        return redirect(url_for('login'))
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    if request.method == 'POST':
        name = request.form['name']
        department = request.form['department']
        cursor.execute('INSERT INTO interns (name, department) VALUES (%s, %s)', (name, department))
        mysql.connection.commit()
    cursor.execute('SELECT * FROM interns')
    interns = cursor.fetchall()
    cursor.close()
    return render_template('admin_dashboard.html', interns=interns)

# View & Assign Task to Intern (Admin only)
@app.route('/intern/<int:intern_id>', methods=['GET', 'POST'])
def view_intern_tasks(intern_id):
    if 'loggedin' not in session:
        return redirect(url_for('login'))
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    if request.method == 'POST':
        task = request.form['task']
        status = request.form['status']
        points = int(request.form['points']) if request.form['points'].strip() else 0
        cursor.execute('INSERT INTO tasks (intern_id, task, status, points) VALUES (%s, %s, %s, %s)', (intern_id, task, status, points))
        mysql.connection.commit()
    cursor.execute('SELECT * FROM interns WHERE id = %s', (intern_id,))
    intern = cursor.fetchone()
    cursor.execute('SELECT * FROM tasks WHERE intern_id = %s', (intern_id,))
    tasks = cursor.fetchall()
    cursor.execute('SELECT SUM(points) as total_points FROM tasks WHERE intern_id = %s', (intern_id,))
    total_points = cursor.fetchone()['total_points'] or 0
    cursor.close()
    return render_template('intern_detail.html', intern=intern, tasks=tasks, total_points=total_points)

# Update Task Page (shows update form, requires login)
@app.route('/update_task_page/<int:task_id>', methods=['GET', 'POST'])
def update_task_page(task_id):
    if 'loggedin' not in session:
        return redirect(url_for('login', next=url_for('update_task_page', task_id=task_id)))
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT * FROM tasks WHERE id = %s', (task_id,))
    task = cursor.fetchone()
    cursor.close()
    if not task:
        return "Task not found", 404
    if request.method == 'POST':
        status = request.form['status']
        points = int(request.form['points']) if request.form['points'].strip() else 0
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('UPDATE tasks SET status = %s, points = %s WHERE id = %s', (status, points, task_id))
        mysql.connection.commit()
        cursor.close()
        return redirect(url_for('index'))
    return render_template('update_task_page.html', task=task)

# Update Task (used by admin/intern detail)
@app.route('/update_task/<int:task_id>', methods=['POST'])
def update_task(task_id):
    if 'loggedin' not in session:
        return redirect(url_for('login'))
    status = request.form['status']
    points = int(request.form['points']) if request.form['points'].strip() else 0
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('UPDATE tasks SET status = %s, points = %s WHERE id = %s', (status, points, task_id))
    mysql.connection.commit()
    cursor.execute('SELECT intern_id FROM tasks WHERE id = %s', (task_id,))
    intern_id = cursor.fetchone()['intern_id']
    cursor.close()
    return redirect(url_for('view_intern_tasks', intern_id=intern_id))

# Logout
@app.route('/logout')
def logout():
    session.pop('loggedin', None)
    session.pop('username', None)
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
