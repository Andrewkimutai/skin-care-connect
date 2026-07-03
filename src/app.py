"""
app.py
Skin Care Connect — main Streamlit application.

Run with:  streamlit run src/app.py
"""
import sys
import uuid
from pathlib import Path
from datetime import datetime

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from PIL import Image

sys.path.append(str(Path(__file__).resolve().parent))

from database import (
    init_db, get_user_by_username, create_user, save_prediction_result,
    book_appointment, get_user_appointments, get_user_predictions,
    get_all_appointments, get_all_users, update_user_role, delete_user,
    update_appointment_status_and_notes,
)
from ai_model import predict_image, CLASS_NAMES_VERBOSE
from auth import hash_password, verify_password
import theme

st.set_page_config(page_title="Skin Care Connect", page_icon="🩺", layout="wide")
theme.inject_css()

# --- Session State ---
DEFAULTS = {
    'authenticated': False, 'username': None, 'user_id': None, 'user_role': None,
    'page': 'home', 'uploaded_image': None, 'prediction_result': None, 'prediction_id': None,
}
for key, value in DEFAULTS.items():
    st.session_state.setdefault(key, value)

init_db()


# --- Auth ---
def login_user(username, password):
    user_record = get_user_by_username(username)
    if user_record:
        user_id, db_username, stored_hash, stored_salt, role = user_record
        if verify_password(stored_hash, stored_salt, password):
            st.session_state.update({
                'authenticated': True, 'username': username,
                'user_id': user_id, 'user_role': role,
            })
            st.rerun()
            return True
    return False


def register_new_user(username, password, email=None, role='user'):
    password_hash, password_salt = hash_password(password)
    return create_user(username, password_hash, password_salt, email, role)


def is_admin():
    return st.session_state.get('user_role') == 'admin'


def is_dermatologist():
    return st.session_state.get('user_role') == 'dermatologist'


def is_user():
    return st.session_state.get('user_role') == 'user'


# --- Navigation ---
def nav_to(page_name):
    st.session_state['page'] = page_name
    st.rerun()


def nav_to_login():
    st.session_state.update({
        'authenticated': False, 'username': None, 'user_id': None,
        'user_role': None, 'page': 'login',
    })
    st.rerun()


# --- Shell ---
def main():
    if st.session_state['authenticated']:
        with st.sidebar:
            st.markdown(f"### 👋 {st.session_state['username']}")
            theme.badge(st.session_state['user_role'].capitalize(), kind="role")
            st.markdown("---")
            st.button("🏠 Home", on_click=nav_to, args=('home',), use_container_width=True)
            if is_user() or is_dermatologist():
                st.button("🔬 Analyze Image", on_click=nav_to, args=('analyze',), use_container_width=True)
            if is_user():
                st.button("📜 History", on_click=nav_to, args=('history',), use_container_width=True)
                st.button("📅 Appointments", on_click=nav_to, args=('appointments',), use_container_width=True)
            if is_dermatologist() or is_admin():
                st.button("🗓️ All Appointments", on_click=nav_to, args=('view_all_appointments',), use_container_width=True)
            if is_admin():
                st.button("👥 Manage Users", on_click=nav_to, args=('manage_users',), use_container_width=True)
            st.markdown("---")
            st.button("🚪 Logout", on_click=nav_to_login, use_container_width=True)

    if st.session_state['authenticated']:
        page = st.session_state['page']
        pages = {
            'home': home_page, 'analyze': analyze_page, 'history': history_page,
            'appointments': appointments_page, 'view_all_appointments': view_all_appointments_page,
            'manage_users': manage_users_page, 'book_appointment': book_appointment_page,
        }
        pages.get(page, home_page)()
    else:
        login_register_page()


