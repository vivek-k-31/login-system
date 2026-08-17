import os
from functools import wraps

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    jsonify,
    flash
)

from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)

from werkzeug.utils import secure_filename

import mysql.connector
from dotenv import load_dotenv


# =========================================================
# LOAD ENVIRONMENT
# =========================================================

load_dotenv()


# =========================================================
# FLASK APP
# =========================================================

app = Flask(__name__)

app.secret_key = os.getenv(
    "SECRET_KEY",
    "change-this-secret-key"
)


# =========================================================
# DATABASE CONFIG
# =========================================================

DB = {
    "host": os.getenv(
        "DB_HOST",
        "127.0.0.1"
    ),

    "port": int(
        os.getenv(
            "DB_PORT",
            "3306"
        )
    ),

    "database": os.getenv(
        "DB_NAME",
        "kjc_portal"
    ),

    "user": os.getenv(
        "DB_USER",
        "root"
    ),

    "password": os.getenv(
        "DB_PASSWORD",
        ""
    )
}


# =========================================================
# UPLOAD CONFIG
# =========================================================

UPLOAD_FOLDER = os.path.join(
    app.static_folder,
    "uploads"
)

os.makedirs(
    UPLOAD_FOLDER,
    exist_ok=True
)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

ALLOWED_IMAGE_EXTENSIONS = {
    "png",
    "jpg",
    "jpeg",
    "webp",
    "gif",
    "svg"
}


# =========================================================
# DATABASE CONNECTION
# =========================================================

def db():

    return mysql.connector.connect(
        **DB
    )


# =========================================================
# FETCH DATABASE
# =========================================================

def fetch(sql, p=(), one=False):

    connection = None
    cursor = None

    try:

        connection = db()

        cursor = connection.cursor(
            dictionary=True
        )

        cursor.execute(
            sql,
            p
        )

        rows = cursor.fetchall()

        if one:

            return (
                rows[0]
                if rows
                else None
            )

        return rows

    finally:

        if cursor:
            cursor.close()

        if connection:
            connection.close()


# =========================================================
# EXECUTE DATABASE
# =========================================================

def execute(sql, p=()):

    connection = None
    cursor = None

    try:

        connection = db()

        cursor = connection.cursor()

        cursor.execute(
            sql,
            p
        )

        connection.commit()

        return cursor.lastrowid

    finally:

        if cursor:
            cursor.close()

        if connection:
            connection.close()


# =========================================================
# EXECUTE MANY
# =========================================================

def execute_many(sql, data):

    connection = None
    cursor = None

    try:

        connection = db()

        cursor = connection.cursor()

        cursor.executemany(
            sql,
            data
        )

        connection.commit()

    finally:

        if cursor:
            cursor.close()

        if connection:
            connection.close()


# =========================================================
# SITE SETTINGS TABLE
# =========================================================

