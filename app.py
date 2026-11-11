
import os
import io
import csv
import json
import joblib
import webbrowser

from datetime import datetime
from zoneinfo import ZoneInfo
from threading import Timer
from functools import wraps

from flask import (
    Flask, render_template, request, redirect,
    url_for, session, flash, make_response
)

from auth_db import register_user, login_user


# ---------------- APP CONFIGURATION ----------------

app = Flask(__name__)

app.secret_key = os.environ.get(
    "SECRET_KEY",
    "student-performance-project-key"
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

MODEL_PATH = os.path.join(
    BASE_DIR, "models", "student_model.pkl"
)

HISTORY_FILE = os.path.join(
    BASE_DIR, "history.json"
)

model = joblib.load(MODEL_PATH)


# ---------------- DEFAULT STAFF ----------------

def create_default_staff():
    try:
        register_user(
            "Staff",
            "STAFF001",
            "staff@college.com",
            "Staff@123",
            "staff"
        )
    except Exception:
        pass


create_default_staff()


# ---------------- HISTORY MANAGEMENT ----------------

def load_history():
    if not os.path.exists(HISTORY_FILE):
        return []

    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as file:
            return json.load(file)

    except (json.JSONDecodeError, OSError):
        return []


def save_history(history):
    with open(HISTORY_FILE, "w", encoding="utf-8") as file:
        json.dump(history, file, indent=4)


def get_visible_history():
    history = load_history()

    if session.get("role") == "staff":
        return history

    student_id = session.get("student_id")

    return [
        item for item in history
        if item.get("student_id") == student_id
    ]


# ---------------- LOGIN PROTECTION ----------------

def login_required(function):
    @wraps(function)
    def wrapper(*args, **kwargs):

        if "user" not in session:
            return redirect(url_for("login"))

        return function(*args, **kwargs)

    return wrapper


def student_required(function):
    @wraps(function)
    def wrapper(*args, **kwargs):

        if "user" not in session:
            return redirect(url_for("login"))

        if session.get("role") != "student":
            flash("Student access only.")
            return redirect(url_for("staff_dashboard"))

        return function(*args, **kwargs)

    return wrapper


def staff_required(function):
    @wraps(function)
    def wrapper(*args, **kwargs):

        if "user" not in session:
            return redirect(url_for("login"))

        if session.get("role") != "staff":
            flash("Staff access only.")
            return redirect(url_for("student_dashboard"))

        return function(*args, **kwargs)

    return wrapper


# ---------------- INPUT VALIDATION ----------------

def validate_academic_inputs(data):

    attendance = float(data["attendance"])
    study_hours = float(data["study_hours"])
    previous_marks = float(data["previous_marks"])
    internal_marks = float(data["internal_marks"])

    if not 0 <= attendance <= 100:
        raise ValueError("Attendance must be between 0 and 100.")

    if not 0 <= study_hours <= 24:
        raise ValueError("Study hours must be between 0 and 24.")

    if not 0 <= previous_marks <= 100:
        raise ValueError("Previous marks must be between 0 and 100.")

    if not 0 <= internal_marks <= 100:
        raise ValueError("Internal marks must be between 0 and 100.")

    return [
        attendance,
        study_hours,
        previous_marks,
        internal_marks
    ]


# ---------------- PREDICTION ----------------

def make_student_record(values):

    prediction = model.predict([values])[0]

    return {
        "attendance": values[0],
        "study_hours": values[1],
        "previous_marks": values[2],
        "internal_marks": values[3],
        "prediction": str(prediction),

        # Indian Standard Time (IST)
        "date": datetime.now(
            ZoneInfo("Asia/Kolkata")
        ).strftime("%d-%m-%Y %I:%M %p"),

        "student_id": session.get("student_id"),
        "student_name": session.get("user")
    }


# ---------------- IMPROVEMENT SUGGESTIONS ----------------

def get_suggestions(prediction, values):

    attendance, study_hours, previous_marks, internal_marks = values

    suggestions = []

    if attendance < 75:
        suggestions.append(
            "Improve attendance and try to maintain at least 75%."
        )

    if study_hours < 2:
        suggestions.append(
            "Increase your daily study time to at least 2 hours."
        )

    if previous_marks < 50:
        suggestions.append(
            "Revise previous lessons and practice more questions."
        )

    if internal_marks < 50:
        suggestions.append(
            "Focus more on internal assessments and assignments."
        )

    if str(prediction).lower() == "good":
        suggestions.append(
            "Good performance! Continue your learning routine."
        )

    if not suggestions:
        suggestions.append(
            "Maintain your current academic routine."
        )

    return suggestions


# ---------------- ACADEMIC RISK ----------------

def get_academic_risk(values):

    attendance, study_hours, previous_marks, internal_marks = values

    if (
        attendance < 60
        or previous_marks < 40
        or internal_marks < 40
    ):
        return "High Risk"

    if attendance < 75 or study_hours < 2:
        return "Medium Risk"

    return "Low Risk"


# ---------------- ATTENDANCE ALERT ----------------

def get_attendance_alert(values):

    attendance = values[0]

    if attendance < 75:
        return (
            "Your attendance is below 75%. "
            "Please attend classes regularly."
        )

    return "Your attendance is satisfactory."


# ---------------- IMPROVEMENT PLAN ----------------

def get_improvement_plan(values):

    attendance, study_hours, previous_marks, internal_marks = values

    plan = []

    if attendance < 75:
        plan.append("Attend classes regularly.")

    if study_hours < 2:
        plan.append("Study for at least 2 hours every day.")

    if previous_marks < 50:
        plan.append("Revise previous lessons.")

    if internal_marks < 50:
        plan.append("Practice internal assessment questions.")

    if not plan:
        plan.append("Continue your learning routine.")

    return plan


# ---------------- PREDICTION EXPLANATION ----------------

def build_prediction_explanation(values, prediction):

    attendance, study_hours, previous_marks, internal_marks = values

    explanation = []

    if attendance < 75:
        explanation.append(
            "Low attendance may affect academic performance."
        )

    if study_hours < 2:
        explanation.append(
            "Daily study hours are relatively low."
        )

    if previous_marks < 50:
        explanation.append(
            "Previous marks indicate a need for revision."
        )

    if internal_marks < 50:
        explanation.append(
            "Internal marks show scope for improvement."
        )

    if not explanation:
        explanation.append(
            "Entered academic values are within the expected ranges."
        )

    explanation.append(
        "Machine Learning Prediction: " + str(prediction)
    )

    return explanation


# ---------------- DASHBOARD STATISTICS ----------------

def get_dashboard_stats():

    history = get_visible_history()

    return {
        "total": len(history),

        "good": sum(
            1 for item in history
            if item.get("prediction", "").lower() == "good"
        ),

        "average": sum(
            1 for item in history
            if item.get("prediction", "").lower() == "average"
        ),

        "poor": sum(
            1 for item in history
            if item.get("prediction", "").lower() == "poor"
        )
    }


def get_latest_student_prediction():

    history = get_visible_history()

    if history:
        return history[-1]

    return None


# ---------------- DASHBOARD RENDERING ----------------

def render_student_dashboard(**kwargs):

    history = get_visible_history()

    stats = get_dashboard_stats()

    latest = get_latest_student_prediction()

    growth_history = history[-10:]

    return render_template(
        "student_dashboard.html",

        history=kwargs.pop("history", history[-5:][::-1]),

        stats=stats,

        latest=latest,

        growth_history=growth_history,

        **kwargs
    )


# ---------------- LOGIN PAGE ----------------

@app.route("/login")
def login():

    return render_template("login.html")


# ---------------- STUDENT LOGIN ----------------

@app.route("/student-login", methods=["GET", "POST"])
def student_login():

    if request.method == "POST":

        email = request.form.get("email")
        password = request.form.get("password")

        user = login_user(email, password, "student")

        if user:

            session["user"] = user["name"]
            session["student_id"] = user["student_id"]
            session["role"] = user["role"]

            return redirect(url_for("student_dashboard"))

        flash("Invalid student login details.")

    return render_template("student_login.html")


# ---------------- STAFF LOGIN ----------------

@app.route("/staff-login", methods=["GET", "POST"])
def staff_login():

    if request.method == "POST":

        email = request.form.get("email")
        password = request.form.get("password")

        user = login_user(email, password, "staff")

        if user:

            session["user"] = user["name"]
            session["student_id"] = user["student_id"]
            session["role"] = user["role"]

            return redirect(url_for("staff_dashboard"))

        flash("Invalid staff login details.")

    return render_template("staff_login.html")


# ---------------- REGISTRATION ----------------

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form.get("name")
        student_id = request.form.get("student_id")
        email = request.form.get("email")
        password = request.form.get("password")

        try:

            register_user(
                name,
                student_id,
                email,
                password,
                "student"
            )

            flash("Registration successful. Please login.")

            return redirect(url_for("student_login"))

        except Exception:

            flash(
                "Registration failed. "
                "Email or Student ID may already exist."
            )

    return render_template("register.html")


# ---------------- LOGOUT ----------------

@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("login"))


