from flask import Flask, render_template, request, redirect, session, url_for
import pymysql
import os

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY')

# Database connectio
def get_db_connection():
    return pymysql.connect(
        host=os.environ.get('MYSQL_HOST'),
        port=int(os.environ.get('MYSQL_PORT', 3306)),
        user=os.environ.get('MYSQL_USER'),
        password=os.environ.get('MYSQL_PASSWORD'),
        db=os.environ.get('MYSQL_DB'),
        cursorclass=pymysql.cursors.DictCursor
    )

@app.route('/')
def index():
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute('SELECT * FROM interns')
        interns = cursor.fetchall()

        # ✅ Order tasks by insertion (task ID)
        cursor.execute('''
            SELECT t.id, i.name, t.task, t.status, t.points, t.intern_id
            FROM tasks t
            JOIN interns i ON t.intern_id = i.id
            ORDER BY t.id ASC
        ''')
        tasks = cursor.fetchall()

        # Top 3 interns by points
        cursor.execute('''
            SELECT i.id, i.name, SUM(t.points) AS total_points
            FROM interns i
            JOIN tasks t ON i.id = t.intern_id
            GROUP BY i.id, i.name
            ORDER BY total_points DESC
            LIMIT 3
        ''')
        top_interns = cursor.fetchall()
    conn.close()
    return render_template('index.html', interns=interns, tasks=tasks, top_interns=top_interns)


@app.route('/public_intern/<int:intern_id>')
def public_intern_detail(intern_id):
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute('SELECT * FROM interns')
        interns = cursor.fetchall()
        cursor.execute('SELECT * FROM interns WHERE id = %s', (intern_id,))
        intern = cursor.fetchone()
        cursor.execute('SELECT * FROM tasks WHERE intern_id = %s', (intern_id,))
        tasks = cursor.fetchall()
        cursor.execute('SELECT SUM(points) as total_points FROM tasks WHERE intern_id = %s', (intern_id,))
        total_points = cursor.fetchone()['total_points'] or 0
    conn.close()
    return render_template('public_intern_detail.html', intern=intern, tasks=tasks, total_points=total_points, interns=interns)

@app.route('/login', methods=['GET', 'POST'])
def login():
    msg = ''
    next_page = request.args.get('next')
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute('SELECT * FROM admins WHERE username = %s AND password = %s', (username, password))
            account = cursor.fetchone()
        conn.close()
        if account:
            session['loggedin'] = True
            session['username'] = username
            return redirect(next_page or url_for('admin_dashboard'))
        else:
            msg = 'Invalid username or password!'
    return render_template('login.html', msg=msg)

@app.route('/admin', methods=['GET', 'POST'])
def admin_dashboard():
    if 'loggedin' not in session:
        return redirect(url_for('login'))
    conn = get_db_connection()
    with conn.cursor() as cursor:
        if request.method == 'POST':
            name = request.form['name']
            department = request.form['department']
            cursor.execute('INSERT INTO interns (name, department) VALUES (%s, %s)', (name, department))
            conn.commit()
        cursor.execute('SELECT * FROM interns')
        interns = cursor.fetchall()
    conn.close()
    return render_template('admin_dashboard.html', interns=interns)

@app.route('/intern/<int:intern_id>', methods=['GET', 'POST'])
def view_intern_tasks(intern_id):
    if 'loggedin' not in session:
        return redirect(url_for('login'))
    conn = get_db_connection()
    with conn.cursor() as cursor:
        if request.method == 'POST':
            task = request.form['task']
            status = request.form['status']
            points = int(request.form['points']) if request.form['points'].strip() else 0
            cursor.execute('INSERT INTO tasks (intern_id, task, status, points) VALUES (%s, %s, %s, %s)', (intern_id, task, status, points))
            conn.commit()
        cursor.execute('SELECT * FROM interns WHERE id = %s', (intern_id,))
        intern = cursor.fetchone()
        cursor.execute('SELECT * FROM tasks WHERE intern_id = %s', (intern_id,))
        tasks = cursor.fetchall()
        cursor.execute('SELECT SUM(points) as total_points FROM tasks WHERE intern_id = %s', (intern_id,))
        total_points = cursor.fetchone()['total_points'] or 0
    conn.close()
    return render_template('intern_detail.html', intern=intern, tasks=tasks, total_points=total_points)

@app.route('/update_task_page/<int:task_id>', methods=['GET', 'POST'])
def update_task_page(task_id):
    if 'loggedin' not in session:
        return redirect(url_for('login', next=url_for('update_task_page', task_id=task_id)))
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute('SELECT * FROM tasks WHERE id = %s', (task_id,))
        task = cursor.fetchone()
    if not task:
        conn.close()
        return "Task not found", 404
    if request.method == 'POST':
        status = request.form['status']
        points = int(request.form['points']) if request.form['points'].strip() else 0
        with conn.cursor() as cursor:
            cursor.execute('UPDATE tasks SET status = %s, points = %s WHERE id = %s', (status, points, task_id))
            conn.commit()
        conn.close()
        return redirect(url_for('index'))
    conn.close()
    return render_template('update_task_page.html', task=task)

@app.route('/update_task/<int:task_id>', methods=['POST'])
def update_task(task_id):
    if 'loggedin' not in session:
        return redirect(url_for('login'))
    status = request.form['status']
    points = int(request.form['points']) if request.form['points'].strip() else 0
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute('UPDATE tasks SET status = %s, points = %s WHERE id = %s', (status, points, task_id))
        conn.commit()
        cursor.execute('SELECT intern_id FROM tasks WHERE id = %s', (task_id,))
        intern_id = cursor.fetchone()['intern_id']
    conn.close()
    return redirect(url_for('view_intern_tasks', intern_id=intern_id))

@app.route('/logout')
def logout():
    session.pop('loggedin', None)
    session.pop('username', None)
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