def login_register_page():
    theme.hero("Skin Care Connect", "AI-assisted triage for skin lesions, connected to real dermatologists.")
    theme.disclaimer()

    col1, col2 = st.columns([1, 1])
    with col1:
        theme.card_start()
        st.subheader("Login")
        login_username = st.text_input("Username", key="login_username")
        login_password = st.text_input("Password", type="password", key="login_password")
        if st.button("Login", type="primary", use_container_width=True):
            if login_user(login_username, login_password):
                st.success("Logged in successfully!")
            else:
                st.error("Invalid username or password.")
        theme.card_end()

    with col2:
        theme.card_start()
        st.subheader("Register")
        reg_username = st.text_input("Username", key="reg_username")
        reg_email = st.text_input("Email (optional)", key="reg_email")
        reg_password = st.text_input("Password", type="password", key="reg_password")
        reg_confirm_password = st.text_input("Confirm password", type="password", key="reg_confirm_password")
        if st.button("Create account", use_container_width=True):
            if reg_password != reg_confirm_password:
                st.error("Passwords do not match.")
            elif len(reg_password) < 6:
                st.error("Password must be at least 6 characters long.")
            elif not reg_username:
                st.error("Username is required.")
            else:
                if register_new_user(reg_username, reg_password, reg_email, 'user'):
                    st.success("Registration successful! Please log in.")
                else:
                    st.error("Username or email already exists.")
        theme.card_end()


def home_page():
    role = st.session_state['user_role']
    theme.hero(f"Welcome, {st.session_state['username']}", f"Signed in as {role}. Here's what you can do.")
    theme.disclaimer()

    features = []
    if is_user() or is_dermatologist():
        features.append(("🔬", "Analyze Image", "Upload a skin photo for an AI-assisted classification."))
    if is_user():
        features.append(("📜", "History", "Review your past analyses."))
        features.append(("📅", "Appointments", "Track appointments booked from your analyses."))
    if is_dermatologist() or is_admin():
        features.append(("🗓️", "All Appointments", "See and respond to every booked appointment."))
    if is_admin():
        features.append(("👥", "Manage Users", "Add, edit or remove user accounts and roles."))

    cols = st.columns(min(len(features), 3) or 1)
    for i, (icon, title, desc) in enumerate(features):
        with cols[i % len(cols)]:
            theme.card_start()
            st.markdown(f"#### {icon} {title}")
            st.write(desc)
            theme.card_end()


def analyze_page():
    theme.hero("Analyze Skin Image", "Upload a clear, well-lit photo of the skin area of concern.")
    theme.disclaimer()

    left, right = st.columns([1, 1.3])

    with left:
        theme.card_start()
        uploaded_file = st.file_uploader(
            "Choose a skin image", type=["jpg", "jpeg", "png"],
            help="Use good lighting and fill the frame with the lesion."
        )
        if uploaded_file is not None:
            image = Image.open(uploaded_file)
            st.image(image, caption="Uploaded image", use_container_width=True)
        theme.card_end()

    if uploaded_file is not None:
        with right:
            try:
                with st.spinner("Analyzing image..."):
                    result = predict_image(image)
                    user_id = st.session_state['user_id']
                    unique_filename = f"{uuid.uuid4()}_{uploaded_file.name}"
                    prediction_id = save_prediction_result(user_id, unique_filename, result)

                    st.session_state['prediction_result'] = result
                    st.session_state['prediction_id'] = prediction_id
                    st.session_state['uploaded_image'] = image

                display_results(result, prediction_id)
            except Exception as e:
                st.error(f"Error processing image: {str(e)}")
                st.info("Please try uploading a different image file.")


