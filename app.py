from flask import Flask, render_template, request
import mysql.connector
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__)

IST = timezone(timedelta(hours=5, minutes=30))

def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv('DB_HOST'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        database=os.getenv('DB_NAME')
    )
@app.route('/')
def home():
    return render_template('index.html', message="")

@app.route('/check_login', methods=['POST'])
def check_login():
    username = request.form.get('username')
    email = request.form.get('email')
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    query = "SELECT * FROM responses WHERE email=%s"
    cursor.execute(query, (email,))
    existing_user = cursor.fetchone()
    conn.close()
    if existing_user:
        return render_template('index.html', message="Already submitted using this email.")
    return render_template('survey.html', name=username, email=email)

@app.route('/submit', methods=['POST'])
def submit():
    username = request.form.get('username')
    email = request.form.get('email')
    q1 = int(request.form.get('q1'))
    q2 = int(request.form.get('q2'))
    q3 = int(request.form.get('q3'))
    q4 = int(request.form.get('q4'))
    q5 = int(request.form.get('q5'))
    total_score = q1 + q2 + q3 + q4 + q5
    submission_time = datetime.now(IST).strftime('%d-%m-%Y %H:%M')

    conn = get_db_connection()
    cursor = conn.cursor()
    query = """
    INSERT INTO responses (username, email, q1, q2, q3, q4, q5, score, submission_time)
    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """
    values = (username, email, q1, q2, q3, q4, q5, total_score, submission_time)
    cursor.execute(query, values)
    conn.commit()
    conn.close()
    return render_template('success.html', username=username)

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if request.method == 'GET':
        return render_template('admin_login.html', error="")
    username = request.form.get('admin_name')
    password = request.form.get('admin_password')
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    query = "SELECT * FROM admins WHERE username=%s AND password=%s"
    cursor.execute(query, (username, password))
    admin_user = cursor.fetchone()
    if not admin_user:
        conn.close()
        return render_template('admin_login.html', error="Invalid Username or Password")
    cursor.execute("SELECT * FROM responses")
    data = cursor.fetchall()
    conn.close()
    return render_template('admin_dashboard.html', data=data, start_date="", end_date="")

@app.route('/filter', methods=['POST'])
def filter_data():
    start_date = request.form.get('start_date')
    end_date = request.form.get('end_date')
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if start_date and end_date:
        # Convert YYYY-MM-DD to DD-MM-YYYY
        start_converted = start_date[8:10] + '-' + start_date[5:7] + '-' + start_date[0:4]
        end_converted = end_date[8:10] + '-' + end_date[5:7] + '-' + end_date[0:4]
        cursor.execute("""
            SELECT * FROM responses 
            WHERE submission_time LIKE %s
            OR submission_time LIKE %s
        """, ('%' + start_converted + '%', '%' + end_converted + '%'))
    elif start_date:
        start_converted = start_date[8:10] + '-' + start_date[5:7] + '-' + start_date[0:4]
        cursor.execute("SELECT * FROM responses WHERE submission_time LIKE %s", ('%' + start_converted + '%',))
    elif end_date:
        end_converted = end_date[8:10] + '-' + end_date[5:7] + '-' + end_date[0:4]
        cursor.execute("SELECT * FROM responses WHERE submission_time LIKE %s", ('%' + end_converted + '%',))
    else:
        cursor.execute("SELECT * FROM responses")

    data = cursor.fetchall()
    conn.close()
    return render_template('admin_dashboard.html', data=data, start_date=start_date or "", end_date=end_date or "")
@app.route('/filter_clear')
def filter_clear():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM responses")
    data = cursor.fetchall()
    conn.close()
    return render_template('admin_dashboard.html', data=data, start_date="", end_date="")
@app.route('/dashboard')
def dashboard():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT username, score FROM responses")
    rows = cursor.fetchall()
    labels = []
    scores = []
    for row in rows:
        user = str(row['username']) if row['username'] else "Unknown"
        try:
            scr = float(row['score']) if row['score'] is not None else 0.0
        except (ValueError, TypeError):
            scr = 0.0
        labels.append(user)
        scores.append(scr)
    cursor.execute("SELECT q1, q2, q3, q4, q5 FROM responses")
    survey_data = cursor.fetchall()
    conn.close()
    question_keys = ['q1', 'q2', 'q3', 'q4', 'q5']
    breakdowns = {q: {1: 0, 2: 0, 3: 0, 4: 0, 5: 0} for q in question_keys}
    for record in survey_data:
        for q in question_keys:
            voted_value = record[q]
            if voted_value in breakdowns[q]:
                breakdowns[q][voted_value] += 1
    question_stats = {
        q: [breakdowns[q][1], breakdowns[q][2], breakdowns[q][3], breakdowns[q][4], breakdowns[q][5]]
        for q in question_keys
    }
    return render_template(
        'dashboard.html',
        labels=labels,
        scores=scores,
        q_stats=question_stats
    )

if __name__ == '__main__':
    app.run(debug=True)