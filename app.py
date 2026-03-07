from flask import Flask, render_template, redirect, url_for, request, session
import os

app = Flask(__name__)
app.secret_key = "your_secret_key_here_change_this_in_production"

# ---------------- HOME ----------------
@app.route("/")
def home():
    return render_template("index.html")

# ---------------- LOGIN ----------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        # Récupère les données du formulaire
        email = request.form.get("email")
        password = request.form.get("password")
        user_type = request.form.get("userType", "student")
        
        print(f"Login attempt - Email: {email}, Type: {user_type}")
        
        # Store user info in session
        session['user_email'] = email
        session['user_type'] = user_type
        session['logged_in'] = True
        
        # Redirige vers le vrai dashboard selon le type
        if user_type == "student":
            return redirect(url_for("student_dashboard"))
        elif user_type == "company":
            return redirect(url_for("company_dashboard"))
        elif user_type == "admin":
            return redirect(url_for("admin_dashboard"))
    
    # GET request - affiche la page de login
    user_type = request.args.get('type', 'student')
    return render_template("login.html", user_type=user_type)

# ---------------- REGISTER ----------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        # Get user type first
        user_type = request.form.get("userType", "student")
        
        # Common fields for both
        email = request.form.get("email")
        password = request.form.get("password")
        confirm_password = request.form.get("confirmPassword")
        phone = request.form.get("phone")
        
        print(f"Register attempt - Email: {email}, Type: {user_type}")
        
        # Basic validation
        if password != confirm_password:
            print("Passwords don't match")
            # You might want to add flash messages here
            return redirect(url_for("register", type=user_type))
        
        # Store user info in session
        session['user_email'] = email
        session['user_type'] = user_type
        session['logged_in'] = True
        
        # Handle based on user type
        if user_type == "student":
            # Student specific fields
            first_name = request.form.get("firstName", "")
            last_name = request.form.get("lastName", "")
            
            print(f"Student Data - Name: {first_name} {last_name}")
            print(f"Phone: {phone}")
            print(f"Email: {email}")
            
            # TODO: Save to database here
            # For now, just redirect to dashboard
            return redirect(url_for("student_dashboard"))
            
        elif user_type == "company":
            # Company specific fields
            company_name = request.form.get("companyName", "")
            wilaya = request.form.get("wilaya", "")
            address = request.form.get("address", "")
            
            print(f"Company Data - Name: {company_name}")
            print(f"Wilaya: {wilaya}, Address: {address}")
            print(f"Phone: {phone}")
            print(f"Email: {email}")
            
            # TODO: Save to database here
            # For now, just redirect to dashboard
            return redirect(url_for("company_dashboard"))
            
        elif user_type == "admin":
            return redirect(url_for("admin_dashboard"))
    
    # GET request - affiche la page d'inscription
    user_type = request.args.get('type', 'student')
    return render_template("register.html", user_type=user_type)

# ---------------- STUDENT PAGES ----------------
@app.route("/student-dashboard")
def student_dashboard():
    # Check if user is logged in
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    return render_template("student_dashboard.html", active_page='dashboard')

@app.route("/student-profile")
def student_profile():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    return render_template("student_profile.html", active_page='profile')