def display_results(result, prediction_id):
    if result['error'] and not result.get('is_valid_prediction', False) and result['predicted_class'] in (
            'Non-Skin Image', 'Unclassified'):
        theme.card_start()
        st.warning(result['error'])
        st.write(result['recommendation'])
        theme.card_end()
        return

    predicted_class = result['predicted_class']
    confidence = result['confidence']
    all_predictions = result['all_predictions']
    recommendation = result['recommendation']
    needs_appointment = result['needs_appointment']

    if predicted_class == "Melanoma":
        risk_kind, risk_label = "danger", "⚠️ Higher-risk class detected"
    elif confidence > 80:
        risk_kind, risk_label = "success", "High model confidence"
    elif confidence > 60:
        risk_kind, risk_label = "warning", "Moderate model confidence"
    else:
        risk_kind, risk_label = "warning", "Low model confidence"

    st.markdown(
        f'<div class="scc-result-hero scc-result-{risk_kind}">'
        f'<h3 style="margin-top:0;">{predicted_class}</h3>'
        f'<p style="margin:0 0 .4rem 0;">{risk_label} &nbsp;•&nbsp; Confidence: <strong>{confidence:.1f}%</strong></p>'
        f'<p style="margin:0;">{recommendation}</p>'
        f'</div>',
        unsafe_allow_html=True,
    )

    if needs_appointment:
        if st.button("📅 Book appointment for this analysis", type="primary"):
            st.session_state['page'] = 'book_appointment'
            st.session_state['booking_prediction_id'] = prediction_id
            st.rerun()

    theme.card_start()
    st.markdown("**Class probabilities**")
    sorted_preds = sorted(all_predictions.items(), key=lambda x: x[1], reverse=True)
    labels, values = zip(*sorted_preds)
    colors = [theme.DANGER if lbl == "Melanoma" else theme.PRIMARY for lbl in labels]
    fig = go.Figure(go.Bar(
        x=values, y=labels, orientation='h', marker_color=colors,
        text=[f"{v:.1f}%" for v in values], textposition='outside',
    ))
    fig.update_layout(
        height=320, margin=dict(l=10, r=10, t=10, b=10),
        xaxis=dict(range=[0, 100], title="Probability (%)"),
        yaxis=dict(autorange="reversed"), plot_bgcolor="white",
    )
    st.plotly_chart(fig, use_container_width=True)
    theme.card_end()


def history_page():
    theme.hero("Analysis History", "Every analysis you've run, most recent first.")
    predictions = get_user_predictions(st.session_state['user_id'])

    if not predictions:
        st.info("You have no analysis history yet.")
        return

    for pred in predictions:
        pid, img_filename, pred_class, conf, rec, needs_appt, timestamp = pred
        with st.expander(f"{timestamp} — {pred_class} ({conf:.1f}%)"):
            st.write(f"**Prediction:** {pred_class}")
            st.write(f"**Confidence:** {conf:.2f}%")
            st.write(f"**Recommendation:** {rec}")
            st.write(f"**Needs appointment:** {'Yes' if needs_appt else 'No'}")


def appointments_page():
    theme.hero("My Appointments", "Appointments you've booked from analysis results.")
    appointments = get_user_appointments(st.session_state['user_id'])

    if not appointments:
        st.info("You have no upcoming appointments.")
        return

    status_kind = {'pending': 'warning', 'confirmed': 'success', 'cancelled': 'danger'}
    for appt in appointments:
        aid, sched_date, status, notes, derm_notes, pred_class, pred_conf, pred_time = appt
        theme.card_start()
        st.write(f"**Date & time:** {sched_date}")
        theme.badge(status.capitalize(), kind=status_kind.get(status, 'role'))
        st.write(f"**Patient notes:** {notes or 'N/A'}")
        st.write(f"**Dermatologist reply:** {derm_notes or 'N/A'}")
        st.write(f"**Related analysis:** {pred_class} ({pred_conf:.1f}%) from {pred_time}")
        theme.card_end()


