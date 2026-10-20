import streamlit as st
import mysql.connector
from datetime import datetime, date, timedelta
from db import get_conn, fetch_all, run


def search(user):
    st.subheader(f"Welcome, {user['name']}")
    st.subheader("Search flights")

    with st.spinner("Loading airports..."):
        airports = fetch_all("SELECT airport_id, code, city FROM airports ORDER BY city")
    names = {a["airport_id"]: f"{a['city']} ({a['code']})" for a in airports}
    ids = list(names.keys())

    with st.form("search_form"):
        c1, c2, c3 = st.columns(3)
        origin = c1.selectbox("From", ids, format_func=lambda i: names[i])
        dest = c2.selectbox("To", ids, index=1, format_func=lambda i: names[i])
        day = c3.date_input("Date", value=date.today() + timedelta(days=1), min_value=date.today())
        go = st.form_submit_button("Search flights")

    if go:
        if origin == dest:
            st.error("From and To must be different.")
        else:
            st.session_state.search = (origin, dest, day)

    params = st.session_state.get("search")
    if not params:
        return

    o, d, the_day = params
    with st.spinner("Searching flights..."):
        rows = fetch_all(
            "SELECT f.flight_id, f.flight_no, f.airline, f.departure_time, f.arrival_time, f.fare_per_seat, "
            "(SELECT COUNT(*) FROM seats s WHERE s.flight_id = f.flight_id AND s.status = 'AVAILABLE') AS seats_left "
            "FROM flights f "
            "WHERE f.origin_id = %s AND f.dest_id = %s AND DATE(f.departure_time) = %s AND f.status = 'ACTIVE' "
            "ORDER BY f.departure_time",
            (o, d, the_day)
        )

    if not rows:
        st.info("No flights found for this route and date.")
        return

    st.markdown(f"### {names[o]} → {names[d]}, {the_day:%d %b %Y}")
    limit = datetime.now() + timedelta(hours=1)
    for r in rows:
        c = st.columns([3, 3, 2, 2, 2])
        c[0].write(f"**{r['flight_no']}**  \n{r['airline']}")
        c[1].write(f"**{r['departure_time']:%H:%M}** → {r['arrival_time']:%H:%M}")
        c[2].write(f"{r['seats_left']} seats left")
        c[3].write(f"৳ {r['fare_per_seat']:,.0f}")
        if r["departure_time"] < datetime.now():
            c[4].write("Departed")
        elif r["departure_time"] < limit:
            c[4].write("Booking closed")
        elif r["seats_left"] == 0:
            c[4].write("Sold out")
        elif c[4].button("Select", key=f"sel_{r['flight_id']}"):
            st.session_state.selected_flight = r["flight_id"]

    if st.session_state.get("selected_flight"):
        st.info("Flight selected. Choosing seats comes in the next slice.")


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


def add_flight(flight_no, airline, origin, dest, dep, arr, fare, seats):
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO flights (flight_no, airline, origin_id, dest_id, departure_time, arrival_time, fare_per_seat, total_seats) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
            (flight_no, airline, origin, dest, dep, arr, fare, seats)
        )
        flight_id = cur.lastrowid
        rows = []
        for i in range(seats):
            rows.append((flight_id, f"{i // 6 + 1}{'ABCDEF'[i % 6]}"))
        cur.executemany("INSERT INTO seats (flight_id, seat_no) VALUES (%s, %s)", rows)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


def flights(user):
    st.subheader("Flights")

    with st.spinner("Loading flights..."):
        airports = fetch_all("SELECT airport_id, code, city FROM airports ORDER BY city")
        rows = fetch_all(
            "SELECT f.flight_id, f.flight_no, f.airline, o.code AS origin, d.code AS dest, "
            "f.departure_time, f.fare_per_seat, f.status "
            "FROM flights f "
            "JOIN airports o ON o.airport_id = f.origin_id "
            "JOIN airports d ON d.airport_id = f.dest_id "
            "ORDER BY f.departure_time"
        )

    names = {a["airport_id"]: f"{a['city']} ({a['code']})" for a in airports}
    ids = list(names.keys())

    with st.expander("Add a flight"):
        with st.form("add_flight_form"):
            c1, c2 = st.columns(2)
            flight_no = c1.text_input("Flight number")
            airline = c2.text_input("Airline")
            origin = c1.selectbox("From", ids, format_func=lambda i: names[i])
            dest = c2.selectbox("To", ids, index=1, format_func=lambda i: names[i])
            dep_date = c1.date_input("Departure date")
            dep_time = c2.time_input("Departure time")
            arr_date = c1.date_input("Arrival date")
            arr_time = c2.time_input("Arrival time")
            fare = c1.number_input("Fare per seat (৳)", min_value=1, value=5000)
            seats = c2.number_input("Total seats", min_value=6, max_value=120, value=72, step=6)
            add = st.form_submit_button("Add flight")
        if add:
            dep = datetime.combine(dep_date, dep_time)
            arr = datetime.combine(arr_date, arr_time)
            if not (flight_no and airline):
                st.error("Please fill in the flight number and airline.")
            elif origin == dest:
                st.error("From and To must be different.")
            elif arr <= dep:
                st.error("Arrival must be after departure.")
            elif dep <= datetime.now():
                st.error("Departure must be in the future.")
            else:
                try:
                    with st.spinner("Adding flight..."):
                        add_flight(flight_no, airline, origin, dest, dep, arr, fare, seats)
                    st.success("Flight added. Open the page again to see it in the list.")
                except mysql.connector.IntegrityError:
                    st.error("This flight number already exists on that date.")

    show_old = st.checkbox("Include past flights")
    rows = [r for r in rows if show_old or r["departure_time"] >= datetime.now()]

    st.markdown("### All flights")
    for r in rows:
        c = st.columns([2, 2, 3, 2, 2])
        c[0].write(f"**{r['flight_no']}**  \n{r['airline']}")
        c[1].write(f"{r['origin']} → {r['dest']}")
        c[2].write(str(r["departure_time"]))
        c[3].write(f"৳ {r['fare_per_seat']}")
        if r["status"] == "CANCELLED":
            c[4].write("Cancelled")
        elif r["departure_time"] < datetime.now():
            c[4].write("Departed")
        elif c[4].button("Cancel", key=f"cancel_{r['flight_id']}"):
            with st.spinner("Cancelling..."):
                run("UPDATE flights SET status='CANCELLED' WHERE flight_id=%s", (r["flight_id"],))
            st.rerun()


def refunds(user):
    st.subheader("Refunds")
    st.info("Coming in Slice 5.")


USER_PAGES = {
    "Home": search,
    "My bookings": my_bookings,
    "Profile": profile,
}

ADMIN_PAGES = {
    "Payments": payments,
    "Flights": flights,
    "Refunds": refunds,
}