def create_admin_settings_table():

    connection = None
    cursor = None

    try:

        connection = db()

        cursor = connection.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS site_settings (

                id INT AUTO_INCREMENT PRIMARY KEY,

                setting_key VARCHAR(100)
                NOT NULL UNIQUE,

                setting_value TEXT NULL,

                updated_at TIMESTAMP
                DEFAULT CURRENT_TIMESTAMP
                ON UPDATE CURRENT_TIMESTAMP

            )
            """
        )

        connection.commit()

        default_settings = [

            (
                "site_title",
                "KJC | Campus Portal"
            ),

            (
                "hero_title",
                "Operate the campus."
            ),

            (
                "hero_subtitle",
                "Manage students, academics and workflows."
            ),

            (
                "hero_label",
                "ADMIN MODE"
            ),

            (
                "campus_image",
                "img/campus.svg"
            ),

            (
                "font_family",
                "Inter"
            )

        ]

        for key, value in default_settings:

            cursor.execute(
                """
                INSERT IGNORE INTO site_settings
                (
                    setting_key,
                    setting_value
                )
                VALUES
                (
                    %s,
                    %s
                )
                """,
                (
                    key,
                    value
                )
            )

        connection.commit()

        print(
            "Site settings table ready."
        )

    except Exception as e:

        print(
            "Site settings table error:",
            e
        )

    finally:

        if cursor:
            cursor.close()

        if connection:
            connection.close()


# =========================================================
# GET SETTING
# =========================================================

def get_setting(
    key,
    default=""
):

    try:

        row = fetch(
            """
            SELECT setting_value
            FROM site_settings
            WHERE setting_key=%s
            """,
            (key,),
            True
        )

        if row:

            return row[
                "setting_value"
            ]

    except Exception:

        pass

    return default


# =========================================================
# SET SETTING
# =========================================================

def set_setting(
    key,
    value
):

    execute(
        """
        INSERT INTO site_settings
        (
            setting_key,
            setting_value
        )
        VALUES
        (
            %s,
            %s
        )

        ON DUPLICATE KEY UPDATE

        setting_value=VALUES(
            setting_value
        )
        """,
        (
            key,
            value
        )
    )


# =========================================================
# GET ALL SETTINGS
# =========================================================

def get_all_settings():

    try:

        rows = fetch(
            """
            SELECT
                setting_key,
                setting_value
            FROM site_settings
            """
        )

        return {
            row["setting_key"]:
            row["setting_value"]
            for row in rows
        }

    except Exception:

        return {}


# =========================================================
# CURRENT USER
# =========================================================

def me():

    if "uid" not in session:

        return None

    return fetch(
        """
        SELECT
            id,
            name,
            email,
            role
        FROM users
        WHERE id=%s
        """,
        (
            session["uid"],
        ),
        True
    )


# =========================================================
# LOGIN REQUIRED
# =========================================================

def login_required(f):

    @wraps(f)
    def wrapper(*args, **kwargs):

        if not me():

            return redirect(
                url_for("login")
            )

        return f(
            *args,
            **kwargs
        )

    return wrapper


# =========================================================
# ADMIN REQUIRED
# =========================================================

def admin_required(f):

    @wraps(f)
    def wrapper(*args, **kwargs):

        user = me()

        if not user:

            return redirect(
                url_for("login")
            )

        if user["role"] != "ADMIN":

            return redirect(
                url_for("dashboard")
            )

        return f(
            *args,
            **kwargs
        )

    return wrapper


# =========================================================
# GLOBAL TEMPLATE DATA
# =========================================================

@app.context_processor
def inject():

    return {
        "current_user": me(),
        "site_settings": get_all_settings()
    }


# =========================================================
# HOME
# =========================================================

@app.route("/")
def home():

    return render_template(
        "index.html"
    )


# =========================================================
# LOGIN
# =========================================================

@app.route(
    "/login",
    methods=["GET", "POST"]
)
def login():

    if request.method == "POST":

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        password = request.form.get(
            "password",
            ""
        )

        if not email or not password:

            flash(
                "Please enter email and password.",
                "error"
            )

            return render_template(
                "login.html"
            )

        try:

            user = fetch(
                """
                SELECT *
                FROM users
                WHERE email=%s
                """,
                (
                    email,
                ),
                True
            )

        except Exception as e:

            print(
                "Login database error:",
                e
            )

            flash(
                "Database connection error.",
                "error"
            )

            return render_template(
                "login.html"
            )

        if user and check_password_hash(
            user["password_hash"],
            password
        ):

            session["uid"] = user["id"]

            try:

                execute(
                    """
                    INSERT INTO login_history
                    (
                        user_id,
                        ip_address
                    )
                    VALUES
                    (
                        %s,
                        %s
                    )
                    """,
                    (
                        user["id"],
                        request.remote_addr
                    )
                )

            except Exception as e:

                print(
                    "Login history error:",
                    e
                )

            if user["role"] == "ADMIN":

                return redirect(
                    url_for("admin")
                )

            return redirect(
                url_for("dashboard")
            )

        flash(
            "Invalid email or password.",
            "error"
        )

    return render_template(
        "login.html"
    )


# =========================================================
# REGISTER
# =========================================================

@app.route(
    "/register",
    methods=["GET", "POST"]
)
def register():

    if request.method == "POST":

        name = request.form.get(
            "name",
            ""
        ).strip()

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        student_id = request.form.get(
            "student_id",
            ""
        ).strip()

        course = request.form.get(
            "course",
            ""
        ).strip()

        semester = request.form.get(
            "semester",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        )

        if (
            not name
            or not email
            or not student_id
            or not course
            or not semester
            or len(password) < 6
        ):

            flash(
                "Complete all fields and use a 6+ character password.",
                "error"
            )

            return render_template(
                "register.html"
            )

        connection = None
        cursor = None

        try:

            connection = db()

            cursor = connection.cursor()

            cursor.execute(
                """
                INSERT INTO users
                (
                    name,
                    email,
                    password_hash,
                    role
                )
                VALUES
                (
                    %s,
                    %s,
                    %s,
                    'STUDENT'
                )
                """,
                (
                    name,
                    email,
                    generate_password_hash(
                        password
                    )
                )
            )

            uid = cursor.lastrowid

            cursor.execute(
                """
                INSERT INTO students
                (
                    user_id,
                    student_id,
                    course,
                    semester
                )
                VALUES
                (
                    %s,
                    %s,
                    %s,
                    %s
                )
                """,
                (
                    uid,
                    student_id,
                    course,
                    semester
                )
            )

            connection.commit()

            flash(
                "Account created successfully. Login now.",
                "success"
            )

            return redirect(
                url_for("login")
            )

        except mysql.connector.Error as e:

            print(
                "Registration error:",
                e
            )

            if connection:
                connection.rollback()

            flash(
                "Email or Student ID may already exist.",
                "error"
            )

        finally:

            if cursor:
                cursor.close()

            if connection:
                connection.close()

    return render_template(
        "register.html"
    )


# =========================================================
# LOGOUT
# =========================================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(
        url_for("home")
    )


# =========================================================
# STUDENT PROFILE
# =========================================================

def student():

    return fetch(
        """
        SELECT
            s.*,
            u.name,
            u.email
        FROM students s
        JOIN users u
            ON u.id=s.user_id
        WHERE s.user_id=%s
        """,
        (
            session["uid"],
        ),
        True
    )


# =========================================================
# STUDENT DASHBOARD
# =========================================================

@app.route("/dashboard")
@login_required
def dashboard():

    current = me()

    if current["role"] == "ADMIN":

        return redirect(
            url_for("admin")
        )

    s = student()

    if not s:

        session.clear()

        flash(
            "Student profile not found.",
            "error"
        )

        return redirect(
            url_for("login")
        )

    attendance = fetch(
        """
        SELECT
            *,
            ROUND(
                attended /
                NULLIF(total, 0) * 100,
                1
            ) AS pct
        FROM attendance
        WHERE student_id=%s
        """,
        (
            s["id"],
        )
    )

    marks = fetch(
        """
        SELECT
            *,
            internal +
            assignment +
            exam AS total
        FROM marks
        WHERE student_id=%s
        """,
        (
            s["id"],
        )
    )

    assignments = fetch(
        """
        SELECT *
        FROM assignments
        WHERE student_id=%s
        ORDER BY due_date
        """,
        (
            s["id"],
        )
    )

    timetable = fetch(
        """
        SELECT *
        FROM timetable
        WHERE course=%s
        AND semester=%s
        ORDER BY
            FIELD(
                day_name,
                'Monday',
                'Tuesday',
                'Wednesday',
                'Thursday',
                'Friday',
                'Saturday'
            ),
            period_time
        """,
        (
            s["course"],
            s["semester"]
        )
    )

    notifications = fetch(
        """
        SELECT *
        FROM notifications
        WHERE
            student_id IS NULL
            OR student_id=%s
        ORDER BY created_at DESC
        LIMIT 10
        """,
        (
            s["id"],
        )
    )

    leaves = fetch(
        """
        SELECT *
        FROM leave_requests
        WHERE student_id=%s
        ORDER BY created_at DESC
        """,
        (
            s["id"],
        )
    )

    fees = fetch(
        """
        SELECT
            *,
            amount - paid AS balance
        FROM fees
        WHERE student_id=%s
        ORDER BY due_date
        """,
        (
            s["id"],
        )
    )

    certificates = fetch(
        """
        SELECT *
        FROM certificates
        WHERE student_id=%s
        ORDER BY issued_on DESC
        """,
        (
            s["id"],
        )
    )

    total_classes = sum(
        x["total"] or 0
        for x in attendance
    )

    attended_classes = sum(
        x["attended"] or 0
        for x in attendance
    )

    att_pct = (
        round(
            attended_classes /
            total_classes *
            100,
            1
        )
        if total_classes
        else 0
    )

    avg = (
        round(
            sum(
                float(
                    x["total"] or 0
                )
                for x in marks
            ) / len(marks),
            1
        )
        if marks
        else 0
    )

    pending = sum(
        1
        for x in assignments
        if x["status"] == "Pending"
    )

    balance = sum(
        float(
            x["balance"] or 0
        )
        for x in fees
    )

    return render_template(
        "dashboard.html",
        s=s,
        attendance=attendance,
        marks=marks,
        assignments=assignments,
        timetable=timetable,
        notifications=notifications,
        leaves=leaves,
        fees=fees,
        certificates=certificates,
        att_pct=att_pct,
        avg=avg,
        pending=pending,
        balance=balance
    )


# =========================================================
# STUDENT PROFILE API
# =========================================================

@app.post("/api/profile")
@login_required
def profile():

    s = student()

    if not s:

        return jsonify(
            ok=False,
            message="Student profile not found."
        ), 404

    execute(
        """
        UPDATE students
        SET
            phone=%s,
            address=%s
        WHERE id=%s
        """,
        (
            request.form.get(
                "phone",
                ""
            ),

            request.form.get(
                "address",
                ""
            ),

            s["id"]
        )
    )

    return jsonify(
        ok=True,
        message="Profile saved."
    )


# =========================================================
# SUBMIT ASSIGNMENT
# =========================================================

@app.post(
    "/api/assignment/<int:aid>/submit"
)
@login_required
def submit_assignment(aid):

    s = student()

    if not s:

        return jsonify(
            ok=False,
            message="Student profile not found."
        ), 404

    execute(
        """
        UPDATE assignments
        SET
            status =
                CASE
                    WHEN due_date < CURDATE()
                    THEN 'Late'
                    ELSE 'Submitted'
                END,
            submitted_at=NOW()
        WHERE id=%s
        AND student_id=%s
        AND status='Pending'
        """,
        (
            aid,
            s["id"]
        )
    )

    return jsonify(
        ok=True,
        message="Assignment submitted."
    )


# =========================================================
# LEAVE REQUEST
# =========================================================

@app.post("/api/leave")
@login_required
def leave():

    s = student()

    if not s:

        return jsonify(
            ok=False,
            message="Student profile not found."
        ), 404

    frm = request.form.get(
        "from_date"
    )

    to = request.form.get(
        "to_date"
    )

    reason = request.form.get(
        "reason",
        ""
    ).strip()

    if not frm or not to or not reason:

        return jsonify(
            ok=False,
            message="Complete all fields."
        ), 400

    execute(
        """
        INSERT INTO leave_requests
        (
            student_id,
            from_date,
            to_date,
            reason
        )
        VALUES
        (
            %s,
            %s,
            %s,
            %s
        )
        """,
        (
            s["id"],
            frm,
            to,
            reason
        )
    )

    return jsonify(
        ok=True,
        message="Leave request submitted."
    )


# =========================================================
# ADMIN DASHBOARD
# =========================================================

@app.route("/admin")
@admin_required
def admin():

    students = fetch(
        """
        SELECT
            s.*,
            u.name,
            u.email
        FROM students s
        JOIN users u
            ON u.id=s.user_id
        ORDER BY u.name
        """
    )

    leaves = fetch(
        """
        SELECT
            l.*,
            u.name,
            s.student_id
        FROM leave_requests l
        JOIN students s
            ON s.id=l.student_id
        JOIN users u
            ON u.id=s.user_id
        ORDER BY l.created_at DESC
        """
    )

    attendance = fetch(
        """
        SELECT
            a.*,
            s.student_id,
            u.name
        FROM attendance a
        JOIN students s
            ON s.id=a.student_id
        JOIN users u
            ON u.id=s.user_id
        ORDER BY a.id DESC
        """
    )

    marks = fetch(
        """
        SELECT
            m.*,
            s.student_id,
            u.name
        FROM marks m
        JOIN students s
            ON s.id=m.student_id
        JOIN users u
            ON u.id=s.user_id
        ORDER BY m.id DESC
        """
    )

    assignments = fetch(
        """
        SELECT
            a.*,
            s.student_id,
            u.name
        FROM assignments a
        JOIN students s
            ON s.id=a.student_id
        JOIN users u
            ON u.id=s.user_id
        ORDER BY a.id DESC
        """
    )

    fees = fetch(
        """
        SELECT
            f.*,
            s.student_id,
            u.name
        FROM fees f
        JOIN students s
            ON s.id=f.student_id
        JOIN users u
            ON u.id=s.user_id
        ORDER BY f.id DESC
        """
    )

    notices = fetch(
        """
        SELECT
            n.*,
            u.name AS student_name
        FROM notifications n
        LEFT JOIN students s
            ON s.id=n.student_id
        LEFT JOIN users u
            ON u.id=s.user_id
        ORDER BY n.created_at DESC
        """
    )

    settings = get_all_settings()

    return render_template(
        "admin.html",
        students=students,
        leaves=leaves,
        attendance=attendance,
        marks=marks,
        assignments=assignments,
        fees=fees,
        notices=notices,
        settings=settings
    )


# =========================================================
# ADMIN - ADD STUDENT
# =========================================================

@app.post("/api/admin/student")
@admin_required
def add_student():

    connection = None
    cursor = None

    try:

        connection = db()

        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT INTO users
            (
                name,
                email,
                password_hash,
                role
            )
            VALUES
            (
                %s,
                %s,
                %s,
                'STUDENT'
            )
            """,
            (
                request.form["name"],
                request.form[
                    "email"
                ].strip().lower(),

                generate_password_hash(
                    request.form.get(
                        "password",
                        "student123"
                    )
                )
            )
        )

        uid = cursor.lastrowid

        cursor.execute(
            """
            INSERT INTO students
            (
                user_id,
                student_id,
                course,
                semester
            )
            VALUES
            (
                %s,
                %s,
                %s,
                %s
            )
            """,
            (
                uid,
                request.form[
                    "student_id"
                ],
                request.form[
                    "course"
                ],
                request.form[
                    "semester"
                ]
            )
        )

        connection.commit()

        return jsonify(
            ok=True,
            message="Student added successfully."
        )

    except mysql.connector.Error as e:

        print(
            "Add student error:",
            e
        )

        if connection:
            connection.rollback()

        return jsonify(
            ok=False,
            message="Could not add student. Check duplicate email or Student ID."
        ), 400

    finally:

        if cursor:
            cursor.close()

        if connection:
            connection.close()


