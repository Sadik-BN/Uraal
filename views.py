import streamlit as st
import mysql.connector
from datetime import datetime, date, timedelta
from db import get_conn, fetch_all, run
from seats_page import seat_page, hold_view, PAY_NUMBER
from booking import expire_old_holds, active_hold, cancel_flight, confirm_payment, reject_payment, submit_payment, PayError, MIN_RECHECK_MIN


def search(user):
    if st.session_state.get("pay_msg"):
        st.success(st.session_state.pop("pay_msg"))
    expire_old_holds()
    hold = active_hold(user["id"])
    last = st.session_state.pop("last_hold_id", None)
    if hold:
        st.session_state.last_hold_id = hold["booking_id"]
    else:
        st.session_state.view_seats = False
        if last:
            rows = fetch_all(
                "SELECT status FROM bookings WHERE booking_id = %s AND user_id = %s",
                (last, user["id"])
            )
            if rows and rows[0]["status"] == "FLIGHT_CANCELLED":
                st.error("This flight was cancelled by the airline, so your held seats were released.")
            elif rows and rows[0]["status"] == "EXPIRED":
                st.warning("Your hold expired, so the seats were released.")
    if hold and not st.session_state.get("view_seats"):
        hold_view(user, hold)
        return

    if st.session_state.get("selected_flight"):
        seat_page(user)
        return

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
            st.session_state.chosen = []
            st.rerun()



STATUS_LABELS = {
    "HELD": ("On hold", "blue"),
    "PENDING": ("Pending admin check", "orange"),
    "CONFIRMED": ("Booked", "green"),
    "RECHECK": ("Recheck required", "orange"),
    "EXPIRED": ("Expired", "gray"),
    "REJECTED": ("Rejected", "red"),
    "CANCELLED": ("Cancelled", "red"),
    "FLIGHT_CANCELLED": ("Flight cancelled", "red"),
}


def my_bookings(user):
    expire_old_holds()
    st.subheader("My bookings")
    if st.session_state.get("pay_msg"):
        st.success(st.session_state.pop("pay_msg"))
    if st.button("↻ Refresh"):
        st.rerun()

    with st.spinner("Loading bookings..."):
        rows = fetch_all(
            "SELECT b.booking_id, b.booking_ref, b.status, b.total_amount, b.hold_expires_at, "
            "b.recheck_deadline, b.cancel_reason, "
            "(SELECT p.admin_message FROM payments p WHERE p.booking_id = b.booking_id "
            " AND p.status = 'REJECTED' ORDER BY p.payment_id DESC LIMIT 1) AS admin_message, "
            "f.flight_no, f.airline, f.departure_time, o.code AS origin, d.code AS dest, "
            "(SELECT GROUP_CONCAT(s.seat_no ORDER BY s.seat_id SEPARATOR ', ') "
            " FROM booking_seats bs JOIN seats s ON s.seat_id = bs.seat_id "
            " WHERE bs.booking_id = b.booking_id) AS seats "
            "FROM bookings b "
            "JOIN flights f ON f.flight_id = b.flight_id "
            "JOIN airports o ON o.airport_id = f.origin_id "
            "JOIN airports d ON d.airport_id = f.dest_id "
            "WHERE b.user_id = %s "
            "ORDER BY b.created_at DESC",
            (user["id"],)
        )

    if not rows:
        st.info("You have no bookings yet.")
        return

    for r in rows:
        label, color = STATUS_LABELS.get(r["status"], (r["status"], "gray"))
        with st.container(border=True):
            top = st.columns([3, 2])
            top[0].markdown(f"**{r['booking_ref']}**")
            top[1].markdown(f":{color}-badge[{label}]")
            st.write(
                f"{r['flight_no']} · {r['airline']} · {r['origin']} → {r['dest']} · "
                f"{r['departure_time']:%d %b %Y, %H:%M}"
            )
            st.write(f"Seats: {r['seats']}  ·  Total: ৳ {r['total_amount']:,.0f}")
            if r["status"] == "HELD":
                st.caption(
                    f"Seats will expire at {r['hold_expires_at'].strftime('%-I:%M %p')}. "
                    "Open Search flights to pay."
                )
            if r["status"] == "RECHECK":
                st.warning(f"Message from admin: {r['admin_message']}")
                st.write(
                    f"Fix the payment before **{r['recheck_deadline']:%d %b, %-I:%M %p}** "
                    "or the booking will be cancelled."
                )
                st.caption(
                    "After fixing the problem, enter the transaction ID. Correct the ID, or pay the "
                    f"remaining or full amount again to {PAY_NUMBER} via bKash, as the message says. "
                    f"Total fare: ৳ {r['total_amount']:,.0f}."
                )
                with st.form(f"recheck_{r['booking_id']}"):
                    txn = st.text_input("bKash transaction ID")
                    go = st.form_submit_button("Submit transaction ID")
                if go:
                    try:
                        with st.spinner("Submitting..."):
                            submit_payment(user["id"], r["booking_id"], txn)
                        st.session_state.pay_msg = "Transaction ID submitted. Your booking is pending admin check."
                        st.rerun()
                    except PayError as e:
                        st.error(str(e))
            if r["status"] == "REJECTED":
                st.error(f"Message from admin: {r['cancel_reason']}")


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


