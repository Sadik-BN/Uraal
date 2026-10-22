import streamlit as st
from db import fetch_all
from booking import cancel_quote, cancel_booking, CancelError

REASONS = ["Change of plans", "Booked wrong date", "Booked wrong route", "Other"]
TIERS = [
    (1440, "More than 24 hours before departure", "90% refund"),
    (360, "6 to 24 hours before departure", "60% refund"),
    (60, "1 to 6 hours before departure", "30% refund"),
    (0, "Less than 1 hour before departure", "Cannot cancel"),
]


def cancel_page(user):
    bid = st.session_state.cancel_id
    if st.button("← Back to my bookings"):
        st.session_state.cancel_id = None
        st.rerun()

    with st.spinner("Loading..."):
        q = cancel_quote(user["id"], bid)
        phone = fetch_all("SELECT phone FROM users WHERE user_id = %s", (user["id"],))[0]["phone"]
    if not q:
        st.error("Booking not found.")
        return

    st.subheader(f"Cancel booking {q['booking_ref']}")
    st.write(f"{q['flight_no']} · departs {q['departure_time']:%d %b %Y, %H:%M}")

    with st.container(border=True):
        st.write("**Refund policy**")
        current = next(t for t in TIERS if q["mins"] >= t[0])
        for t in TIERS:
            mark = "  ← your booking" if t is current else ""
            st.write(f"{t[1]}: **{t[2]}**{mark}")
        st.write("Flight cancelled by the airline: **100% refund**")
        st.caption("Refunds are sent by bKash after admin approval. Cancelling cannot be undone.")

    if not q["can_cancel"]:
        st.error("This booking can no longer be cancelled.")
        return

    with st.container(border=True):
        st.write(f"Fare paid: ৳ {q['total_amount']:,.0f}")
        st.write(f"Cancellation fee ({100 - q['pct']}%): − ৳ {q['total_amount'] - q['amount']:,.0f}")
        st.write(f"**Refund amount ({q['pct']}%): ৳ {q['amount']:,.0f}**")

    with st.form("cancel_form"):
        reason = st.selectbox("Reason", REASONS)
        st.write(f"Your refund will be sent to your bKash number: **{phone}**")
        sure = st.checkbox("I understand the refund policy and that this cannot be undone.")
        go = st.form_submit_button("Confirm cancellation")
    if go:
        if not sure:
            st.error("Please tick the box to confirm.")
        else:
            try:
                with st.spinner("Cancelling..."):
                    pct, amount = cancel_booking(user["id"], bid, reason, phone)
                st.session_state.cancel_id = None
                st.session_state.cancel_msg = (
                    f"Booking cancelled. Your refund of ৳ {amount:,.0f} ({pct}%) is pending."
                )
                st.rerun()
            except CancelError as e:
                st.error(str(e))