# =========================================================
# ADMIN - EDIT STUDENT
# =========================================================

@app.post(
    "/api/admin/student/<int:sid>/edit"
)
@admin_required
def edit_student(sid):

    student_row = fetch(
        """
        SELECT user_id
        FROM students
        WHERE id=%s
        """,
        (
            sid,
        ),
        True
    )

    if not student_row:

        return jsonify(
            ok=False,
            message="Student not found."
        ), 404

    execute(
        """
        UPDATE students
        SET
            student_id=%s,
            course=%s,
            semester=%s
        WHERE id=%s
        """,
        (
            request.form.get(
                "student_id"
            ),

            request.form.get(
                "course"
            ),

            request.form.get(
                "semester"
            ),

            sid
        )
    )

    execute(
        """
        UPDATE users
        SET
            name=%s,
            email=%s
        WHERE id=%s
        """,
        (
            request.form.get(
                "name"
            ),

            request.form.get(
                "email"
            ).strip().lower(),

            student_row["user_id"]
        )
    )

    password = request.form.get(
        "password",
        ""
    ).strip()

    if password:

        execute(
            """
            UPDATE users
            SET password_hash=%s
            WHERE id=%s
            """,
            (
                generate_password_hash(
                    password
                ),

                student_row[
                    "user_id"
                ]
            )
        )

    return jsonify(
        ok=True,
        message="Student updated."
    )


