from flask import Flask, render_template, redirect, url_for, request, session
import os
from flask_mysqldb import MySQL

app = Flask(__name__)
app.secret_key = "your_secret_key_here_change_this_in_production"

# ---------------- DATABASE CONFIG ----------------
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'internship_platform'

mysql = MySQL(app)

# ---------------- HOME ----------------
@app.route("/")
def home():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM users")
    data = cur.fetchall()
    cur.close()
    return render_template("index.html", users=data)

# ---------------- LOGIN ----------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        user_type = request.form.get("userType", "student")

        session['user_email'] = email
        session['user_type'] = user_type
        session['logged_in'] = True

        if user_type == "student":
            return redirect(url_for("student_dashboard"))
        elif user_type == "company":
            return redirect(url_for("company_dashboard"))
        elif user_type == "admin":
            return redirect(url_for("admin_dashboard"))

    user_type = request.args.get('type', 'student')
    return render_template("login.html", user_type=user_type)

# ---------------- REGISTER ----------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":

        user_type = request.form.get("userType", "student")
        email = request.form.get("email")
        password = request.form.get("password")
        confirm_password = request.form.get("confirmPassword")
        phone = request.form.get("phone")

        if password != confirm_password:
            return redirect(url_for("register", type=user_type))

        cur = mysql.connection.cursor()
        cur.execute(
            "INSERT INTO users (email, password, role, phoneNumber) VALUES (%s,%s,%s,%s)",
            (email, password, user_type, phone)
        )
        mysql.connection.commit()
        cur.close()

        session['user_email'] = email
        session['user_type'] = user_type
        session['logged_in'] = True

        if user_type == "student":
            return redirect(url_for("student_dashboard"))
        elif user_type == "company":
            return redirect(url_for("company_dashboard"))
        elif user_type == "admin":
            return redirect(url_for("admin_dashboard"))

    user_type = request.args.get('type', 'student')
    return render_template("register.html", user_type=user_type)

# ---------------- STUDENT DASHBOARD ----------------
@app.route("/student-dashboard")
def student_dashboard():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    return render_template("student_dashboard.html")

# ---------------- STUDENT PROFILE ----------------
@app.route("/student-profile")
def student_profile():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    return render_template("student_profile.html")

# ---------------- STUDENT SEARCH ----------------
@app.route("/student-search")
def student_search():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    internships = [
        {"id": 1, "company": "TechCorp Algeria", "position": "Full Stack Developer", "wilaya": "Alger"},
        {"id": 2, "company": "InnovaSoft", "position": "Frontend Developer", "wilaya": "Oran"},
        {"id": 3, "company": "DataSolutions", "position": "Data Analyst", "wilaya": "Constantine"}
    ]

    return render_template("student_search.html", internships=internships)

# ---------------- STUDENT APPLICATIONS ----------------
@app.route("/my-applications")
def my_applications():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    applications = [
        {"id": 1, "position": "Full Stack Developer", "company": "TechCorp Algeria", "status": "In Review"},
        {"id": 2, "position": "Frontend Developer", "company": "InnovaSoft", "status": "Accepted"},
    ]

    return render_template("student_applications.html", applications=applications)

# ---------------- APPLICATION DETAILS ----------------
@app.route("/application-details/<int:id>")
def application_details(id):

    items = [
        {"id": 1, "position": "Full Stack Developer", "company": "TechCorp Algeria"},
        {"id": 2, "position": "Frontend Developer", "company": "InnovaSoft"}
    ]

    item = next((i for i in items if i["id"] == id), None)

    if item:
        return render_template("application_details.html", application=item)

    return redirect(url_for("my_applications"))

# ---------------- COMPANY DASHBOARD ----------------
@app.route("/company-dashboard")
def company_dashboard():
    if not session.get('logged_in') or session.get('user_type') != 'company':
        return redirect(url_for('login'))
    return render_template("CompanyDashboard.html")

# ---------------- COMPANY PROFILE ----------------
@app.route("/company-profile")
def company_profile():
    if not session.get('logged_in') or session.get('user_type') != 'company':
        return redirect(url_for('login'))
    return render_template("CompanyProfile.html")

# ---------------- COMPANY CREATE OFFER ----------------
@app.route("/company-create-offer")
def company_create_offer():
    if not session.get('logged_in') or session.get('user_type') != 'company':
        return redirect(url_for('login'))
    return render_template("CompanyCreateNewOffer.html")

# ---------------- COMPANY MANAGE OFFERS ----------------
@app.route("/company-manage-offers")
def company_manage_offers():
    if not session.get('logged_in') or session.get('user_type') != 'company':
        return redirect(url_for('login'))
    return render_template("CompanyManageOffers.html")

# ---------------- COMPANY APPLICATIONS ----------------
@app.route("/company-applications")
def company_applications():
    if not session.get('logged_in') or session.get('user_type') != 'company':
        return redirect(url_for('login'))
    return render_template("CompanyApplicatins.html")

# ---------------- ADMIN DASHBOARD ----------------
@app.route("/admin-dashboard")
def admin_dashboard():
    if not session.get('logged_in') or session.get('user_type') != 'admin':
        return redirect(url_for('login'))
    return render_template("AdminDashboard.html")

# ---------------- ADMIN VALIDATION ----------------
@app.route("/admin-validation")
def admin_validation():
    if not session.get('logged_in') or session.get('user_type') != 'admin':
        return redirect(url_for('login'))
    return render_template("AdminValidation.html")

# ---------------- ADMIN STATISTICS ----------------
@app.route("/admin-statistics")
def admin_statistics():
    if not session.get('logged_in') or session.get('user_type') != 'admin':
        return redirect(url_for('login'))
    return render_template("AdminStatistics.html")

# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

# ---------------- DEBUG ----------------
@app.route("/debug-templates")
def debug_templates():
    template_folder = app.template_folder
    files = os.listdir(template_folder)
    return f"Template folder: {template_folder}<br>Files: {', '.join(files)}"

@app.route("/test")
def test():
    return "Flask is working!"


# ---------------- RUN APP ----------------
if __name__ == "__main__":
    print("\n=== Starting Flask App ===")
    print("Access the app at: http://127.0.0.1:5000\n")
    app.run(debug=True)