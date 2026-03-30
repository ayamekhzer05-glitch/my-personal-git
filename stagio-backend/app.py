from flask import Flask, render_template, redirect, url_for, request, session, flash, jsonify
from markupsafe import Markup
import os
import json
import requests as http_requests
from flask_mysqldb import MySQL
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from functools import wraps
import MySQLdb.cursors

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
template_dir = os.path.join(base_dir, 'templates')
UPLOAD_FOLDER = os.path.join(base_dir, 'uploads')
ALLOWED_CV = {'pdf', 'doc', 'docx'}

# ✅ مفتاح Gemini API
GEMINI_API_KEY = "AIzaSyAdCHe5rnn1hCPbazZdRxCTtvrF_5Oirks"

app = Flask(__name__, template_folder=template_dir)
app.secret_key = "stagio_2026_super_secret"
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'internship_platform'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'
mysql = MySQL(app)

def login_required_web(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            flash('Please login first', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def login_required_api(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return jsonify({'error': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    return decorated_function

# ==================== API AUTH ====================

@app.route("/api/test")
def api_test():
    return jsonify({"message": "API is working!"})

@app.route("/api/auth/register", methods=["POST"])
def api_register():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        email    = data['email']
        password = data['password']
        role     = data['role']
        phone    = data.get('phoneNumber')
        if role not in ['student', 'company', 'admin']:
            return jsonify({'error': 'Invalid role'}), 400
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT id FROM users WHERE email=%s", (email,))
        if cursor.fetchone():
            cursor.close()
            return jsonify({'error': 'Email already registered'}), 409
        cursor.execute("INSERT INTO users (email,password,role,phoneNumber,created_at) VALUES (%s,%s,%s,%s,NOW())",
                       (email, generate_password_hash(password), role, phone))
        mysql.connection.commit()
        user_id = cursor.lastrowid
        if role == 'student':
            first = data.get('student_data', {}).get('first_name', '')
            last  = data.get('student_data', {}).get('last_name', '')
            cursor.execute("INSERT INTO students (user_id,first_name,last_name,placement_status,created_at) VALUES (%s,%s,%s,'unplaced',NOW())",
                           (user_id, first, last))
            mysql.connection.commit()
        cursor.close()
        session.update({'user_id': user_id, 'user_email': email, 'user_type': role, 'logged_in': True})
        return jsonify({'success': True, 'user': {'id': user_id, 'email': email, 'role': role}}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route("/api/auth/login", methods=["POST"])
def api_login():
    try:
        data     = request.get_json()
        email    = data.get('email')
        password = data.get('password')
        cursor   = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT * FROM users WHERE email=%s", (email,))
        user = cursor.fetchone()
        cursor.close()
        if not user or not check_password_hash(user['password'], password):
            return jsonify({'error': 'Invalid email or password'}), 401
        session.update({'user_id': user['id'], 'user_email': user['email'],
                        'user_type': user['role'], 'logged_in': True})
        return jsonify({'success': True, 'user': {
            'id': user['id'], 'email': user['email'],
            'role': user['role'], 'phoneNumber': user['phoneNumber']
        }}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route("/api/auth/logout", methods=["POST"])
def api_logout():
    session.clear()
    return jsonify({'success': True}), 200

@app.route("/api/auth/profile")
@login_required_api
def api_profile():
    user_id = session['user_id']
    cursor  = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT id,email,role,phoneNumber,created_at FROM users WHERE id=%s", (user_id,))
    user = cursor.fetchone()
    profile = None
    if user['role'] == 'student':
        cursor.execute("SELECT * FROM students WHERE user_id=%s", (user_id,))
        profile = cursor.fetchone()
        if profile:
            cursor.execute("SELECT s.name FROM skills s JOIN student_skills ss ON s.id=ss.skill_id WHERE ss.student_id=%s", (profile['id'],))
            profile['skills'] = [r['name'] for r in cursor.fetchall()]
        else:
            cursor.execute("INSERT INTO students (user_id,first_name,last_name,placement_status,created_at) VALUES (%s,'','','unplaced',NOW())", (user_id,))
            mysql.connection.commit()
            cursor.execute("SELECT * FROM students WHERE user_id=%s", (user_id,))
            profile = cursor.fetchone()
            profile['skills'] = []
    elif user['role'] == 'company':
        cursor.execute("SELECT * FROM companies WHERE user_id=%s", (user_id,))
        profile = cursor.fetchone()
    cursor.close()
    return jsonify({'success': True, 'user': user, 'profile': profile}), 200

# ==================== API Student Profile ====================

@app.route("/api/student/profile", methods=["GET"])
@login_required_api
def api_get_student_profile():
    if session.get('user_type') != 'student':
        return jsonify({'error': 'Unauthorized'}), 403
    user_id = session['user_id']
    cursor  = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT id,email,role,phoneNumber,created_at FROM users WHERE id=%s", (user_id,))
    user = cursor.fetchone()
    cursor.execute("SELECT * FROM students WHERE user_id=%s", (user_id,))
    student = cursor.fetchone()
    if not student:
        cursor.execute("INSERT INTO students (user_id,first_name,last_name,placement_status,created_at) VALUES (%s,'','','unplaced',NOW())", (user_id,))
        mysql.connection.commit()
        cursor.execute("SELECT * FROM students WHERE user_id=%s", (user_id,))
        student = cursor.fetchone()
    cursor.execute("SELECT s.name FROM skills s JOIN student_skills ss ON s.id=ss.skill_id WHERE ss.student_id=%s", (student['id'],))
    student['skills'] = [r['name'] for r in cursor.fetchall()]
    cursor.close()
    return jsonify({'success': True, 'user': user, 'profile': student}), 200


@app.route("/api/student/profile", methods=["PUT"])
@login_required_api
def api_update_student_profile():
    if session.get('user_type') != 'student':
        return jsonify({'error': 'Unauthorized'}), 403
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    user_id = session['user_id']
    cursor  = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("""UPDATE students SET first_name=%s,last_name=%s,bio=%s,university=%s,
        field_of_study=%s,degree=%s,year=%s,github_link=%s,portfolio_link=%s,linkedin=%s WHERE user_id=%s""",
        (data.get('first_name',''), data.get('last_name',''), data.get('bio',''),
         data.get('university',''), data.get('field_of_study',''), data.get('degree',''),
         data.get('year',''), data.get('github_link',''), data.get('portfolio_link',''),
         data.get('linkedin',''), user_id))
    if data.get('phoneNumber'):
        cursor.execute("UPDATE users SET phoneNumber=%s WHERE id=%s", (data['phoneNumber'], user_id))
    skills_list = data.get('skills', [])
    cursor.execute("SELECT id FROM students WHERE user_id=%s", (user_id,))
    student = cursor.fetchone()
    if student and skills_list is not None:
        sid = student['id']
        cursor.execute("DELETE FROM student_skills WHERE student_id=%s", (sid,))
        for skill_name in skills_list:
            skill_name = skill_name.strip()
            if not skill_name: continue
            cursor.execute("SELECT id FROM skills WHERE name=%s", (skill_name,))
            row = cursor.fetchone()
            if not row:
                cursor.execute("INSERT INTO skills (name) VALUES (%s)", (skill_name,))
                mysql.connection.commit()
                skill_id = cursor.lastrowid
            else:
                skill_id = row['id']
            cursor.execute("INSERT IGNORE INTO student_skills (student_id,skill_id) VALUES (%s,%s)", (sid, skill_id))
    mysql.connection.commit()
    cursor.close()
    return jsonify({'success': True, 'message': 'Profile updated successfully'}), 200

# ==================== API Internships ====================

@app.route("/api/internships")
def api_internships():
    location = request.args.get('wilaya', '')
    tech     = request.args.get('tech', '')
    type_    = request.args.get('type', '')
    search   = request.args.get('search', '')
    query = """SELECT io.*, c.company_name FROM internship_offers io
        LEFT JOIN companies c ON io.company_id=c.id WHERE io.status='open'"""
    params = []
    if location: query += " AND io.location=%s";        params.append(location)
    if type_:    query += " AND io.type=%s";             params.append(type_)
    if tech:     query += " AND io.technology LIKE %s";  params.append(f'%{tech}%')
    if search:
        query += " AND (io.title LIKE %s OR io.technology LIKE %s)"
        params += [f'%{search}%', f'%{search}%']
    query += " ORDER BY io.created_at DESC"
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute(query, params)
    offers = cursor.fetchall()
    cursor.close()
    for o in offers:
        o['technologies'] = o['technology'].split(',') if o['technology'] else []
        o['posted']       = o['created_at'].strftime('%d %b %Y') if o['created_at'] else ''
    return jsonify({'success': True, 'internships': offers, 'count': len(offers)}), 200


@app.route("/api/internships/apply", methods=["POST"])
@login_required_api
def api_apply():
    if session.get('user_type') != 'student':
        return jsonify({'error': 'Only students can apply'}), 403
    data     = request.get_json()
    offer_id = data.get('internship_id')
    if not offer_id:
        return jsonify({'error': 'internship_id required'}), 400
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT id FROM students WHERE user_id=%s", (session['user_id'],))
    student = cursor.fetchone()
    if not student:
        cursor.close()
        return jsonify({'error': 'Student profile not found'}), 404
    cursor.execute("SELECT id FROM applications WHERE student_id=%s AND offer_id=%s", (student['id'], offer_id))
    if cursor.fetchone():
        cursor.close()
        return jsonify({'error': 'Already applied'}), 409
    cursor.execute("INSERT INTO applications (student_id,offer_id,status,applied_at) VALUES (%s,%s,'pending',NOW())", (student['id'], offer_id))
    mysql.connection.commit()
    cursor.close()
    return jsonify({'success': True, 'message': 'Application submitted!'}), 201


@app.route("/api/student/applications")
@login_required_api
def api_student_applications():
    if session.get('user_type') != 'student':
        return jsonify({'error': 'Unauthorized'}), 403
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT id FROM students WHERE user_id=%s", (session['user_id'],))
    student = cursor.fetchone()
    if not student:
        cursor.close()
        return jsonify({'success': True, 'applications': []}), 200
    cursor.execute("""SELECT a.id, a.status, a.applied_at,
               io.title as position, io.location as wilaya, io.type,
               c.company_name as company
        FROM applications a JOIN internship_offers io ON a.offer_id=io.id
        LEFT JOIN companies c ON io.company_id=c.id
        WHERE a.student_id=%s ORDER BY a.applied_at DESC""", (student['id'],))
    apps = cursor.fetchall()
    cursor.close()
    status_map = {'pending': 'In Review', 'accepted': 'Accepted', 'rejected': 'Rejected'}
    for a in apps:
        a['status']     = status_map.get(a['status'], a['status'])
        a['lastUpdate'] = a['applied_at'].strftime('%d %b %Y') if a['applied_at'] else ''
    return jsonify({'success': True, 'applications': apps, 'count': len(apps)}), 200


# ==================== AI Cover Letter with Mock ====================

@app.route("/api/generate-cover-letter", methods=["POST"])
@login_required_api
def generate_cover_letter():
    """✅ توليد cover letter (نسخة وهمية للاختبار)"""
    if session.get('user_type') != 'student':
        return jsonify({'error': 'Unauthorized'}), 403

    try:
        data = request.get_json()
        offer_id = data.get('offer_id')
        if not offer_id:
            return jsonify({'error': 'offer_id required'}), 400

        user_id = session['user_id']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        # جلب بيانات الطالب
        cursor.execute("SELECT * FROM students WHERE user_id=%s", (user_id,))
        student = cursor.fetchone()
        
        if not student:
            cursor.close()
            return jsonify({'error': 'Student profile not found'}), 404
            
        cursor.execute("SELECT s.name FROM skills s JOIN student_skills ss ON s.id=ss.skill_id WHERE ss.student_id=%s", (student['id'],))
        skills = [r['name'] for r in cursor.fetchall()]

        # جلب بيانات التربص
        cursor.execute("""SELECT io.*, c.company_name FROM internship_offers io
            LEFT JOIN companies c ON io.company_id=c.id WHERE io.id=%s""", (offer_id,))
        offer = cursor.fetchone()
        cursor.close()

        if not offer:
            return jsonify({'error': 'Offer not found'}), 404

        # توليد cover letter وهمي (Mock) للاختبار
        company_name = offer.get('company_name', 'the company')
        position = offer.get('title', 'the position')
        student_name = f"{student.get('first_name', '')} {student.get('last_name', '')}".strip() or "the candidate"
        
        mock_cover_letter = f"""
Dear {company_name} Team,

I am writing to express my strong interest in the {position} internship position at {company_name}. As a {student.get('degree', 'university')} student in {student.get('field_of_study', 'Computer Science')} at {student.get('university', 'my university')}, I have developed a strong foundation in {', '.join(skills) if skills else 'various technologies'} that align perfectly with your requirements.

During my academic journey, I have worked on several projects that have prepared me for this internship. My skills in {', '.join(skills[:3]) if skills else 'programming and problem-solving'} would allow me to contribute effectively to your team. I am particularly excited about this opportunity because {offer.get('description', 'it aligns with my career goals')}.

I am confident that my enthusiasm, dedication, and technical skills make me a strong candidate for this position. I am eager to bring my knowledge and passion to {company_name} and learn from your experienced team.

Thank you for considering my application. I look forward to the opportunity to discuss how I can contribute to your organization.

Sincerely,
{student_name}
"""
        return jsonify({'success': True, 'cover_letter': mock_cover_letter}), 200
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return jsonify({'error': f'Error: {str(e)}'}), 500

# ==================== Test Routes ====================

@app.route("/api/test-gemini", methods=["GET"])
def test_gemini():
    """اختبار اتصال Gemini API"""
    try:
        test_prompt = "Say 'Hello, API is working!' in one sentence."
        
        # استخدام النموذج gemini-pro
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={GEMINI_API_KEY}"
        
        payload = {
            "contents": [{
                "parts": [{"text": test_prompt}]
            }]
        }
        
        print("Testing Gemini API with gemini-pro...")
        response = http_requests.post(url, json=payload, timeout=10)
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            if 'candidates' in result and len(result['candidates']) > 0:
                text = result['candidates'][0]['content']['parts'][0]['text']
                return jsonify({
                    'success': True, 
                    'message': 'Gemini API is working!', 
                    'response': text
                })
            else:
                return jsonify({
                    'success': False, 
                    'error': 'No candidates in response',
                    'full_response': result
                })
        else:
            return jsonify({
                'success': False,
                'status_code': response.status_code,
                'error': response.text
            })
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route("/api/list-models", methods=["GET"])
def list_models():
    """عرض جميع النماذج المتاحة"""
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models?key={GEMINI_API_KEY}"
        response = http_requests.get(url)
        return jsonify(response.json())
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route("/api/test-offer/<int:offer_id>", methods=["GET"])
@login_required_api
def test_offer(offer_id):
    """اختبار جلب بيانات العرض"""
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("""SELECT io.*, c.company_name FROM internship_offers io
        LEFT JOIN companies c ON io.company_id=c.id WHERE io.id=%s""", (offer_id,))
    offer = cursor.fetchone()
    cursor.close()
    
    if offer:
        return jsonify({'success': True, 'offer': offer})
    else:
        return jsonify({'success': False, 'error': 'Offer not found'})

# ==================== HTML Pages ====================

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email    = request.form.get("email")
        password = request.form.get("password")
        cursor   = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT * FROM users WHERE email=%s", (email,))
        user = cursor.fetchone()
        cursor.close()
        if user and check_password_hash(user['password'], password):
            session.update({'user_id': user['id'], 'user_email': user['email'],
                            'user_type': user['role'], 'logged_in': True})
            flash('Login successful!', 'success')
            if user['role'] == 'student':   return redirect(url_for('student_dashboard'))
            elif user['role'] == 'company': return redirect(url_for('company_dashboard'))
            elif user['role'] == 'admin':   return redirect(url_for('admin_dashboard'))
        flash('Invalid email or password', 'danger')
    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email    = request.form.get("email")
        password = request.form.get("password")
        role     = request.form.get("userType", "student")
        phone    = request.form.get("phone")
        if password != request.form.get("confirmPassword"):
            flash('Passwords do not match', 'danger')
            return redirect(url_for('register'))
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT id FROM users WHERE email=%s", (email,))
        if cursor.fetchone():
            cursor.close()
            flash('Email already registered', 'danger')
            return redirect(url_for('register'))
        cursor.execute("INSERT INTO users (email,password,role,phoneNumber,created_at) VALUES (%s,%s,%s,%s,NOW())",
                       (email, generate_password_hash(password), role, phone))
        mysql.connection.commit()
        user_id = cursor.lastrowid
        if role == 'student':
            cursor.execute("INSERT INTO students (user_id,first_name,last_name,placement_status,created_at) VALUES (%s,%s,%s,'unplaced',NOW())",
                           (user_id, request.form.get("first_name",""), request.form.get("last_name","")))
            mysql.connection.commit()
        cursor.close()
        session.update({'user_id': user_id, 'user_email': email, 'user_type': role, 'logged_in': True})
        flash('Registration successful!', 'success')
        if role == 'student':   return redirect(url_for('student_dashboard'))
        elif role == 'company': return redirect(url_for('company_dashboard'))
        elif role == 'admin':   return redirect(url_for('admin_dashboard'))
    return render_template("register.html")

@app.route("/logout")
def logout():
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('home'))

# ==================== Student Pages ====================

@app.route("/student-dashboard")
@login_required_web
def student_dashboard():
    if session.get('user_type') != 'student':
        return redirect(url_for('home'))
    user_id = session['user_id']
    cursor  = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM students WHERE user_id=%s", (user_id,))
    student = cursor.fetchone()
    stats = {'total': 0, 'review': 0, 'accepted': 0}
    recent_applications = []
    recent_offers = []
    if student:
        cursor.execute("SELECT COUNT(*) as c FROM applications WHERE student_id=%s", (student['id'],))
        stats['total'] = cursor.fetchone()['c']
        cursor.execute("SELECT COUNT(*) as c FROM applications WHERE student_id=%s AND status='pending'", (student['id'],))
        stats['review'] = cursor.fetchone()['c']
        cursor.execute("SELECT COUNT(*) as c FROM applications WHERE student_id=%s AND status='accepted'", (student['id'],))
        stats['accepted'] = cursor.fetchone()['c']
        cursor.execute("""SELECT a.status, io.title as position
            FROM applications a JOIN internship_offers io ON a.offer_id=io.id
            WHERE a.student_id=%s ORDER BY a.applied_at DESC LIMIT 3""", (student['id'],))
        recent_applications = cursor.fetchall()
        for a in recent_applications:
            sm = {'pending': 'In Review', 'accepted': 'Accepted', 'rejected': 'Rejected'}
            a['status'] = sm.get(a['status'], a['status'])
    cursor.execute("""SELECT io.*, c.company_name FROM internship_offers io
        LEFT JOIN companies c ON io.company_id=c.id
        WHERE io.status='open' ORDER BY io.created_at DESC LIMIT 4""")
    for o in cursor.fetchall():
        o['technologies'] = o['technology'].split(',') if o['technology'] else []
        recent_offers.append(o)
    cursor.close()
    name   = f"{student.get('first_name','')} {student.get('last_name','')}".strip() if student else 'Student'
    avatar = ((student.get('first_name') or 'S')[0] + (student.get('last_name') or '')[0]).upper() if student else 'ST'
    return render_template("student_dashboard.html",
        student=student, stats=stats,
        recent_applications=recent_applications,
        recent_internships=recent_offers,
        name=name, avatar=avatar)


@app.route("/student-profile")
@login_required_web
def student_profile():
    if session.get('user_type') != 'student':
        return redirect(url_for('home'))
    user_id = session['user_id']
    cursor  = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM users WHERE id=%s", (user_id,))
    user = cursor.fetchone()
    cursor.execute("SELECT * FROM students WHERE user_id=%s", (user_id,))
    student = cursor.fetchone()
    if not student:
        cursor.execute("INSERT INTO students (user_id,first_name,last_name,placement_status,created_at) VALUES (%s,'','','unplaced',NOW())", (user_id,))
        mysql.connection.commit()
        cursor.execute("SELECT * FROM students WHERE user_id=%s", (user_id,))
        student = cursor.fetchone()
    cursor.execute("SELECT s.name FROM skills s JOIN student_skills ss ON s.id=ss.skill_id WHERE ss.student_id=%s", (student['id'],))
    student['skills'] = [r['name'] for r in cursor.fetchall()]
    cursor.close()
    degree = student.get('degree') or ''
    degree_options = Markup(''.join(
        f'<option value="{v}" {"selected" if v==degree else ""}>{l}</option>'
        for v,l in [('License',"Bachelor's (License)"),('Master',"Master's"),('PhD','PhD')]
    ))
    yr = str(student.get('year') or '')
    year_options = Markup(''.join(
        f'<option value="{y}" {"selected" if y==yr else ""}>{y}</option>'
        for y in ['L1','L2','L3','M1','M2']
    ))
    return render_template("student_profile.html",
        student=student, user=user,
        degree_options=degree_options, year_options=year_options,
        avatar_initials=((student.get('first_name') or 'S')[0]+(student.get('last_name') or '')[0]).upper(),
        skills_json=json.dumps(student['skills']),
        cv_display=Markup(f'<p class="cv-current">📄 {student["cv"]}</p>' if student.get('cv') else ''))


@app.route("/student-profile/edit", methods=["GET", "POST"])
@login_required_web
def student_profile_edit():
    if request.method == "POST":
        user_id = session['user_id']
        cursor  = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("""UPDATE students SET first_name=%s,last_name=%s,bio=%s,university=%s,
            field_of_study=%s,degree=%s,year=%s,github_link=%s,portfolio_link=%s,linkedin=%s WHERE user_id=%s""",
            (request.form.get('first_name',''), request.form.get('last_name',''),
             request.form.get('bio',''), request.form.get('university',''),
             request.form.get('field_of_study',''), request.form.get('degree',''),
             request.form.get('year',''), request.form.get('github_link',''),
             request.form.get('portfolio_link',''), request.form.get('linkedin',''), user_id))
        phone = request.form.get('phone','').strip()
        if phone:
            cursor.execute("UPDATE users SET phoneNumber=%s WHERE id=%s", (phone, user_id))
        try:
            skills_list = [s.strip() for s in json.loads(request.form.get('skills','[]')) if s.strip()]
        except:
            skills_list = []
        cursor.execute("SELECT id FROM students WHERE user_id=%s", (user_id,))
        sid = cursor.fetchone()['id']
        cursor.execute("DELETE FROM student_skills WHERE student_id=%s", (sid,))
        for name in skills_list:
            cursor.execute("SELECT id FROM skills WHERE name=%s", (name,))
            row = cursor.fetchone()
            if not row:
                cursor.execute("INSERT INTO skills (name) VALUES (%s)", (name,))
                mysql.connection.commit()
                skill_id = cursor.lastrowid
            else:
                skill_id = row['id']
            cursor.execute("INSERT IGNORE INTO student_skills (student_id,skill_id) VALUES (%s,%s)", (sid, skill_id))
        if 'cv' in request.files:
            f = request.files['cv']
            if f and f.filename:
                ext = f.filename.rsplit('.',1)[-1].lower()
                if ext in ALLOWED_CV:
                    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
                    fname = secure_filename(f"cv_{user_id}.{ext}")
                    f.save(os.path.join(UPLOAD_FOLDER, fname))
                    cursor.execute("UPDATE students SET cv=%s WHERE user_id=%s", (fname, user_id))
        mysql.connection.commit()
        cursor.close()
        flash('Profile updated successfully!', 'success')
    return redirect(url_for('student_profile'))


@app.route("/student-search")
@login_required_web
def student_search():
    if session.get('user_type') != 'student':
        return redirect(url_for('home'))
    location = request.args.get('wilaya', '')
    type_    = request.args.get('type', '')
    tech     = request.args.get('tech', '')
    search   = request.args.get('search', '')
    query = """SELECT io.*, c.company_name FROM internship_offers io
        LEFT JOIN companies c ON io.company_id=c.id WHERE io.status='open'"""
    params = []
    if location: query += " AND io.location=%s";        params.append(location)
    if type_:    query += " AND io.type=%s";             params.append(type_)
    if tech:     query += " AND io.technology LIKE %s";  params.append(f'%{tech}%')
    if search:
        query += " AND (io.title LIKE %s OR io.technology LIKE %s)"
        params += [f'%{search}%', f'%{search}%']
    query += " ORDER BY io.created_at DESC"
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute(query, params)
    raw = cursor.fetchall()
    cursor.close()
    internships = []
    for o in raw:
        o['technologies'] = o['technology'].split(',') if o['technology'] else []
        o['posted']       = o['created_at'].strftime('%d %b %Y') if o['created_at'] else ''
        o['wilaya']       = o['location']
        o['position']     = o['title']
        o['company']      = o.get('company_name') or 'Company'
        internships.append(o)
    return render_template("student_search.html", internships=internships)


@app.route("/my-applications")
@login_required_web
def my_applications():
    if session.get('user_type') != 'student':
        return redirect(url_for('home'))
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT id FROM students WHERE user_id=%s", (session['user_id'],))
    student = cursor.fetchone()
    applications = []
    if student:
        cursor.execute("""SELECT a.id, a.status, a.applied_at,
               io.title as position, io.location as wilaya, io.type,
               c.company_name as company
            FROM applications a
            JOIN internship_offers io ON a.offer_id=io.id
            LEFT JOIN companies c ON io.company_id=c.id
            WHERE a.student_id=%s ORDER BY a.applied_at DESC""", (student['id'],))
        sm = {'pending': 'In Review', 'accepted': 'Accepted', 'rejected': 'Rejected'}
        for a in cursor.fetchall():
            a['status']     = sm.get(a['status'], a['status'])
            a['lastUpdate'] = a['applied_at'].strftime('%d %b %Y') if a['applied_at'] else ''
            applications.append(a)
    cursor.close()
    return render_template("student_applications.html", applications=applications)


@app.route("/apply/<int:offer_id>", methods=["POST"])
@login_required_web
def apply_internship(offer_id):
    if session.get('user_type') != 'student':
        flash('Access denied', 'danger')
        return redirect(url_for('home'))
    cover_letter = request.form.get('cover_letter', '')
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT id FROM students WHERE user_id=%s", (session['user_id'],))
    student = cursor.fetchone()
    if not student:
        flash('Student profile not found', 'danger')
        cursor.close()
        return redirect(url_for('student_search'))
    cursor.execute("SELECT id FROM applications WHERE student_id=%s AND offer_id=%s", (student['id'], offer_id))
    if cursor.fetchone():
        flash('You already applied!', 'warning')
        cursor.close()
        return redirect(url_for('student_search'))
    cursor.execute("INSERT INTO applications (student_id,offer_id,status,applied_at,agreement_pdf) VALUES (%s,%s,'pending',NOW(),%s)",
                   (student['id'], offer_id, cover_letter))
    mysql.connection.commit()
    cursor.close()
    flash('Application submitted successfully! ✅', 'success')
    return redirect(url_for('my_applications'))


@app.route("/application/<int:id>")
@login_required_web
def application_details(id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT id FROM students WHERE user_id=%s", (session['user_id'],))
    student = cursor.fetchone()
    cursor.execute("""SELECT a.*, io.title as position, io.location as wilaya,
               io.type, io.duration, io.technology, io.description, c.company_name as company
        FROM applications a JOIN internship_offers io ON a.offer_id=io.id
        LEFT JOIN companies c ON io.company_id=c.id
        WHERE a.id=%s AND a.student_id=%s""", (id, student['id'] if student else 0))
    application = cursor.fetchone()
    cursor.close()
    if not application:
        flash('Application not found', 'danger')
        return redirect(url_for('my_applications'))
    application['technologies'] = application['technology'].split(',') if application['technology'] else []
    sm = {'pending': 'In Review', 'accepted': 'Accepted', 'rejected': 'Rejected'}
    application['status'] = sm.get(application['status'], application['status'])
    return render_template("application_details.html", application=application)


@app.route("/withdraw/<int:id>", methods=["POST"])
@login_required_web
def withdraw_application(id):
    if session.get('user_type') != 'student':
        flash('Access denied', 'danger')
        return redirect(url_for('home'))
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT id FROM students WHERE user_id=%s", (session['user_id'],))
    student = cursor.fetchone()
    if not student:
        flash('Student not found', 'danger')
        cursor.close()
        return redirect(url_for('my_applications'))
    cursor.execute("SELECT id FROM applications WHERE id=%s AND student_id=%s", (id, student['id']))
    if not cursor.fetchone():
        flash('Application not found', 'danger')
        cursor.close()
        return redirect(url_for('my_applications'))
    cursor.execute("DELETE FROM applications WHERE id=%s", (id,))
    mysql.connection.commit()
    cursor.close()
    flash('Application withdrawn successfully', 'success')
    return redirect(url_for('my_applications'))

# ==================== Company ====================

@app.route("/company-dashboard")
@login_required_web
def company_dashboard():
    if session.get('user_type') != 'company': return redirect(url_for('home'))
    return render_template("CompanyDashboard.html")

@app.route("/company-profile")
@login_required_web
def company_profile():
    if session.get('user_type') != 'company': return redirect(url_for('home'))
    return render_template("CompanyProfile.html")

@app.route("/company-create-offer")
@login_required_web
def company_create_offer():
    if session.get('user_type') != 'company': return redirect(url_for('home'))
    return render_template("CompanyCreateNewOffer.html")

@app.route("/company-manage-offers")
@login_required_web
def company_manage_offers():
    if session.get('user_type') != 'company': return redirect(url_for('home'))
    return render_template("CompanyManageOffers.html")

@app.route("/company-applications")
@login_required_web
def company_applications():
    if session.get('user_type') != 'company': return redirect(url_for('home'))
    return render_template("CompanyApplicatins.html")

# ==================== Admin ====================

@app.route("/admin-dashboard")
@login_required_web
def admin_dashboard():
    if session.get('user_type') != 'admin': return redirect(url_for('home'))
    return render_template("AdminDashboard.html")

@app.route("/admin-validation")
@login_required_web
def admin_validation():
    if session.get('user_type') != 'admin': return redirect(url_for('home'))
    return render_template("AdminValidation.html")

@app.route("/admin-statistics")
@login_required_web
def admin_statistics():
    if session.get('user_type') != 'admin': return redirect(url_for('home'))
    return render_template("AdminStatistics.html")

if __name__ == "__main__":
    print("\n🚀 http://127.0.0.1:5000")
    app.run(debug=True)