# =========================================================
# ADMIN - DELETE STUDENT
# =========================================================

@app.post(
    "/api/admin/student/<int:sid>/delete"
)
@admin_required
def delete_student(sid):

    row = fetch(
        """
        SELECT user_id
        FROM students
        WHERE id=%s
        """,
        (
            sid,
        ),
        True
    )

    if not row:

        return jsonify(
            ok=False,
            message="Student not found."
        ), 404

    connection = None
    cursor = None

    try:

        connection = db()

        cursor = connection.cursor()

        tables = [
            "attendance",
            "marks",
            "assignments",
            "leave_requests",
            "fees",
            "notifications",
            "certificates"
        ]

        for table in tables:

            cursor.execute(
                f"""
                DELETE FROM {table}
                WHERE student_id=%s
                """,
                (
                    sid,
                )
            )

        cursor.execute(
            """
            DELETE FROM students
            WHERE id=%s
            """,
            (
                sid,
            )
        )

        cursor.execute(
            """
            DELETE FROM users
            WHERE id=%s
            """,
            (
                row["user_id"],
            )
        )

        connection.commit()

        return jsonify(
            ok=True,
            message="Student deleted completely."
        )

    except Exception as e:

        if connection:
            connection.rollback()

        print(
            "Delete student error:",
            e
        )

        return jsonify(
            ok=False,
            message=str(e)
        ), 400

    finally:

        if cursor:
            cursor.close()

        if connection:
            connection.close()