# ---------------- STUDENT DASHBOARD ----------------

@app.route("/")
@student_required
def student_dashboard():

    return render_student_dashboard()


# ---------------- PERFORMANCE PREDICTION ----------------

@app.route("/predict", methods=["POST"])
@student_required
def predict():

    try:

        values = validate_academic_inputs(request.form)

        record = make_student_record(values)

        history = load_history()

        history.append(record)

        save_history(history)

        prediction = record["prediction"]

        return render_student_dashboard(

            prediction=prediction,

            suggestions=get_suggestions(
                prediction, values
            ),

            explanation=build_prediction_explanation(
                values, prediction
            ),

            risk=get_academic_risk(values),

            attendance_alert=get_attendance_alert(values),

            improvement_plan=get_improvement_plan(values),

            input_values=values
        )

    except (ValueError, TypeError, KeyError):

        flash("Please enter valid academic details.")

        return redirect(url_for("student_dashboard"))


# ---------------- WHAT-IF SIMULATOR ----------------

@app.route("/simulate", methods=["POST"])
@student_required
def simulate():

    try:

        values = validate_academic_inputs(request.form)

        prediction = model.predict([values])[0]

        latest = get_latest_student_prediction()

        previous_prediction = (
            latest.get("prediction")
            if latest
            else "No previous prediction"
        )

        return render_student_dashboard(

            simulation_prediction=str(prediction),

            previous_prediction=previous_prediction,

            simulation_values=values
        )

    except (ValueError, TypeError, KeyError):

        flash("Please enter valid values for simulation.")

        return redirect(url_for("student_dashboard"))


