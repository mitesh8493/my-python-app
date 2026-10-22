from flask import Flask, render_template, request, redirect, session
from functools import wraps

import mysql.connector
import hashlib
import os

app = Flask(__name__)
app.secret_key = "taskmanagement"
def role_required(*roles):
    def wrapper(func):
        @wraps(func)
        def decorated(*args, **kwargs):
            if "user" not in session:
                return redirect("/login")
            if session.get("role") not in roles:
                return "Access Denied ❌"
            return func(*args, **kwargs)
        return decorated
    return wrapper

db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="",
    database="task_management"
)

# ---------------- HOME ----------------
@app.route("/")
def home():
    return render_template("home.html")

#----------------about----------------
@app.route("/about")
def about():

    cursor = db.cursor()

    cursor.execute("SELECT * FROM company WHERE id=%s", (session.get("company_id"),))
    company = cursor.fetchone()

    cursor.close()

    return render_template("about.html", company=company)
#--------editcompany--------
@app.route("/edit_company")
@role_required("admin")
def edit_company():

    cursor = db.cursor()
    cursor.execute("SELECT * FROM company WHERE id=%s", (session.get("company_id"),))
    company = cursor.fetchone()
    cursor.close()

    return render_template("edit_company.html", company=company)

#-----------------update company---------

@app.route("/update_company", methods=["POST"])
@role_required("admin")
def update_company():

    import os
    from werkzeug.utils import secure_filename

    company_name = request.form['company_name']
    owner_name=request.form['owner_name']
    email = request.form.get('email')
    phone = request.form.get('phone')
    address = request.form['address']
    city = request.form['city']
    state = request.form['state']

    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static/logos')
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)

    logo = request.files['logo']

    filename = None

    #  LOGO UPLOAD
    if logo and logo.filename != "":
        filename = secure_filename(logo.filename)
        logo.save(os.path.join(UPLOAD_FOLDER, filename))

        cursor = db.cursor()
        cursor.execute("""
            UPDATE company 
            SET company_name=%s,owner_name=%s,email=%s,phone=%s,address=%s,city=%s,state=%s,logo=%s
            WHERE id=%s
        """, (company_name,owner_name,email,phone,address,city,state,filename,session.get("company_id")))

    else:
        cursor = db.cursor()
        cursor.execute("""
            UPDATE company 
            SET company_name=%s,owner_name=%s,email=%s,phone=%s,address=%s,city=%s,state=%s
            WHERE id=%s
        """, (company_name,owner_name,email,phone,address,city,state,session.get("company_id")))

    db.commit()
    cursor.close()

    flash("Company Updated Successfully ")
    return redirect("/admin")

# ---------------- LOGIN ----------------
@app.route("/login")
def login():
    cursor = db.cursor()
    cursor.execute("SELECT id, company_name FROM company")
    companies = cursor.fetchall()
    cursor.close()

    return render_template("login.html", companies=companies)

@app.route('/login_user', methods=['POST'])
def login_user():
    email = request.form['email']
    password = request.form['password']

    hashed_password = hashlib.sha256(password.encode()).hexdigest()

    cursor = db.cursor(buffered=True)
    cursor.execute(
        "SELECT * FROM users WHERE email=%s AND password=%s",
        (email, hashed_password)
    )
    user = cursor.fetchone()
    cursor.close()

    if user:
     role = user[4].lower().strip()

    # 🔥 role mapping (FINAL FIX)
    if role in ["project manager", "manager"]:
        role = "manager"
    elif role == "admin":
        role = "admin"
    elif role == "employee":
        role = "employee"

    session['role'] = role
    session['user'] = user[2]
    session['company_id'] = user[15]

    return redirect("/" + role)
def log_action(email, action):
    cursor = db.cursor()
    cursor.execute(
        "INSERT INTO logs (user_email, action) VALUES (%s,%s)",
        (email, action)
    )
    db.commit()
    cursor.close()


def dashboard():
    if "user" not in session:
        return redirect("/login")

    role = session.get("role")

    if role == "admin":
        return redirect("/admin")
    elif role == "manager":
        return redirect("/manager")
    elif role == "employee":
        return redirect("/employee")
    else:
        return redirect("/customer")

    