# =========================================================
# ADMIN - ATTENDANCE
# =========================================================

@app.post("/api/admin/attendance")
@admin_required
def add_attendance():

    execute(
        """
        INSERT INTO attendance
        (
            student_id,
            subject,
            attended,
            total
        )
        VALUES
        (
            %s,
            %s,
            %s,
            %s
        )
        """,
        (
            request.form["student_id"],
            request.form["subject"],
            request.form["attended"],
            request.form["total"]
        )
    )

    return jsonify(
        ok=True,
        message="Attendance saved."
    )


# =========================================================
# ADMIN - EDIT ATTENDANCE
# =========================================================

@app.post(
    "/api/admin/attendance/<int:aid>/edit"
)
@admin_required
def edit_attendance(aid):

    execute(
        """
        UPDATE attendance
        SET
            student_id=%s,
            subject=%s,
            attended=%s,
            total=%s
        WHERE id=%s
        """,
        (
            request.form["student_id"],
            request.form["subject"],
            request.form["attended"],
            request.form["total"],
            aid
        )
    )

    return jsonify(
        ok=True,
        message="Attendance updated."
    )


# =========================================================
# ADMIN - DELETE ATTENDANCE
# =========================================================

@app.post(
    "/api/admin/attendance/<int:aid>/delete"
)
@admin_required
def delete_attendance(aid):

    execute(
        """
        DELETE FROM attendance
        WHERE id=%s
        """,
        (
            aid,
        )
    )

    return jsonify(
        ok=True,
        message="Attendance deleted."
    )