# ---------------- TARGET MARKS PLANNER ----------------

@app.route("/target-marks", methods=["POST"])
@student_required
def target_marks():

    try:

        current_marks = float(
            request.form.get("current_marks")
        )

        target_marks = float(
            request.form.get("target_marks")
        )

        if not 0 <= current_marks <= 100:
            raise ValueError

        if not 0 <= target_marks <= 100:
            raise ValueError

        gap = target_marks - current_marks

        if gap > 0:

            message = (
                f"You need to improve by {gap:.1f} marks "
                "to reach your target."
            )

        elif gap == 0:

            message = "You have reached your target marks!"

        else:

            message = "You have already achieved your target!"

        return render_student_dashboard(
            target_message=message,
            marks_gap=gap
        )

    except (ValueError, TypeError):

        flash("Enter valid marks between 0 and 100.")

        return redirect(url_for("student_dashboard"))


# ---------------- PREDICTION HISTORY ----------------

@app.route("/history")
@login_required
def history_page():

    history = get_visible_history()

    if session.get("role") == "staff":

        return render_template(
            "history.html",
            history=history[::-1]
        )

    return render_student_dashboard(
        history=history[::-1]
    )


# ---------------- STAFF DASHBOARD ----------------

@app.route("/staff-dashboard")
@staff_required
def staff_dashboard():

    history = get_visible_history()

    stats = get_dashboard_stats()

    return render_template(
        "staff_dashboard.html",
        history=history[::-1],
        stats=stats
    )


# ---------------- CSV REPORT ----------------

@app.route("/download-report")
@staff_required
def download_report():

    history = get_visible_history()

    output = io.StringIO()

    writer = csv.writer(output)

    writer.writerow([
        "Student Name",
        "Student ID",
        "Attendance",
        "Study Hours",
        "Previous Marks",
        "Internal Marks",
        "Prediction",
        "Date"
    ])

    for item in history:

        writer.writerow([
            item.get("student_name"),
            item.get("student_id"),
            item.get("attendance"),
            item.get("study_hours"),
            item.get("previous_marks"),
            item.get("internal_marks"),
            item.get("prediction"),
            item.get("date")
        ])

    response = make_response(output.getvalue())

    response.headers["Content-Disposition"] = (
        "attachment; filename=student_performance_report.csv"
    )

    response.headers["Content-Type"] = "text/csv"

    return response


# ---------------- PDF REPORT ----------------

@app.route("/download-pdf")
@student_required
def download_pdf():

    try:

        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import (
            SimpleDocTemplate,
            Paragraph,
            Spacer,
            Table,
            TableStyle
        )
        from reportlab.lib.styles import getSampleStyleSheet

        buffer = io.BytesIO()

        document = SimpleDocTemplate(
            buffer,
            pagesize=A4
        )

        styles = getSampleStyleSheet()

        elements = []

        elements.append(
            Paragraph(
                "Student Performance Report",
                styles["Title"]
            )
        )

        elements.append(Spacer(1, 20))

        elements.append(
            Paragraph(
                "Student Name: " + str(session.get("user")),
                styles["Normal"]
            )
        )

        elements.append(
            Paragraph(
                "Student ID: " + str(session.get("student_id")),
                styles["Normal"]
            )
        )

        elements.append(Spacer(1, 20))

        history = get_visible_history()

        table_data = [[
            "Date",
            "Attendance",
            "Study Hours",
            "Previous",
            "Internal",
            "Result"
        ]]

        for item in history:

            table_data.append([
                str(item.get("date", "")),
                str(item.get("attendance", "")),
                str(item.get("study_hours", "")),
                str(item.get("previous_marks", "")),
                str(item.get("internal_marks", "")),
                str(item.get("prediction", ""))
            ])

        table = Table(
            table_data,
            repeatRows=1
        )

        table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.darkblue),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("PADDING", (0, 0), (-1, -1), 6)
            ])
        )

        elements.append(table)

        document.build(elements)

        buffer.seek(0)

        response = make_response(buffer.getvalue())

        response.headers["Content-Type"] = "application/pdf"

        response.headers["Content-Disposition"] = (
            "attachment; filename=student_performance_report.pdf"
        )

        return response

    except ImportError:

        return (
            "Please install reportlab using: pip install reportlab",
            500
        )


# ---------------- RUN APPLICATION ----------------

if __name__ == "__main__":

    Timer(
        1.5,
        lambda: webbrowser.open(
            "http://127.0.0.1:5000/login"
        )
    ).start()

    print("Student Performance Prediction Started!")

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True,
        use_reloader=False
    )
