import streamlit as st
import mysql.connector
from db import get_conn


def home(user):
    st.subheader(f"Welcome, {user['name']}")
    st.write("Flight search is coming in the next slice.")


def search(user):
    st.subheader("Search flights")
    st.info("Coming in Slice 2.")


def my_bookings(user):
    st.subheader("My bookings")
    st.info("Coming in Slice 3.")


def profile(user):
    st.subheader("Profile")

    with st.spinner("Loading profile..."):
        conn = get_conn()
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT full_name, email, phone FROM users WHERE user_id=%s", (user["id"],))
        row = cur.fetchone()
        cur.close()
        conn.close()

    with st.form("profile_form"):
        full_name = st.text_input("Full name", value=row["full_name"])
        email = st.text_input("Email", value=row["email"])
        phone = st.text_input("Phone number", value=row["phone"])
        save = st.form_submit_button("Save changes")

    if save:
        if not (full_name and email and phone):
            st.error("Please fill in all fields.")
        else:
            try:
                with st.spinner("Saving..."):
                    conn = get_conn()
                    cur = conn.cursor()
                    cur.execute(
                        "UPDATE users SET full_name=%s, email=%s, phone=%s WHERE user_id=%s",
                        (full_name, email, phone, user["id"])
                    )
                    conn.commit()
                    cur.close()
                    conn.close()
                user["name"] = full_name
                st.success("Profile updated.")
            except mysql.connector.IntegrityError:
                st.error("This email or phone is already used by another account.")


def payments(user):
    st.subheader("Payments to check")
    st.info("Coming in Slice 4.")


def flights(user):
    st.subheader("Flights")
    st.info("Coming in Slice 2.")


def refunds(user):
    st.subheader("Refunds")
    st.info("Coming in Slice 5.")


USER_PAGES = {
    "Home": home,
    "Search flights": search,
    "My bookings": my_bookings,
    "Profile": profile,
}

ADMIN_PAGES = {
    "Payments": payments,
    "Flights": flights,
    "Refunds": refunds,
}