# =========================================================
# ADMIN - MARKS
# =========================================================

@app.post("/api/admin/marks")
@admin_required
def add_marks():

    execute(
        """
        INSERT INTO marks
        (
            student_id,
            subject,
            internal,
            assignment,
            exam
        )
        VALUES
        (
            %s,
            %s,
            %s,
            %s,
            %s
        )
        """,
        (
            request.form["student_id"],
            request.form["subject"],
            request.form.get(
                "internal",
                0
            ),
            request.form.get(
                "assignment",
                0
            ),
            request.form.get(
                "exam",
                0
            )
        )
    )

    return jsonify(
        ok=True,
        message="Marks saved."
    )


# =========================================================
# ADMIN - EDIT MARKS
# =========================================================

@app.post(
    "/api/admin/marks/<int:mid>/edit"
)
@admin_required
def edit_marks(mid):

    execute(
        """
        UPDATE marks
        SET
            student_id=%s,
            subject=%s,
            internal=%s,
            assignment=%s,
            exam=%s
        WHERE id=%s
        """,
        (
            request.form["student_id"],
            request.form["subject"],
            request.form.get(
                "internal",
                0
            ),
            request.form.get(
                "assignment",
                0
            ),
            request.form.get(
                "exam",
                0
            ),
            mid
        )
    )

    return jsonify(
        ok=True,
        message="Marks updated."
    )


# =========================================================
# ADMIN - DELETE MARKS
# =========================================================

@app.post(
    "/api/admin/marks/<int:mid>/delete"
)
@admin_required
def delete_marks(mid):

    execute(
        """
        DELETE FROM marks
        WHERE id=%s
        """,
        (
            mid,
        )
    )

    return jsonify(
        ok=True,
        message="Marks deleted."
    )


# =========================================================
# ADMIN - ASSIGNMENT
# =========================================================

@app.post("/api/admin/assignment")
@admin_required
def add_assignment():

    execute(
        """
        INSERT INTO assignments
        (
            student_id,
            title,
            subject,
            due_date
        )
        VALUES
        (
            %s,
            %s,
            %s,
            %s
        )
        """,
        (
            request.form["student_id"],
            request.form["title"],
            request.form["subject"],
            request.form["due_date"]
        )
    )

    return jsonify(
        ok=True,
        message="Assignment created."
    )


# =========================================================
# ADMIN - EDIT ASSIGNMENT
# =========================================================

@app.post(
    "/api/admin/assignment/<int:aid>/edit"
)
@admin_required
def edit_assignment(aid):

    execute(
        """
        UPDATE assignments
        SET
            student_id=%s,
            title=%s,
            subject=%s,
            due_date=%s
        WHERE id=%s
        """,
        (
            request.form["student_id"],
            request.form["title"],
            request.form["subject"],
            request.form["due_date"],
            aid
        )
    )

    return jsonify(
        ok=True,
        message="Assignment updated."
    )


# =========================================================
# ADMIN - DELETE ASSIGNMENT
# =========================================================

@app.post(
    "/api/admin/assignment/<int:aid>/delete"
)
@admin_required
def delete_assignment(aid):

    execute(
        """
        DELETE FROM assignments
        WHERE id=%s
        """,
        (
            aid,
        )
    )

    return jsonify(
        ok=True,
        message="Assignment deleted."
    )


# =========================================================
# ADMIN - NOTICE
# =========================================================