@app.route("/student-search")
def student_search():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    # Get filter parameters from request
    wilaya = request.args.get('wilaya', '')
    type_filter = request.args.get('type', '')
    tech = request.args.get('tech', '')
    search = request.args.get('search', '')
    
    internships = [
        {"id": 1, "company": "TechCorp Algeria", "position": "Full Stack Developer", "wilaya": "Alger", "type": "Full-time", "duration": "6 months", "technologies": ["React", "Node.js", "MongoDB"], "posted": "2 days ago"},
        {"id": 2, "company": "InnovaSoft", "position": "Frontend Developer", "wilaya": "Oran", "type": "Full-time", "duration": "4 months", "technologies": ["Vue.js", "TypeScript"], "posted": "1 week ago"},
        {"id": 3, "company": "DataSolutions", "position": "Data Analyst", "wilaya": "Constantine", "type": "Part-time", "duration": "3 months", "technologies": ["Python", "SQL", "Tableau"], "posted": "3 days ago"},
        {"id": 4, "company": "CloudNine", "position": "Backend Developer", "wilaya": "Alger", "type": "Full-time", "duration": "6 months", "technologies": ["Java", "Spring Boot", "PostgreSQL"], "posted": "5 days ago"},
        {"id": 5, "company": "MobileFirst", "position": "Mobile Developer", "wilaya": "Blida", "type": "Full-time", "duration": "5 months", "technologies": ["React Native", "Flutter"], "posted": "1 day ago"},
        {"id": 6, "company": "SecureNet", "position": "Cybersecurity Intern", "wilaya": "Oran", "type": "Full-time", "duration": "6 months", "technologies": ["Security", "Networking"], "posted": "4 days ago"},
    ]
    
    # Apply filters (simple filtering for demonstration)
    filtered_internships = internships
    if wilaya:
        filtered_internships = [i for i in filtered_internships if i['wilaya'] == wilaya]
    if type_filter:
        filtered_internships = [i for i in filtered_internships if i['type'] == type_filter]
    if tech:
        filtered_internships = [i for i in filtered_internships if any(tech.lower() in t.lower() for t in i['technologies'])]
    if search:
        search_lower = search.lower()
        filtered_internships = [i for i in filtered_internships if 
                               search_lower in i['position'].lower() or 
                               search_lower in i['company'].lower() or
                               any(search_lower in t.lower() for t in i['technologies'])]
    
    return render_template("student_search.html", internships=filtered_internships, active_page='search')

# ---------------- MY APPLICATIONS ROUTE ----------------
@app.route("/my-applications")
def my_applications():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    applications = [
        {"id": 1, "position": "Full Stack Developer", "company": "TechCorp Algeria", "status": "In Review", "lastUpdate": "2 days ago"},
        {"id": 2, "position": "Frontend Developer", "company": "InnovaSoft", "status": "Accepted", "lastUpdate": "1 week ago"},
        {"id": 3, "position": "Data Analyst", "company": "DataSolutions", "status": "In Review", "lastUpdate": "3 days ago"},
        {"id": 4, "position": "Backend Developer", "company": "CloudNine", "status": "Rejected", "lastUpdate": "10 days ago"},
    ]
    return render_template("student_applications.html", applications=applications, active_page='applications')