REASONS = ["Invalid transaction ID", "Full payment not received", "Fare refunded", "Other"]


def fmt_mins(mins):
    h, m = divmod(max(int(mins), 0), 60)
    if h:
        return f"{h}h {m}m"
    return f"{m}m"


def payments(user):
    st.subheader("Payments to check")
    if st.button("↻ Refresh"):
        st.rerun()
    expire_old_holds()

    with st.spinner("Loading payments..."):
        rows = fetch_all(
            "SELECT p.payment_id, p.txn_id, p.attempt_no, b.booking_id, b.booking_ref, b.total_amount, NOW() AS db_now, "
            "u.full_name, u.phone, f.flight_no, f.departure_time, o.code AS origin, d.code AS dest, "
            "p.submitted_at, "
            "TIMESTAMPDIFF(MINUTE, NOW(), f.departure_time) AS mins_to_dep, "
            "(SELECT GROUP_CONCAT(s.seat_no ORDER BY s.seat_id SEPARATOR ', ') "
            " FROM booking_seats bs JOIN seats s ON s.seat_id = bs.seat_id "
            " WHERE bs.booking_id = b.booking_id) AS seats "
            "FROM payments p "
            "JOIN bookings b ON b.booking_id = p.booking_id "
            "JOIN users u ON u.user_id = b.user_id "
            "JOIN flights f ON f.flight_id = b.flight_id "
            "JOIN airports o ON o.airport_id = f.origin_id "
            "JOIN airports d ON d.airport_id = f.dest_id "
            "WHERE p.status = 'PENDING' AND b.status = 'PENDING' "
            "ORDER BY f.departure_time"
        )
        rechecks = fetch_all(
            "SELECT b.booking_ref, u.full_name, f.flight_no, "
            "b.recheck_deadline "
            "FROM bookings b "
            "JOIN users u ON u.user_id = b.user_id "
            "JOIN flights f ON f.flight_id = b.flight_id "
            "WHERE b.status = 'RECHECK' ORDER BY b.recheck_deadline"
        )

    if st.session_state.get("admin_msg"):
        st.success(st.session_state.pop("admin_msg"))

    if not rows:
        st.info("No payments waiting for a check.")
    else:
        urgent = sum(1 for r in rows if r["mins_to_dep"] < 360)
        if urgent:
            st.error(f"{urgent} payment(s) need urgent attention: the flight departs in under 6 hours.")
        st.caption("Sorted by nearest departure.")
        for r in rows:
            pid = r["payment_id"]
            with st.container(border=True):
                top = st.columns([3, 2])
                top[0].markdown(f"**{r['booking_ref']}** · {r['full_name']} · {r['phone']}")
                if r["mins_to_dep"] < 0:
                    top[1].markdown(":red-badge[Flight departed]")
                elif r["mins_to_dep"] < 360:
                    top[1].markdown(":red-badge[Departs within 6 hours]")
                st.write(
                    f"{r['flight_no']} · {r['origin']} → {r['dest']} · "
                    f"{r['departure_time']:%d %b %Y, %H:%M} · Seats: {r['seats']}"
                )
                st.write(
                    f"Fare: **৳ {r['total_amount']:,.0f}** · Transaction ID: `{r['txn_id']}` · "
                    f"Submitted: {r['submitted_at']:%d %b, %-I:%M %p} · Attempt {r['attempt_no']}"
                )
                prev = fetch_all(
                    "SELECT attempt_no, txn_id, submitted_at, admin_message FROM payments "
                    "WHERE booking_id = %s AND payment_id < %s ORDER BY attempt_no",
                    (r["booking_id"], pid)
                )
                if prev:
                    with st.expander(f"Previous attempts ({len(prev)})"):
                        for h in prev:
                            st.write(f"Attempt {h['attempt_no']} · `{h['txn_id']}` · {h['submitted_at']:%d %b, %-I:%M %p}")
                            st.caption(f"Your message: {h['admin_message']}")
                ok = st.checkbox(f"I checked that ৳ {r['total_amount']:,.0f} was received", key=f"chk_{pid}")
                if st.button("Confirm", key=f"ok_{pid}", type="primary", disabled=not ok):
                    try:
                        with st.spinner("Confirming..."):
                            confirm_payment(user["id"], pid)
                        st.session_state.admin_msg = f"{r['booking_ref']} confirmed."
                        st.rerun()
                    except PayError as e:
                        st.error(str(e))
                with st.expander("Reject payment"):
                    room = r["mins_to_dep"] - 60
                    reason = st.selectbox("Reason", REASONS, key=f"rs_{pid}")
                    extra = st.text_input("Message to passenger (optional)", key=f"rm_{pid}")
                    msg = reason
                    if extra.strip():
                        msg = f"{reason}. {extra.strip()}"
                    if room >= MIN_RECHECK_MIN:
                        hours = st.selectbox(
                            "Time for the passenger to fix the payment (hours)",
                            [1, 2, 3, 6, 12, 24, 48], index=5, key=f"hr_{pid}"
                        )
                        limit = r["departure_time"] - timedelta(hours=1)
                        deadline = min(r["db_now"] + timedelta(hours=hours), limit)
                        note = " (shortened: 1 hour before departure)" if deadline == limit else ""
                        st.caption(f"Deadline: {deadline:%d %b, %-I:%M %p}{note}")
                        if st.button("Send back to passenger", key=f"rj_{pid}"):
                            try:
                                with st.spinner("Sending..."):
                                    reject_payment(user["id"], pid, msg, hours)
                                st.session_state.admin_msg = f"{r['booking_ref']} sent back for recheck."
                                st.rerun()
                            except PayError as e:
                                st.error(str(e))
                    else:
                        st.warning("Not enough time before departure for a recheck.")
                    if st.button("Reject and release seats", key=f"rl_{pid}"):
                        try:
                            with st.spinner("Rejecting..."):
                                reject_payment(user["id"], pid, msg, release=True)
                            st.session_state.admin_msg = f"{r['booking_ref']} rejected and seats released."
                            st.rerun()
                        except PayError as e:
                            st.error(str(e))

    if rechecks:
        st.markdown("### Waiting for passenger recheck")
        for r in rechecks:
            st.write(
                f"**{r['booking_ref']}** · {r['full_name']} · {r['flight_no']} · "
                f"Deadline: {r['recheck_deadline']:%d %b, %-I:%M %p}"
            )


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
                    st.success("Flight added. Click refresh to see it in the list.")
                except mysql.connector.IntegrityError:
                    st.error("This flight number already exists on that date.")

    cb1, cb2, _ = st.columns([2, 1.2, 4])
    show_old = cb1.checkbox("Include past flights")
    if cb2.button("↻ Refresh"):
        st.rerun()
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
                cancel_flight(r["flight_id"])
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