@app.post("/api/admin/notice")
@admin_required
def add_notice():

    execute(
        """
        INSERT INTO notifications
        (
            student_id,
            title,
            message
        )
        VALUES
        (
            %s,
            %s,
            %s
        )
        """,
        (
            request.form.get(
                "student_id"
            ) or None,

            request.form["title"],

            request.form["message"]
        )
    )

    return jsonify(
        ok=True,
        message="Notice published."
    )


# =========================================================
# ADMIN - EDIT NOTICE
# =========================================================

@app.post(
    "/api/admin/notice/<int:nid>/edit"
)
@admin_required
def edit_notice(nid):

    execute(
        """
        UPDATE notifications
        SET
            student_id=%s,
            title=%s,
            message=%s
        WHERE id=%s
        """,
        (
            request.form.get(
                "student_id"
            ) or None,

            request.form["title"],

            request.form["message"],

            nid
        )
    )

    return jsonify(
        ok=True,
        message="Notice updated."
    )


# =========================================================
# ADMIN - DELETE NOTICE
# =========================================================

@app.post(
    "/api/admin/notice/<int:nid>/delete"
)
@admin_required
def delete_notice(nid):

    execute(
        """
        DELETE FROM notifications
        WHERE id=%s
        """,
        (
            nid,
        )
    )

    return jsonify(
        ok=True,
        message="Notice deleted."
    )


# =========================================================
# ADMIN - FEES
# =========================================================

@app.post("/api/admin/fee")
@admin_required
def add_fee():

    execute(
        """
        INSERT INTO fees
        (
            student_id,
            semester,
            amount,
            paid,
            due_date
        )
        VALUES
        (
            %s,
            %s,
            %s,
            %s,
            %s
        )
        """,
        (
            request.form["student_id"],
            request.form["semester"],
            request.form["amount"],
            request.form.get(
                "paid",
                0
            ),
            request.form.get(
                "due_date"
            ) or None
        )
    )

    return jsonify(
        ok=True,
        message="Fee saved."
    )


# =========================================================
# ADMIN - EDIT FEES
# =========================================================

@app.post(
    "/api/admin/fee/<int:fid>/edit"
)
@admin_required
def edit_fee(fid):

    execute(
        """
        UPDATE fees
        SET
            student_id=%s,
            semester=%s,
            amount=%s,
            paid=%s,
            due_date=%s
        WHERE id=%s
        """,
        (
            request.form["student_id"],
            request.form["semester"],
            request.form["amount"],
            request.form.get(
                "paid",
                0
            ),
            request.form.get(
                "due_date"
            ) or None,
            fid
        )
    )

    return jsonify(
        ok=True,
        message="Fee updated."
    )


# =========================================================
# ADMIN - DELETE FEE
# =========================================================

@app.post(
    "/api/admin/fee/<int:fid>/delete"
)
@admin_required
def delete_fee(fid):

    execute(
        """
        DELETE FROM fees
        WHERE id=%s
        """,
        (
            fid,
        )
    )

    return jsonify(
        ok=True,
        message="Fee deleted."
    )


# =========================================================
# ADMIN - LEAVE APPROVAL
# =========================================================

@app.post(
    "/api/admin/leave/<int:lid>"
)
@admin_required
def update_leave(lid):

    status = request.form.get(
        "status"
    )

    if status not in (
        "Approved",
        "Rejected"
    ):

        return jsonify(
            ok=False,
            message="Invalid status."
        ), 400

    execute(
        """
        UPDATE leave_requests
        SET status=%s
        WHERE id=%s
        """,
        (
            status,
            lid
        )
    )

    return jsonify(
        ok=True,
        message=f"Leave {status.lower()}."
    )


# =========================================================
# ADMIN - DELETE LEAVE
# =========================================================

@app.post(
    "/api/admin/leave/<int:lid>/delete"
)
@admin_required
def delete_leave(lid):

    execute(
        """
        DELETE FROM leave_requests
        WHERE id=%s
        """,
        (
            lid,
        )
    )

    return jsonify(
        ok=True,
        message="Leave request deleted."
    )


# =========================================================
# ADMIN - WEBSITE SETTINGS
# =========================================================

@app.post("/api/admin/settings")
@admin_required
def update_settings():

    allowed = {
        "site_title",
        "hero_title",
        "hero_subtitle",
        "hero_label",
        "font_family"
    }

    for key in allowed:

        if key in request.form:

            value = request.form.get(
                key,
                ""
            ).strip()

            set_setting(
                key,
                value
            )

    return jsonify(
        ok=True,
        message="Website settings updated."
    )