# ---------------- APPLICATION DETAILS ROUTE ----------------
@app.route("/application-details/<int:id>")
def application_details(id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    # Base de données complète avec tous les détails
    all_items = [
        {
            "id": 1, 
            "position": "Full Stack Developer", 
            "company": "TechCorp Algeria", 
            "status": "In Review", 
            "date": "2024-02-15", 
            "lastUpdate": "2 days ago", 
            "description": "Full stack development position with React and Flask. You will work on developing modern web applications using cutting-edge technologies.",
            "location": "Algiers", 
            "type": "Full-time", 
            "duration": "6 months", 
            "technologies": ["React", "Node.js", "MongoDB"]
        },
        {
            "id": 2, 
            "position": "Frontend Developer", 
            "company": "InnovaSoft", 
            "status": "Accepted", 
            "date": "2024-02-10", 
            "lastUpdate": "1 week ago", 
            "description": "Frontend development with Vue.js and Tailwind CSS. Create beautiful and responsive user interfaces.",
            "location": "Oran", 
            "type": "Full-time", 
            "duration": "4 months", 
            "technologies": ["Vue.js", "TypeScript"]
        },
        {
            "id": 3, 
            "position": "Data Analyst", 
            "company": "DataSolutions", 
            "status": "In Review", 
            "date": "2024-02-14", 
            "lastUpdate": "3 days ago", 
            "description": "Data analysis with Python and SQL. Work with large datasets to extract valuable insights.",
            "location": "Constantine", 
            "type": "Part-time", 
            "duration": "3 months", 
            "technologies": ["Python", "SQL", "Tableau"]
        },
        {
            "id": 4, 
            "position": "Backend Developer", 
            "company": "CloudNine", 
            "status": "Rejected", 
            "date": "2024-02-08", 
            "lastUpdate": "10 days ago", 
            "description": "Backend development with Python and AWS. Build scalable and secure backend services.",
            "location": "Remote", 
            "type": "Full-time", 
            "duration": "6 months", 
            "technologies": ["Java", "Spring Boot", "PostgreSQL"]
        },
        {
            "id": 5, 
            "position": "Mobile Developer", 
            "company": "MobileFirst", 
            "status": "In Review", 
            "date": "2024-02-16", 
            "lastUpdate": "1 day ago", 
            "description": "Mobile development with React Native and Flutter. Create cross-platform mobile applications.",
            "location": "Blida", 
            "type": "Full-time", 
            "duration": "5 months", 
            "technologies": ["React Native", "Flutter"]
        },
        {
            "id": 6, 
            "position": "Cybersecurity Intern", 
            "company": "SecureNet", 
            "status": "In Review", 
            "date": "2024-02-12", 
            "lastUpdate": "4 days ago", 
            "description": "Cybersecurity internship focusing on network security, penetration testing, and security protocols.",
            "location": "Oran", 
            "type": "Full-time", 
            "duration": "6 months", 
            "technologies": ["Security", "Networking"]
        },
    ]
    
    # Rechercher l'élément par ID
    item = next((item for item in all_items if item["id"] == id), None)
    
    if item:
        return render_template("application_details.html", application=item)
    else:
        # Rediriger vers la liste des applications si l'ID n'existe pas
        return redirect(url_for("my_applications"))

# ---------------- COMPANY PAGES ----------------
@app.route("/company-dashboard")
def company_dashboard():
    # Check if user is logged in and is a company
    if not session.get('logged_in') or session.get('user_type') != 'company':
        return redirect(url_for('login'))
    return render_template("CompanyDashboard.html")

@app.route("/company-profile")
def company_profile():
    if not session.get('logged_in') or session.get('user_type') != 'company':
        return redirect(url_for('login'))
    return render_template("CompanyProfile.html")

@app.route("/company-create-offer")
def company_create_offer():
    if not session.get('logged_in') or session.get('user_type') != 'company':
        return redirect(url_for('login'))
    return render_template("CompanyCreateNewOffer.html")

@app.route("/company-manage-offers")
def company_manage_offers():
    if not session.get('logged_in') or session.get('user_type') != 'company':
        return redirect(url_for('login'))
    return render_template("CompanyManageOffers.html")

@app.route("/company-applications")
def company_applications():
    if not session.get('logged_in') or session.get('user_type') != 'company':
        return redirect(url_for('login'))
    return render_template("CompanyApplicatins.html")  # Note: garde la faute d'orthographe pour correspondre au nom du fichier

# ---------------- ADMIN PAGES ----------------
@app.route("/admin-dashboard")
def admin_dashboard():
    if not session.get('logged_in') or session.get('user_type') != 'admin':
        return redirect(url_for('login'))
    return render_template("AdminDashboard.html")

@app.route("/admin-validation")
def admin_validation():
    if not session.get('logged_in') or session.get('user_type') != 'admin':
        return redirect(url_for('login'))
    return render_template("AdminValidation.html")

@app.route("/admin-statistics")
def admin_statistics():
    if not session.get('logged_in') or session.get('user_type') != 'admin':
        return redirect(url_for('login'))
    return render_template("AdminStatistics.html")

# ---------------- LOGOUT ROUTE ----------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

# ---------------- DEBUG ROUTE ----------------
@app.route("/debug-templates")
def debug_templates():
    template_folder = app.template_folder
    files = os.listdir(template_folder)
    return f"Template folder: {template_folder}<br>Files: {', '.join(files)}"

@app.route("/test")
def test():
    return "Flask is working! Routes available: /company-dashboard, /company-profile, /company-manage-offers, /company-applications"

if __name__ == "__main__":
    print("\n=== Starting Flask App ===")
    print("Available routes:")
    print("  ✓ /")
    print("  ✓ /login")
    print("  ✓ /register") 
    print("  ✓ /company-dashboard")
    print("  ✓ /company-profile")
    print("  ✓ /company-manage-offers")
    print("  ✓ /company-applications")
    print("  ✓ /company-create-offer")
    print("  ✓ /student-dashboard")
    print("  ✓ /admin-dashboard")
    print("  ✓ /logout")
    print("  ✓ /test")
    print("\nAccess the app at: http://127.0.0.1:5000\n")
    app.run(debug=True)