def view_all_appointments_page():
    theme.hero("All Appointments", "Dermatologist / admin view of every booking.")

    if not (is_dermatologist() or is_admin()):
        st.error("Access denied.")
        st.button("Back to Home", on_click=nav_to, args=('home',))
        return

    appointments = get_all_appointments()
    if not appointments:
        st.info("There are no appointments scheduled.")
        return

    for appt in appointments:
        aid, patient_username, sched_date, status, patient_notes, derm_notes, pred_class, pred_conf, pred_time = appt
        theme.card_start()
        st.write(f"**Patient:** {patient_username}  |  **ID:** {aid}")
        st.write(f"**Scheduled:** {sched_date}")
        st.write(f"**Patient notes:** {patient_notes or 'N/A'}")
        st.write(f"**Related analysis:** {pred_class} ({pred_conf:.1f}%) from {pred_time}")

        with st.form(key=f"update_form_{aid}"):
            new_status = st.selectbox(
                "Update status", ["pending", "confirmed", "cancelled"],
                index=["pending", "confirmed", "cancelled"].index(status), key=f"status_{aid}"
            )
            new_notes = st.text_area("Reply to patient", value=derm_notes or "", key=f"notes_{aid}")
            if st.form_submit_button("Update appointment"):
                if update_appointment_status_and_notes(aid, new_status, new_notes):
                    st.success("Appointment updated.")
                    st.rerun()
                else:
                    st.error("Failed to update appointment.")
        theme.card_end()


def manage_users_page():
    theme.hero("Manage Users", "Add, edit, or remove user accounts.")

    if not is_admin():
        st.error("Access denied.")
        st.button("Back to Home", on_click=nav_to, args=('home',))
        return

    users = get_all_users()
    if users:
        df = pd.DataFrame(users, columns=['ID', 'Username', 'Email', 'Role', 'Created At'])
        edited_df = st.data_editor(df, num_rows="dynamic", use_container_width=True,
                                    disabled=['ID', 'Username', 'Email', 'Created At'])

        if st.button("Save role changes"):
            changed = False
            for index, row in edited_df.iterrows():
                if row['Role'] != df.iloc[index]['Role']:
                    if update_user_role(row['ID'], row['Role']):
                        st.success(f"Updated role for user #{row['ID']} to {row['Role']}")
                        changed = True
                    else:
                        st.error(f"Failed to update role for user #{row['ID']}")
            if changed:
                st.rerun()

        st.subheader("Delete user")
        user_ids_to_delete = st.multiselect("Select user IDs to delete", options=df['ID'].tolist())
        if st.button("Delete selected users") and user_ids_to_delete:
            for uid in user_ids_to_delete:
                delete_user(uid)
            st.success("Deleted selected users.")
            st.rerun()
    else:
        st.info("There are no users registered.")

    st.subheader("Add new user")
    with st.form(key='add_user_form'):
        new_username = st.text_input("Username")
        new_email = st.text_input("Email (optional)")
        new_password = st.text_input("Password", type="password")
        new_role = st.selectbox("Role", ["user", "dermatologist", "admin"])
        if st.form_submit_button("Add user"):
            if new_password:
                if register_new_user(new_username, new_password, new_email, new_role):
                    st.success(f"User '{new_username}' added with role '{new_role}'.")
                    st.rerun()
                else:
                    st.error("Username or email already exists.")
            else:
                st.error("Password is required.")


def book_appointment_page():
    theme.hero("Book Appointment", "Confirm a slot to review this analysis with a dermatologist.")

    pred_id = st.session_state.get('booking_prediction_id')
    result = st.session_state.get('prediction_result')
    if not pred_id or not result:
        st.error("No prediction selected for booking.")
        st.button("Back to Home", on_click=nav_to, args=('home',))
        return

    theme.card_start()
    st.write(f"**Analysis ID:** {pred_id}")
    st.write(f"**Result:** {result['predicted_class']} ({result['confidence']:.1f}%)")
    st.write(f"**Recommendation:** {result['recommendation']}")
    theme.card_end()

    with st.form(key='appointment_form'):
        scheduled_date = st.date_input("Date")
        scheduled_time = st.time_input("Time")
        notes = st.text_area("Notes (optional)")
        if st.form_submit_button("Confirm appointment"):
            scheduled_datetime = datetime.combine(scheduled_date, scheduled_time)
            book_appointment(st.session_state['user_id'], pred_id, scheduled_datetime, notes)
            st.success("Appointment booked successfully!")
            st.button("Back to Appointments", on_click=nav_to, args=('appointments',))

    st.button("Cancel", on_click=nav_to, args=('analyze',))


if __name__ == "__main__":
    main()