# =========================================================
# ADMIN - FONT SETTINGS
# =========================================================

@app.post("/api/admin/font")
@admin_required
def update_font():

    allowed_fonts = {
        "Inter",
        "Segoe UI",
        "Arial",
        "Verdana",
        "Tahoma",
        "Georgia",
        "Times New Roman",
        "Trebuchet MS",
        "Courier New",
        "system-ui"
    }

    font = request.form.get(
        "font_family",
        "Inter"
    ).strip()

    if font not in allowed_fonts:

        return jsonify(
            ok=False,
            message="Font not allowed."
        ), 400

    set_setting(
        "font_family",
        font
    )

    return jsonify(
        ok=True,
        message="Font updated."
    )


# =========================================================
# ADMIN - CAMPUS PHOTO UPLOAD
# =========================================================

@app.post("/api/admin/photo")
@admin_required
def upload_photo():

    file = request.files.get(
        "photo"
    )

    if not file or not file.filename:

        return jsonify(
            ok=False,
            message="Please select an image."
        ), 400

    original_name = secure_filename(
        file.filename
    )

    extension = (
        original_name
        .rsplit(".", 1)[-1]
        .lower()
        if "." in original_name
        else ""
    )

    if extension not in ALLOWED_IMAGE_EXTENSIONS:

        return jsonify(
            ok=False,
            message="Unsupported image format."
        ), 400

    filename = (
        "campus."
        + extension
    )

    filepath = os.path.join(
        app.config["UPLOAD_FOLDER"],
        filename
    )

    for old_file in os.listdir(
        app.config["UPLOAD_FOLDER"]
    ):

        if old_file.startswith(
            "campus."
        ):

            try:

                os.remove(
                    os.path.join(
                        app.config[
                            "UPLOAD_FOLDER"
                        ],
                        old_file
                    )
                )

            except OSError:

                pass

    file.save(
        filepath
    )

    image_url = (
        "uploads/"
        + filename
    )

    set_setting(
        "campus_image",
        image_url
    )

    return jsonify(
        ok=True,
        message="Campus photo updated.",
        image=image_url
    )


# =========================================================
# ADMIN - REMOVE CAMPUS PHOTO
# =========================================================

@app.post(
    "/api/admin/photo/delete"
)
@admin_required
def delete_photo():

    current_image = get_setting(
        "campus_image",
        ""
    )

    if current_image.startswith(
        "uploads/"
    ):

        filename = os.path.basename(
            current_image
        )

        filepath = os.path.join(
            app.config["UPLOAD_FOLDER"],
            filename
        )

        if os.path.exists(
            filepath
        ):

            try:

                os.remove(
                    filepath
                )

            except OSError:

                pass

    set_setting(
        "campus_image",
        "img/campus.svg"
    )

    return jsonify(
        ok=True,
        message="Campus photo removed."
    )


# =========================================================
# ADMIN - RESET WEBSITE
# =========================================================

@app.post(
    "/api/admin/settings/reset"
)
@admin_required
def reset_settings():

    defaults = {

        "site_title":
            "KJC | Campus Portal",

        "hero_title":
            "Operate the campus.",

        "hero_subtitle":
            "Manage students, academics and workflows.",

        "hero_label":
            "ADMIN MODE",

        "font_family":
            "Inter",

        "campus_image":
            "img/campus.svg"
    }

    for key, value in defaults.items():

        set_setting(
            key,
            value
        )

    return jsonify(
        ok=True,
        message="Website settings reset."
    )


# =========================================================
# ADMIN - SETTINGS API
# =========================================================

@app.get(
    "/api/admin/settings"
)
@admin_required
def admin_settings():

    return jsonify(
        ok=True,
        settings=get_all_settings()
    )


# =========================================================
# HEALTH CHECK
# =========================================================

@app.get("/health")
def health():

    try:

        fetch(
            "SELECT 1"
        )

        return jsonify(
            status="ok",
            database="connected"
        )

    except Exception as e:

        return jsonify(
            status="error",
            database="disconnected",
            message=str(e)
        ), 500


# =========================================================
# STARTUP
# =========================================================

try:

    create_admin_settings_table()

except Exception as e:

    print(
        "Startup database error:",
        e
    )


# =========================================================
# RUN SERVER
# =========================================================

if __name__ == "__main__":

    print(
        "========================================"
    )

    print(
        " KJC CAMPUS PORTAL"
    )

    print(
        " Backend starting..."
    )

    print(
        " URL: http://127.0.0.1:5000"
    )

    print(
        "========================================"
    )

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )