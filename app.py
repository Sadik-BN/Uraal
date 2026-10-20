import streamlit as st
import mysql.connector
from db import get_conn
from views import USER_PAGES, ADMIN_PAGES

st.set_page_config(page_title="Uraal", page_icon="✈️")

if "user" not in st.session_state:
    st.session_state.user = None


def check_login(role, email, password):
    conn = get_conn()
    cur = conn.cursor(dictionary=True)
    if role == "User":
        cur.execute(
            "SELECT user_id AS id, full_name AS name FROM users WHERE email=%s AND password=%s",
            (email, password)
        )
    else:
        cur.execute(
            "SELECT admin_id AS id, name FROM admins WHERE email=%s AND password=%s",
            (email, password)
        )
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row


def register(full_name, email, phone, password):
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO users (full_name, email, phone, password) VALUES (%s, %s, %s, %s)",
            (full_name, email, phone, password)
        )
        conn.commit()
        cur.close()
        conn.close()
        return True
    except mysql.connector.IntegrityError:
        return False


st.title("Uraal Flight Booking")
user = st.session_state.user

if user:
    pages = USER_PAGES if user["role"] == "user" else ADMIN_PAGES
    st.sidebar.write(f"Logged in as **{user['name']}** ({user['role']})")
    choice = st.sidebar.radio("Menu", list(pages.keys()))
    if st.sidebar.button("Log out"):
        st.session_state.user = None
        st.rerun()
    pages[choice](user)
else:
    tab1, tab2 = st.tabs(["Log in", "Create account"])

    with tab1:
        with st.form("login_form"):
            role = st.radio("Log in as", ["User", "Admin"], horizontal=True)
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            go = st.form_submit_button("Log in")
        if go:
            with st.spinner("Logging in..."):
                row = check_login(role, email, password)
                if row:
                    row["role"] = role.lower()
                    st.session_state.user = row
                    st.rerun()
                else:
                    st.error("Email or password is incorrect.")

    with tab2:
        with st.form("register_form"):
            full_name = st.text_input("Full name")
            r_email = st.text_input("Email", key="r_email")
            phone = st.text_input("Phone number")
            r_password = st.text_input("Password", type="password", key="r_password")
            password2 = st.text_input("Confirm password", type="password")
            submit = st.form_submit_button("Create account")
        if submit:
            if not (full_name and r_email and phone and r_password):
                st.error("Please fill in all fields.")
            elif r_password != password2:
                st.error("Passwords do not match.")
            else:
                with st.spinner("Creating account..."):
                    ok = register(full_name, r_email, phone, r_password)
                if ok:
                    st.success("Account created. You can log in now.")
                else:
                    st.error("This email or phone is already registered.")