@app.route("/add_company", methods=["GET", "POST"])
def add_company():

    if request.method == "POST":

        company_name = request.form['company_name']
        owner_name = request.form['owner_name']
        email = request.form['email']
        phone = request.form['phone']
        address = request.form['address']
        city = request.form['city']
        state = request.form['state']
        pincode = request.form['pincode']
        country = request.form['country']

        cursor = db.cursor()

        # 🔥 Insert company
        cursor.execute("""
            INSERT INTO company 
            (company_name, owner_name, email, phone, address, city, state, pincode, country)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (company_name, owner_name, email, phone, address, city, state, pincode, country))

        db.commit()

        # 🔥 Get company_id
        cursor.execute("SELECT LAST_INSERT_ID()")
        company_id = cursor.fetchone()[0]

        # 🔥 Create admin for that company
        import hashlib
        default_password = "123456"
        hashed_password = hashlib.sha256(default_password.encode()).hexdigest()

        cursor.execute("""
            INSERT INTO users (username, email, password, role, company_id)
            VALUES (%s,%s,%s,'admin',%s)
        """, (owner_name, email, hashed_password, company_id))

        db.commit()
        cursor.close()

        return "<script>alert('Company Added + Admin Created (password: 123456)'); window.location='/login';</script>"

    return render_template("add_company.html", company=None)

@app.route("/logs")
def logs():
    cursor = db.cursor()
    cursor.execute("SELECT * FROM logs ORDER BY time DESC")
    data = cursor.fetchall()
    cursor.close()
    return render_template("logs.html", logs=data)

@app.route("/users")
@role_required("admin", "manager")
def users():

    search = request.args.get("search", "")
    role_filter = request.args.get("role", "")

    page = int(request.args.get("page", 1))
    limit = 5
    offset = (page - 1) * limit

    cursor = db.cursor(dictionary=True)

    query = """
    SELECT 
        u.id,
        u.username,
        u.email,
        u.role,
        d.dept_name,
        c.company_name
    FROM users u
    LEFT JOIN department d ON u.dept_id = d.id
    LEFT JOIN company c ON u.company_id = c.id
    WHERE 1=1
    """

    params = []

    # 🔥 MOST IMPORTANT (company security)
    query += " AND u.company_id=%s"
    params.append(session.get("company_id"))

    # Manager restriction
    if session.get("role") == "manager":
        query += " AND u.role='employee'"

    # Search
    if search:
        query += " AND u.username LIKE %s"
        params.append(f"%{search}%")

    # Role filter
    if role_filter:
        query += " AND u.role=%s"
        params.append(role_filter)

    # Pagination
    query += " LIMIT %s OFFSET %s"
    params.extend([limit, offset])

    cursor.execute(query, params)
    users = cursor.fetchall()

    cursor.close()

    return render_template(
        "users.html",
        users=users,
        page=page,
        search=search,
        role_filter=role_filter
    )
    return render_template("users.html", users=users, page=page, search=search, role_filter=role_filter)

@app.route("/add_user", methods=["GET", "POST"])
def add_user():

    if session.get("role") not in ["admin", "manager"]:
        return "Access Denied ❌"

    if request.method == "POST":

        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']

        import hashlib
        hashed = hashlib.sha256(password.encode()).hexdigest()

        cursor = db.cursor()

        cursor.execute(
    "INSERT INTO users (username, email, password, role, company_id) VALUES (%s,%s,%s,%s,%s)",
    (username, email, hashed, role, session.get("company_id"))
)
        # add_user route में
        log_action(session['user'], f"Added new user {email}")

        db.commit()
        cursor.close()

        # 🔥 redirect based on role
        if session.get("role") == "admin":
            return redirect("/admin")
        else:
            return redirect("/manager")

    return render_template("add_user.html")

@app.route("/delete_user/<int:id>")
def delete_user(id):

    if session.get("role") not in ["admin", "manager"]:
        return "Access Denied ❌"

    cursor = db.cursor()
    cursor.execute("DELETE FROM users WHERE id=%s", (id,))
    log_action(session['user'], f"Deleted user ID {id}")
    db.commit()
    cursor.close()

    return redirect("/users")

@app.route("/edit_user/<int:id>", methods=["GET", "POST"])
def edit_user(id):

    if session.get("role") not in ["admin", "manager"]:
        return "Access Denied ❌"

    cursor = db.cursor()

    # 🔹 GET (form open)
    if request.method == "GET":

        # ✅ company-wise security
        cursor.execute("""
            SELECT * FROM users 
            WHERE id=%s AND company_id=%s
        """, (id, session.get("company_id")))
        user = cursor.fetchone()

        if not user:
            return "User not found ❌"

        # ✅ departments fetch
        cursor.execute("""
            SELECT id, dept_name 
            FROM department 
            WHERE company_id=%s
        """, (session.get("company_id"),))
        departments = cursor.fetchall()

        return render_template(
            "edit_user.html",
            user=user,
            departments=departments
        )

    # 🔹 POST (update)
    username = request.form['username']
    email = request.form['email']
    role = request.form['role']
    dept_id = request.form.get("dept_id")
    company_id=request.form.get("")

    # 🔥 Manager restriction
    if session.get("role") == "manager" and role != "employee":
        return "Manager can only assign employee role ❌"

    # 🔥 Update logic
    if role == "employee":
        cursor.execute("""
            UPDATE users 
            SET username=%s, email=%s, role=%s, dept_id=%s 
            WHERE id=%s AND company_id=%s
        """, (username, email, role, dept_id, id, session.get("company_id")))
    else:
        cursor.execute("""
            UPDATE users 
            SET username=%s, email=%s, role=%s, dept_id=NULL 
            WHERE id=%s AND company_id=%s
        """, (username, email, role, id, session.get("company_id")))

    db.commit()
    cursor.close()

    return redirect("/users")

@app.route("/add_department", methods=["GET", "POST"])
def add_department():

    if session.get("role") not in ["admin", "manager"]:
        return "Access Denied ❌"

    cursor = db.cursor()

    # 🔹 Form submit
    if request.method == "POST":

        dept_name = request.form['dept_name']

        cursor.execute("""
        INSERT INTO department (dept_name, company_id)
        VALUES (%s, %s)
        """, (dept_name, session.get("company_id")))

        db.commit()
        cursor.close()

        return redirect("/add_department")

    return render_template("add_department.html")


@app.route("/profile")
def profile():


    if "user" not in session:
        return redirect("/login")

    email = session['user']

    cursor = db.cursor(dictionary=True)  
    cursor.execute("""
        SELECT 
            u.*,
            d.dept_name,
            c.company_name
        FROM users u
        LEFT JOIN department d ON u.dept_id = d.id
        LEFT JOIN company c ON u.company_id = c.id
        WHERE u.email=%s
    """, (email,))
    user = cursor.fetchone()
    cursor.close()
    print(user)
    

    return render_template("profile.html", user=user)

@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect("/login")

    role = session.get("role")

    if role == "admin":
        return redirect("/admin")
    elif role == "manager":
        return redirect("/manager")
    elif role == "employee":
        return redirect("/employee")
    else:
        return redirect("/customer")

@app.route("/update_profile", methods=["POST"])
def update_profile():

    import os, hashlib, time

    if "user" not in session:
        return redirect("/login")

    email = session.get('user')  

    name = request.form.get('username')
    contact = request.form.get('contact')
    address = request.form.get('address')
    gender = request.form.get('gender')
    dob = request.form.get('dob')
    experience = request.form.get('experience')
    password = request.form.get('password')

    salary = request.form.get('salary')
    doj = request.form.get('doj')
    company_name = request.form.get('company_name') or None

    photo = request.files.get('photo')

    cursor = db.cursor()

    # 📸 PHOTO SAVE
    photo_name = None
    if photo and photo.filename != "":
        upload_path = "static/uploads"

        if not os.path.exists(upload_path):
            os.makedirs(upload_path)

        photo_name = str(int(time.time())) + "_" + photo.filename  
        photo.save(os.path.join(upload_path, photo_name))

    # 🔐 PASSWORD HASH
    if password:
        hashed = hashlib.sha256(password.encode()).hexdigest()

        cursor.execute("""
        UPDATE users 
        SET username=%s, password=%s, contact=%s, address=%s, 
            gender=%s, dob=%s, experience=%s,
            salary=%s, doj=%s, company_name=%s
        WHERE email=%s
        """, (
            name, hashed, contact, address,
            gender, dob, experience,
            salary, doj, company_name,
            email
        ))

    else:
        cursor.execute("""
        UPDATE users 
        SET username=%s, contact=%s, address=%s, 
            gender=%s, dob=%s, experience=%s,
            salary=%s, doj=%s, company_name=%s
        WHERE email=%s
        """, (
            name, contact, address,
            gender, dob, experience,
            salary, doj, company_name,
            email
        ))

    # 📷 PHOTO UPDATE
    if photo_name:
        cursor.execute(
            "UPDATE users SET photo=%s WHERE email=%s",
            (photo_name, email)
        )

    db.commit()
    cursor.close()
    return "<script>alert('Profile Updated ✅'); window.location='/profile';</script>"



# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# ---------------- REGISTER ----------------
@app.route("/register")
def register():
    cursor = db.cursor()
    cursor.execute("SELECT id, company_name FROM company")
    companies = cursor.fetchall()
    cursor.close()

    return render_template("register.html", companies=companies)

@app.route('/register_user', methods=["POST"])
def register_user():
    username = request.form['username']
    email = request.form['email']
    password = request.form['password']
    role = request.form['role']
    #address = request.form['address']
    #contact = request.form['contact']
    company_id = request.form.get("company_id")


    cursor = db.cursor()

    cursor.execute(
    "SELECT * FROM users WHERE email=%s AND company_id=%s",
    (email, company_id)
)

    if cursor.fetchone():
     cursor.close()
     return "User already exists in this company "
    hashed_password = hashlib.sha256(password.encode()).hexdigest()

    cursor.execute(
    "INSERT INTO users (username,email,password,role,company_id) VALUES (%s,%s,%s,%s,%s)",
    (username, email, hashed_password, role,company_id)
)
    db.commit()
    cursor.close()

    return redirect("/login")

# ---------------- FORGOT PASSWORD ----------------
@app.route("/forgot_password")
def forgot_password():
    return render_template("forgot_password.html")

@app.route("/check_email", methods=["POST"])
def check_email():
    email = request.form['email']

    cursor = db.cursor()
    cursor.execute("SELECT * FROM users WHERE email=%s", (email,))
    user = cursor.fetchone()
    cursor.close()

    if user:
        return render_template("reset_password.html", email=email)
    else:
        return "Email not found "

@app.route("/reset_password", methods=["POST"])
def reset_password():

    email = request.form.get('email')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')

    if not email or not new_password or not confirm_password:
        return "All fields are required "

    #  MAIN CHECK
    if new_password != confirm_password:
        return "Passwords do not match "

    import hashlib
    hashed = hashlib.sha256(new_password.encode()).hexdigest()

    cursor = db.cursor(buffered=True)
    cursor.execute(
        "UPDATE users SET password=%s WHERE email=%s",
        (hashed, email)
    )
    db.commit()
    cursor.close()

    return redirect("/login")

# ---------------- DASHBOARDS ----------------
@app.route("/admin")
@role_required("admin")
def admin_dashboard():
    cursor = db.cursor()
    company_id = session.get("company_id")

    cursor.execute("SELECT * FROM company WHERE id=%s", (session.get("company_id"),))
    company = cursor.fetchone()

    cursor.execute("SELECT * FROM task WHERE company_id=%s", (company_id,))
    tasks = cursor.fetchall()

    cursor.execute("SELECT COUNT(*) FROM task WHERE status='Pending' AND company_id=%s", (company_id,))
    pending = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM task WHERE status='In Progress' AND company_id=%s", (company_id,))
    progress = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM task WHERE status='Completed' AND company_id=%s", (company_id,))
    completed = cursor.fetchone()[0]

    cursor.execute("""SELECT id, username, email, role FROM users WHERE company_id=%s""", (company_id,))
    users = cursor.fetchall()



    cursor.execute("SELECT * FROM projects WHERE company_id=%s",(company_id,))
    projects = cursor.fetchall()

    cursor.execute("SELECT COUNT(*) FROM projects WHERE status='Pending' AND company_id=%s", (company_id,))
    p_pending = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM projects WHERE status='In Progress' AND company_id=%s", (company_id,))
    p_progress = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM projects WHERE status='Completed' AND company_id=%s", (company_id,))
    p_completed = cursor.fetchone()[0]

    cursor.execute("SELECT * FROM feedback ORDER BY date DESC") 
    feedbacks = cursor.fetchall() 

    cursor.execute("""
        SELECT a.status, COUNT(*) 
        FROM attendance a
        JOIN users u ON a.user_email = u.email
        WHERE u.company_id=%s
        GROUP BY a.status
    """, (company_id,))
    attendance_data = cursor.fetchall()

   # convert for chart
     # ✅ IMPORTANT FIX
    labels = []
    values = []

    for row in attendance_data:
        labels.append(row[0])
        values.append(row[1])

        # Get only numeric ratings
    ratings = [f[4] for f in feedbacks if isinstance(f[4], int) or isinstance(f[4], float)]
    avg_rating = round(sum(ratings)/len(ratings), 1) if ratings else 0


    
    return render_template("admin_dashboard.html",company=company, tasks=tasks, users=users,
    projects=projects, 
    feedbacks=feedbacks,
    avg_rating=avg_rating,
    pending=pending,
    progress=progress,
    completed=completed,
    p_pending=p_pending,
    p_progress=p_progress,
    p_completed=p_completed,
    attendance=attendance_data,
    labels=labels,      # ✅ must pass
    values=values
    
    )

@app.route("/manager")
@role_required("manager")
def manager_dashboard():

    cursor = db.cursor(buffered=True)
    company_id = session.get("company_id")

    cursor.execute("SELECT * FROM company WHERE id=%s", (session.get("company_id"),))
    company = cursor.fetchone()


    cursor.execute("SELECT * FROM task WHERE company_id=%s", (session.get("company_id"),))
    tasks = cursor.fetchall()

    # Counts
    cursor.execute("SELECT COUNT(*) FROM task WHERE status='Pending'")
    pending = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM task WHERE status='In Progress'")
    progress = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM task WHERE status='Completed'")
    completed = cursor.fetchone()[0]

    cursor.execute("""SELECT * FROM projects WHERE company_id=%s""", (session.get("company_id"),))
    projects = cursor.fetchall()


    cursor.execute("SELECT COUNT(*) FROM projects WHERE status='Pending'")
    p_pending = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM projects WHERE status='In Progress'")
    p_progress = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM projects WHERE status='Completed'")
    p_completed = cursor.fetchone()[0]

    cursor.close()

    return render_template(
    "manager_dashboard.html",
    tasks=tasks,
    company=company,
    projects=projects,
    pending=pending,
    progress=progress,
    completed=completed,
    p_pending=p_pending,
    p_progress=p_progress,
    p_completed=p_completed
)

@app.route("/employee")
@role_required("employee")
def employee():
    

    cursor = db.cursor()
    user = session.get("user")
    company_id = session.get("company_id")    

    cursor.execute("SELECT * FROM company WHERE id=%s", (session.get("company_id"),))
    company = cursor.fetchone()
    
       # ---------------- TASKS ----------------
    cursor.execute("""
    SELECT * FROM task 
    WHERE assigned_to=%s AND company_id=%s
    """, (user, company_id))
    tasks = cursor.fetchall()
    
    cursor.execute("""
    SELECT COUNT(*) 
    FROM task 
    WHERE assigned_to=%s AND company_id=%s
    """, (user, company_id))
    task_count = cursor.fetchone()[0]  

    # ✅ TASK STATUS COUNTS

    cursor.execute("""
    SELECT COUNT(*) FROM task 
    WHERE assigned_to=%s AND company_id=%s AND status='Pending'
    """, (user, company_id))
    pending_tasks = cursor.fetchone()[0]

    cursor.execute("""
    SELECT COUNT(*) FROM task 
    WHERE assigned_to=%s AND company_id=%s AND status='In Progress'
    """, (user, company_id))
    progress_tasks = cursor.fetchone()[0]

    cursor.execute("""
    SELECT COUNT(*) FROM task 
    WHERE assigned_to=%s AND company_id=%s AND status='Completed'
    """, (user, company_id))
    completed_tasks = cursor.fetchone()[0]  

    # ---------------- PROJECTS ----------------
    cursor.execute("""
    SELECT * FROM projects 
    WHERE assigned_to=%s AND company_id=%s
    """, (user, company_id))
    projects = cursor.fetchall() 

    cursor.execute("""
    SELECT COUNT(*) 
    FROM projects 
    WHERE assigned_to=%s AND company_id=%s
    """, (user, company_id))
    project_count = cursor.fetchone()[0]

    # ✅ PROJECT STATUS COUNTS

    cursor.execute("""
    SELECT COUNT(*) FROM projects 
    WHERE assigned_to=%s AND company_id=%s AND status='Pending'
    """, (user, company_id))
    pending_projects = cursor.fetchone()[0]

    cursor.execute("""
    SELECT COUNT(*) FROM projects 
    WHERE assigned_to=%s AND company_id=%s AND status='In Progress'
    """, (user, company_id))
    progress_projects = cursor.fetchone()[0]

    cursor.execute("""
    SELECT COUNT(*) FROM projects 
    WHERE assigned_to=%s AND company_id=%s AND status='Completed'
    """, (user, company_id))
    completed_projects = cursor.fetchone()[0]

    # attendance percentage
    cursor.execute("SELECT COUNT(*) FROM attendance WHERE user_email=%s", (user,))
    total_days = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM attendance WHERE user_email=%s AND status='Present'", (user,))
    present_days = cursor.fetchone()[0]

    if total_days > 0:
     percentage = (present_days / total_days) * 100
    else:
     percentage = 0

    # ---------------- ATTENDANCE ----------------
    cursor.execute("""
SELECT * FROM attendance 
WHERE user_email=%s AND company_id=%s
""", (session.get("user"), session.get("company_id")))
    attendance = cursor.fetchall()


    cursor.close()

    # ---------------- EVENTS FOR CALENDAR ----------------
    events = []

    # ✅ TASK EVENTS
    for t in tasks:
        try:
            if t[5]:   # deadline exists
                events.append({
                    "title": t[1],
                    "start": str(t[5]),
                    "color": "blue"
                })
        except:
            pass

    # ✅ ATTENDANCE EVENTS
    for a in attendance:
        try:
            if a[0]:   # date exists

                if a[1] == "Present":
                    color = "green"
                elif a[1] == "Absent":
                    color = "red"
                else:
                    color = "orange"

                events.append({
                    "title": a[1],
                    "start": a[0].strftime('%Y-%m-%d'),
                    "color": color,
                    "allDay":True

                })
        except:
            pass
        
    

    from datetime import date

    return render_template(
        "employee_dashboard.html",
        tasks=tasks,
        projects=projects,
        company=company,
        attendance=attendance,
        events=events,
        task_count=task_count,        
        project_count=project_count,
        pending_tasks=pending_tasks,
        progress_tasks=progress_tasks,
        completed_tasks=completed_tasks,

        pending_projects=pending_projects,
        progress_projects=progress_projects,
        completed_projects=completed_projects,
        current_date=date.today(),   # 👉 required for calendar
        percentage=round(percentage,2)
        
    )       

# Add Employee
# ----------------------------
@app.route("/add_employee", methods=["POST"])
def add_employee():
    if session.get("role") != "manager":
        return "Access Denied "

    username = request.form["username"]
    email = request.form["email"]
    password = request.form["password"]
    company_id = session.get("company_id")  

    import hashlib
    hashed_password = hashlib.sha256(password.encode()).hexdigest()

    cursor = db.cursor()
    cursor.execute("""
        INSERT INTO users (username, email, password, role, company_id)
        VALUES (%s, %s, %s, 'employee', %s)
    """, (username, email, hashed_password, company_id))
    db.commit()
    cursor.close()

    return redirect(url_for("manager_dashboard"))

@app.route("/update_task_ajax", methods=["POST"])
def update_task_ajax():

    data = request.get_json()

    cursor = db.cursor()

    cursor.execute(
        "UPDATE task SET status=%s WHERE id=%s",
        (data['status'], data['id'])
    )

    db.commit()
    cursor.close()

    return {"message":"success"}


@app.route("/customer")
def customer_dashboard():

    if session.get("role") != "customer":
        return "Access Denied ❌"

    company_id = session.get("company_id")

    cursor = db.cursor()

    # ✅ projects (company wise)
    cursor.execute("""
        SELECT id, name, description, status, deadline
        FROM projects
        WHERE company_id=%s
    """, (company_id,))
    projects = cursor.fetchall()

    # ✅ company details fetch
    cursor.execute("""
        SELECT * FROM company WHERE id=%s
    """, (company_id,))
    company = cursor.fetchone()

    cursor.close()

    return render_template(
        "customer_dashboard.html",
        projects=projects,
        company=company   # 🔥 IMPORTANT
    )

@app.route("/attendance")
def attendance():

    if session.get("role") not in ["admin", "manager"]:
        return "Access Denied ❌"
   
    if "company_id" not in session:
        return redirect("/login")

    cursor = db.cursor()
    company_id = session.get("company_id")

    # ✅ Attendance (only same company)
    cursor.execute("""
        SELECT id, user_email, date, status 
        FROM attendance 
        WHERE company_id=%s
        ORDER BY date DESC
    """, (company_id,))
    records = cursor.fetchall()

    # ✅ Employees (only same company)
    cursor.execute("""
        SELECT email 
        FROM users 
        WHERE role='employee' AND company_id=%s
    """, (company_id,))
    employees = cursor.fetchall()

    employee_list = [emp[0] for emp in employees]

    cursor.close()

    return render_template(
        "attendance.html",
        records=records,
        employees=employees
    )

@app.route("/mark_attendance", methods=["POST"])
def mark_attendance():

    if "company_id" not in session:
        return redirect("/login")

    email = request.form.get("user_email")
    name = request.form.get("employee_name")
    date = request.form.get("date")
    status = request.form.get("status")
    company_id = session.get("company_id")   # ✅ ADD THIS


    cursor = db.cursor()

    # 🔥 check with company_id also
    cursor.execute(
        "SELECT * FROM attendance WHERE user_email=%s AND date=%s AND company_id=%s",
        (email, date, company_id)
    )
    existing = cursor.fetchone()

    if existing:
        cursor.execute(
            """UPDATE attendance 
               SET employee_name=%s, status=%s 
               WHERE user_email=%s AND date=%s AND company_id=%s""",
            (name, status, email, date, company_id)
        )
        msg = "Attendance Updated ✅"
    else:
        cursor.execute(
            """INSERT INTO attendance 
               (user_email, employee_name, date, status, company_id) 
               VALUES (%s,%s,%s,%s,%s)""",
            (email, name, date, status, company_id)
        )
        msg = "Attendance Added ✅"

    db.commit()
    cursor.close()

    flash(msg)
    return redirect("/manage_attendance")

@app.route("/delete_attendance/<int:attendance_id>", methods=["POST"]) 
def delete_attendance(attendance_id): 
    cursor = db.cursor() 
    cursor.execute("DELETE FROM attendance WHERE id=%s",(attendance_id,)) 
    db.commit() 
    return redirect("/manage_attendance")

@app.route('/monthly_report')
def monthly_report():

    cursor = db.cursor()

    cursor.execute("""
        SELECT user_email,
        SUM(CASE WHEN status='Present' THEN 1 ELSE 0 END) as present,
        SUM(CASE WHEN status='Absent' THEN 1 ELSE 0 END) as absent
        FROM attendance
        WHERE MONTH(date)=MONTH(CURDATE())
        GROUP BY user_email
    """)

    data = cursor.fetchall()
    cursor.close()

    return render_template("monthly_report.html", data=data)

@app.route('/admin_analytics')
def admin_analytics():
    if "company_id" not in session:
        return redirect("/login")

    company_id = session.get("company_id")
    cursor = db.cursor(dictionary=True) # dictionary=True se data handle karna easy ho jata hai

    # 1. Total Users (Overall)
    cursor.execute("SELECT COUNT(*) as count FROM users WHERE company_id=%s", (company_id,))
    users = cursor.fetchone()['count']

    # 2. Total Employees Count
    cursor.execute("SELECT COUNT(*) as count FROM users WHERE company_id=%s AND role='Employee'", (company_id,))
    total_employees = cursor.fetchone()['count']

    # 3. Total Managers Count
    cursor.execute("SELECT COUNT(*) as count FROM users WHERE company_id=%s AND role='Manager'", (company_id,))
    total_managers = cursor.fetchone()['count']

    # 4. Total Tasks
    cursor.execute("SELECT COUNT(*) as count FROM task WHERE company_id=%s", (company_id,))
    tasks = cursor.fetchone()['count']

    # 5. Total Projects
    cursor.execute("SELECT COUNT(*) as count FROM projects WHERE company_id=%s", (company_id,))
    projects = cursor.fetchone()['count']

    # 6. Employee Wise Task & Project Status (For the Table)
    # Ye query har employee ke liye count nikaalegi
    cursor.execute("""
        SELECT 
            u.username,
            SUM(CASE WHEN t.status = 'Pending' THEN 1 ELSE 0 END) as t_pending,
            SUM(CASE WHEN t.status = 'In Progress' THEN 1 ELSE 0 END) as t_progress,
            SUM(CASE WHEN t.status = 'Completed' THEN 1 ELSE 0 END) as t_completed,
            SUM(CASE WHEN p.status = 'Pending' THEN 1 ELSE 0 END) as p_pending,
            SUM(CASE WHEN p.status = 'In Progress' THEN 1 ELSE 0 END) as p_progress,
            SUM(CASE WHEN p.status = 'Completed' THEN 1 ELSE 0 END) as p_completed
        FROM users u
        LEFT JOIN task t ON u.email = t.assigned_to
        LEFT JOIN projects p ON u.email = p.assigned_to
        WHERE u.company_id = %s AND u.role = 'Employee'
        GROUP BY u.id, u.username
    """, (company_id,))
    employee_stats = cursor.fetchall()

    # 7. Attendance Stats
    cursor.execute("""
        SELECT status, COUNT(*) as count 
        FROM attendance 
        WHERE company_id=%s
        GROUP BY status
    """, (company_id,))
    attendance = cursor.fetchall()

    cursor.close()

    return render_template(
        "admin_analytics.html",
        users=users,
        total_employees=total_employees,
        total_managers=total_managers,
        tasks=tasks,
        projects=projects,
        employee_stats=employee_stats,
        attendance=attendance
    )

# ---------------- TASK ----------------
@app.route("/create_task", methods=["GET", "POST"])
@role_required("admin", "manager")
def create_task():
    cursor = db.cursor()
    import os

    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static/uploads')
    if not os.path.exists(UPLOAD_FOLDER):
     os.makedirs(UPLOAD_FOLDER)
    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

    cursor.execute("SELECT username, email FROM users WHERE role='employee' AND company_id=%s",
                   (session.get("company_id"),))
    employees = cursor.fetchall()  # returns list of tuples [(username, email), ...]
    cursor.close()

    if request.method == "POST":
        title = request.form['title']
        description = request.form['description']
        assigned_to = request.form['assigned_to']
        deadline = request.form['deadline']

        document = request.files.get('document')
        doc_filename = None
        if document and document.filename != '':
            from werkzeug.utils import secure_filename
            doc_filename = secure_filename(document.filename)
            document.save(os.path.join(app.config['UPLOAD_FOLDER'], doc_filename))

        cursor = db.cursor()
        cursor.execute(
    "INSERT INTO task (title,description,status,assigned_to,deadline,document,company_id) VALUES (%s,%s,%s,%s,%s,%s,%s)",
    (title, description, "Pending",assigned_to,deadline,doc_filename, session.get("company_id"))
)
        db.commit()
        cursor.close()

        return redirect("/admin")

    return render_template("create_task.html",employees=employees)

@app.route("/manager_create_task", methods=["GET", "POST"])
def manager_create_task():

    import os
    import time

    cursor = db.cursor(buffered=True)

    # ✅ Fetch only same company employees
    cursor.execute("""
        SELECT username, email 
        FROM users 
        WHERE role='employee' AND company_id=%s
    """, (session.get("company_id"),))
    
    employees = cursor.fetchall()

    if request.method == "POST":

        title = request.form['title']
        description = request.form['description']
        assigned_to = request.form['assigned_to']
        deadline = request.form['deadline']

        # 📄 FILE HANDLE
        document = request.files.get("document")
        doc_name = None

        if document and document.filename != "":
            upload_path = "static/documents"

            if not os.path.exists(upload_path):
                os.makedirs(upload_path)

            # 🔥 unique filename
            doc_name = str(int(time.time())) + "_" + document.filename
            document.save(os.path.join(upload_path, doc_name))

        # ✅ INSERT QUERY
        cursor.execute("""
        INSERT INTO task(title, description, status, assigned_to, deadline, company_id, document) 
        VALUES(%s,%s,%s,%s,%s,%s,%s)
        """,
        (title, description, "Pending", assigned_to, deadline, session.get("company_id"), doc_name)
        )

        db.commit()
        cursor.close()

        return redirect("/manager")

    cursor.close()
    return render_template("manager_create_task.html", employees=employees)

@app.route("/view_tasks")
def view_tasks():

    cursor = db.cursor(buffered=True)

    role = session.get("role")
    user = session.get("user")
    company_id = session.get("company_id")

    if role == "employee":
        # ✅ Employee → sirf apne + same company + completed hide
        cursor.execute("""
            SELECT * FROM task 
            WHERE assigned_to=%s 
            AND company_id=%s
            AND status != 'Completed'
        """, (user, company_id))

    else:
        # ✅ Admin / Manager → sirf apni company ke tasks
        cursor.execute("""
            SELECT * FROM task 
            WHERE company_id=%s
        """, (company_id,))

    tasks = cursor.fetchall()
    cursor.close()

    from datetime import date

    return render_template("view_tasks.html", tasks=tasks, role=role, now=date.today)

@app.route("/task_list")
def task_list():

    cursor = db.cursor()

    role = session.get("role")
    user = session.get("user")
    company_id = session.get("company_id")

    if role == "employee":
        # ✅ Employee → sirf apna + same company + completed hide
        cursor.execute("""
            SELECT * FROM task 
            WHERE assigned_to=%s 
            AND company_id=%s
            AND status != 'Completed'
        """, (user, company_id))

    else:
        # ✅ Admin/Manager → sirf apni company ke tasks
        cursor.execute("""
            SELECT * FROM task 
            WHERE company_id=%s
        """, (company_id,))

    tasks = cursor.fetchall()
    cursor.close()

    return render_template("task_list.html", tasks=tasks)

@app.route("/delete_task/<int:task_id>")
def delete_task(task_id):

    cursor = db.cursor()

    cursor.execute("""
        DELETE FROM task 
        WHERE id=%s AND company_id=%s
    """, (task_id, session['company_id']))

    db.commit()
    cursor.close()

    return redirect("/view_tasks")

@app.route("/update_task/<int:id>", methods=["GET", "POST"])
def update_task(id):

    cursor = db.cursor()

    if request.method == "POST":
        status = request.form['status']   # ✅ पहले status लो

        cursor.execute(
            "UPDATE task SET status=%s WHERE id=%s",
            (status, id)
        )
        db.commit()

    
        log_action(session['user'], f"Updated task {id} status to {status}")

        return redirect("/view_tasks")

    cursor.execute("SELECT * FROM task WHERE id=%s", (id,))
    task = cursor.fetchone()

    return render_template("update_status.html", task=task)


@app.route("/add_project", methods=["POST"])
def add_project():
    name = request.form['project_name']
    description = request.form['description']
    assigned_to = request.form['assigned_to'] 
    deadline = request.form['deadline'] 

    from werkzeug.utils import secure_filename
    import os
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static/uploads')
    if not os.path.exists(UPLOAD_FOLDER):
     os.makedirs(UPLOAD_FOLDER)

    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
    document = request.files.get('document') 
    doc_filename = None
    if document and document.filename != '':
        doc_filename = secure_filename(document.filename)
        document.save(os.path.join(app.config['UPLOAD_FOLDER'], doc_filename))

    cursor = db.cursor(buffered=True)
    cursor.execute(
        "INSERT INTO projects (name, description, assigned_to, deadline, status, document, company_id) VALUES (%s,%s,%s,%s,%s,%s,%s)",
        (name, description, assigned_to, deadline, "Active", doc_filename, session.get("company_id"))
    )
    db.commit()
    cursor.close()

    return redirect("/projects")

# ---------------- PROJECT ----------------
@app.route("/create_project", methods=["GET", "POST"])
def create_project():

    cursor = db.cursor()

    cursor.execute("""
SELECT username,email 
FROM users 
WHERE role='employee' AND company_id=%s
""", (session.get("company_id"),))
    employees = cursor.fetchall()

    if request.method == "POST":
        name = request.form['name']
        desc = request.form['description']
        assigned_to = request.form['assigned_to']
        deadline = request.form['deadline']

    
         
        cursor.execute(
    "INSERT INTO projects (name,description,assigned_to,deadline,status,company_id) VALUES (%s,%s,%s,%s,%s,%s)",
    (name, desc, assigned_to, deadline, "Active", session.get("company_id"))
)
        db.commit()
        cursor.close()

        return redirect("/manager")

    cursor.close()
    return render_template("create_project.html", employees=employees)
from flask import session

# ---------------- PROJECT LIST ----------------
@app.route("/projects")
def projects():

    cursor = db.cursor()

    role = session.get("role")
    user = session.get("user")

    active_projects = []
    completed_projects = []

    if role == "employee":
        cursor.execute("SELECT * FROM projects WHERE assigned_to=%s", (user,))
        active_projects = cursor.fetchall()
        cursor.execute("""SELECT * FROM projects WHERE assigned_to=%s AND status!='Completed'""", (user,))
        active_projects = cursor.fetchall()
        
    else:
        cursor.execute("SELECT * FROM projects WHERE company_id=%s", (session.get("company_id"),))
        active_projects = cursor.fetchall()

        cursor.execute("""SELECT * FROM projects WHERE company_id=%s AND status='Completed'""", (session.get("company_id"),))
        completed_projects = cursor.fetchall()

    data = cursor.fetchall()
    cursor.close()

    return render_template("project_list.html", projects=active_projects,completed_projects=completed_projects,role=role)

@app.route("/view_projects")
def view_projects():

    cursor = db.cursor()

    role = session.get("role")
    user = session.get("user")

    active_projects = []
    completed_projects = []

    if role == "employee":
        cursor.execute("SELECT * FROM projects WHERE assigned_to=%s", (user,))
        active_projects = cursor.fetchall()
        cursor.execute("""SELECT * FROM projects WHERE assigned_to=%s AND status!='Completed'""", (user,))
        active_projects = cursor.fetchall()
        
    else:
        cursor.execute("SELECT * FROM projects WHERE company_id=%s", (session.get("company_id"),))
        active_projects = cursor.fetchall()

        cursor.execute("""SELECT * FROM projects WHERE company_id=%s AND status='Completed'""", (session.get("company_id"),))
        completed_projects = cursor.fetchall()

    data = cursor.fetchall()
    cursor.close()

    return render_template("project_list.html", projects=active_projects,completed_projects=completed_projects,)


# ---------------- PROJECT LIST WITH ROLE ----------------
@app.route("/project_list")
@role_required("admin", "manager")
def project_list():
    cursor = db.cursor(buffered=True)
    cursor.execute("""
    SELECT 
        p.id,
        p.name,
        p.description,
        p.status,
        u.username,
        p.deadline,
        p.document
    FROM projects p
    LEFT JOIN users u ON p.assigned_to = u.email
    WHERE p.company_id=%s
""", (session.get("company_id"),))
    
    projects = cursor.fetchall()
    cursor.close()

    role = session.get("role")

    return render_template("project_list.html", projects=projects, role=role)


@app.route("/delete_project/<int:id>")
@role_required("admin", "manager")
def delete_project(id):
    cursor = db.cursor()
    cursor.execute("DELETE FROM projects WHERE id=%s AND company_id=%s", (id, session.get("company_id")))
    db.commit()
    cursor.close()

    return redirect("/project_list")



from werkzeug.utils import secure_filename
import os

@app.route("/manager_create_project", methods=["GET", "POST"])
def manager_create_project():

    cursor = db.cursor(buffered=True)

    cursor.execute("""
    SELECT username,email 
    FROM users 
    WHERE role='employee' AND company_id=%s
    """, (session.get("company_id"),))
    employees = cursor.fetchall()

    if request.method == "POST":

        name = request.form['name']
        description = request.form['description']
        assigned_to = request.form['assigned_to']
        deadline = request.form['deadline']

        # 🔥 DOCUMENT UPLOAD
        file = request.files.get('document')
        filename = None

        if file and file.filename != "":
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        # INSERT WITH DOCUMENT
        cursor.execute("""
        INSERT INTO projects 
        (name, description, status, assigned_to, deadline, company_id, document) 
        VALUES (%s,%s,%s,%s,%s,%s,%s)
        """,
        (name, description, "Active", assigned_to, deadline, session.get("company_id"), filename)
        )

        db.commit()
        cursor.close()

        return redirect("/manager")

    return render_template("manager_create_project.html", employees=employees)

# ---------------- SUBMIT FEEDBACK ----------------
@app.route("/submit_feedback", methods=["POST"])
def submit_feedback():
    customer_name = request.form.get('customer_name')
    email = request.form.get('email')
    message = request.form.get('message')
    rating = request.form.get('rating') # Agar rating field bhi hai toh

    try:
        cursor = db.cursor(buffered=True)
        # Table structure ke hisaab se query (agar rating column hai toh add kar dein)
        query = "INSERT INTO feedback (customer_name, email, message, rating) VALUES (%s, %s, %s, %s)"
        cursor.execute(query, (customer_name, email, message, rating))
        db.commit()
        cursor.close()

        # Success message flash karein
        flash("Thank you! Your feedback has been submitted successfully. ✅", "success")
    
    except Exception as e:
        flash("Thank you for a feedback.", "danger")

    return redirect("/customer") # Wapas dashboard par bhej deine bej fee

@app.route("/delete_feedback/<int:feedback_id>")
def delete_feedback(feedback_id):
    cursor = db.cursor()
    cursor.execute("DELETE FROM feedback WHERE id=%s", (feedback_id,))
    db.commit()
    cursor.close()
    return redirect("/admin")  # wapas admin dashboard pe


# ---------------- ADMIN FEEDBACK ----------------
@app.route("/admin_feedback")
def admin_feedback():

    cursor = db.cursor(buffered=True)
    cursor.execute("SELECT * FROM feedback ORDER BY date DESC")

    feedbacks = cursor.fetchall()
    cursor.close()

    return render_template("admin_feedback.html", feedbacks=feedbacks)

@app.route("/get_stats")
def get_stats():

    cursor = db.cursor()
    company_id = session.get("company_id")


    # TASK
    cursor.execute("SELECT COUNT(*) FROM task WHERE company_id=%s AND status='Pending'", (company_id,))
    pending = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM task WHERE company_id=%s AND status='In Progress'",(company_id,))
    progress = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM task WHERE company_id=%s ANDvstatus='Completed'",(company_id,))
    completed_task = cursor.fetchone()[0]

    # PROJECT
    cursor.execute("SELECT COUNT(*) FROM projects WHERE company_id=%s AND status='Pending'",(company_id,))
    p_pending = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM projects WHERE company_id=%s AND status='In Progress'",(company_id,))
    p_progress = cursor.fetchone()[0]

    
    cursor.execute("SELECT COUNT(*) FROM projects WHERE company_id=%s AND status='Completed'", (company_id,))
    completed_project = cursor.fetchone()[0]

    cursor.close()

    return {
        "task": [pending, progress, completed_task],
        "project": [p_pending, p_progress, completed_project],
        "counts": {
            "pending": pending,
            "completed": completed_task
        }
    }

@app.route("/manage_attendance")
def manage_attendance():

    page = request.args.get('page', 1, type=int)
    per_page = 10
    offset = (page - 1) * per_page

    company_id = session.get("company_id")

    cursor = db.cursor()

    # total records
    cursor.execute("""SELECT COUNT(*) FROM attendance WHERE company_id=%s""", (company_id,))
    total = cursor.fetchone()[0]
    

    # paginated data
    cursor.execute("""SELECT * FROM attendance WHERE company_id=%s ORDER BY date DESC LIMIT %s OFFSET %s""", (company_id, per_page, offset))
    data = cursor.fetchall()
    cursor.close()

    total_pages = (total + per_page - 1) // per_page

    return render_template(
        "manage_attendance.html",
        data=data,
        page=page,
        total_pages=total_pages
    )

from flask import redirect, url_for, flash

@app.route("/update_attendance/<int:id>", methods=["POST"])
def update_attendance(id):

    email = request.form.get("email")
    name = request.form.get("employee_name")
    date = request.form.get("date")
    status = request.form.get("status")

    cursor = db.cursor()

    cursor.execute("""
        UPDATE attendance 
        SET user_email=%s, employee_name=%s, date=%s, status=%s 
        WHERE id=%s
    """, (email, name, date, status, id))

    db.commit()
    cursor.close()

    flash("Attendance Updated Successfully ✅")

    return redirect("/manage_attendance")

@app.route("/calendar")
def calendar_view():
    events = [
        {"title": "Project Deadline", "start": "2026-03-30"},
        {"title": "Meeting", "start": "2026-04-02"}
    ]
    return render_template("calendar.html", events=events)

@app.route("/complete_project/<int:id>",methods=["POST"])
def complete_project(id):

    report = request.form['report']
    document = request.files.get('document')

    from werkzeug.utils import secure_filename
    import os

    doc_filename = None

    if document and document.filename != "":
        doc_filename = secure_filename(document.filename)
        document.save(os.path.join(app.config['UPLOAD_FOLDER'], doc_filename))
                      
    cursor = db.cursor()
    cursor.execute("UPDATE projects SET status=%s,report=%s,submitted_file=%s WHERE id=%s", ("Completed",report,doc_filename, id))
    db.commit()
    cursor.close()
    return redirect("/projects")


@app.route("/complete_task/<int:task_id>", methods=["POST"])
def complete_task(task_id):

    if session.get("role") != "employee":
        return "Access Denied "

    report = request.form.get("report")
    document = request.files.get("document")

    from werkzeug.utils import secure_filename
    import os

    filename = None

    if document and document.filename != "":
        filename = secure_filename(document.filename)
        document.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

    cursor = db.cursor()

    cursor.execute("""
        UPDATE task 
        SET status=%s, report=%s, submitted_file=%s 
        WHERE id=%s
    """, ("Completed", report, filename, task_id))

    db.commit()
    cursor.close()

    return redirect("/view_tasks")

@app.route("/add_requirement", methods=["GET", "POST"])
def add_requirement():

    if session.get("role") != "customer":
        return "Access Denied ❌"

    if request.method == "POST":

        title = request.form['title']
        description = request.form['description']
        email = session.get("user")
        company_id = session.get("company_id")

        cursor = db.cursor()

        cursor.execute("""
            INSERT INTO requirements (customer_email, title, description, company_id)
            VALUES (%s,%s,%s,%s)
        """, (email, title, description, company_id))

        db.commit()
        cursor.close()

        return redirect("/customer")

    return render_template("add_requirement.html")

@app.route("/view_requirements")
def view_requirements():

    if session.get("role") not in ["admin", "manager"]:
        return "Access Denied ❌"

    cursor = db.cursor()

    cursor.execute("""
        SELECT * FROM requirements
        WHERE company_id=%s
        ORDER BY id DESC
    """, (session.get("company_id"),))

    data = cursor.fetchall()
    cursor.close()

    return render_template("view_requirements.html", data=data)



# ---------------- MAIN ----------------
if __name__ == "__main__":
    app.run(debug=True)