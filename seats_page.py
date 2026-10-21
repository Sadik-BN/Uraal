import streamlit as st
from db import fetch_all
from booking import hold_seats, release_hold, update_hold, HoldError

COLS = {"A": 1, "B": 2, "C": 3, "D": 5, "E": 6, "F": 7}
WIDTHS = [0.6, 1, 1, 1, 0.5, 1, 1, 1]
MAX_SEATS = 4


def seat_page(user):
    fid = st.session_state.selected_flight
    if "chosen" not in st.session_state:
        st.session_state.chosen = []
    chosen = st.session_state.chosen

    viewing = st.session_state.get("view_seats", False)
    b1, b2, _ = st.columns([1.5, 1.3, 4])
    if viewing:
        if b1.button("← Back to my hold"):
            st.session_state.view_seats = False
            st.session_state.selected_flight = None
            st.session_state.chosen = []
            st.rerun()
    elif b1.button("← Back to flights"):
        st.session_state.selected_flight = None
        st.session_state.chosen = []
        st.rerun()
    if b2.button("↻ Refresh seats"):
        st.rerun()

    with st.spinner("Loading seats..."):
        flight = fetch_all(
            "SELECT f.flight_no, f.airline, f.departure_time, f.fare_per_seat, f.status AS fstatus, "
            "o.code AS origin, d.code AS dest "
            "FROM flights f "
            "JOIN airports o ON o.airport_id = f.origin_id "
            "JOIN airports d ON d.airport_id = f.dest_id "
            "WHERE f.flight_id = %s",
            (fid,)
        )[0]
        seats = fetch_all("SELECT seat_id, seat_no, status FROM seats WHERE flight_id = %s", (fid,))


    free_ids = {s["seat_id"] for s in seats if s["status"] == "AVAILABLE"}

    mine_ids = set()
    if viewing:
        mine = fetch_all("SELECT seat_id FROM booking_seats WHERE booking_id = %s", (st.session_state.hold_id,))
        mine_ids = {m["seat_id"] for m in mine}
    ok_ids = free_ids | mine_ids
    if any(i not in ok_ids for i in chosen):
        chosen[:] = [i for i in chosen if i in ok_ids]
        st.session_state.seat_msg = "A seat you selected was taken, so it was removed from your selection."


    if flight["fstatus"] != "ACTIVE":
        st.error("This flight has been cancelled. Please choose another flight.")
        st.session_state.selected_flight = None
        st.session_state.chosen = []
        return

    st.subheader("Choose your seats")
    
    st.write(
        f"**{flight['flight_no']}** · {flight['airline']} · "
        f"{flight['origin']} → {flight['dest']} · {flight['departure_time']:%d %b %Y, %H:%M}"
    )

    grid = {}
    for s in seats:
        grid[(int(s["seat_no"][:-1]), s["seat_no"][-1])] = s
    rows = max(r for r, letter in grid)

    if st.session_state.get("seat_msg"):
        st.warning(st.session_state.seat_msg)
        st.session_state.seat_msg = ""

    left, right = st.columns([2.2, 1])

    with left:
        head = st.columns(WIDTHS)
        for letter, idx in COLS.items():
            head[idx].write(f"**{letter}**")
        for r in range(1, rows + 1):
            cols = st.columns(WIDTHS)
            cols[0].write(str(r))
            for letter, idx in COLS.items():
                s = grid.get((r, letter))
                if not s:
                    continue
                free = s["status"] == "AVAILABLE" or s["seat_id"] in mine_ids
                picked = s["seat_id"] in chosen
                label = s["seat_no"] if (free or picked) else "✕"
                kind = "primary" if picked else "secondary"
                clicked = cols[idx].button(
                    label, key=f"seat_{s['seat_id']}", type=kind,
                    disabled=not free, use_container_width=True
                )
                if clicked:
                    if picked:
                        chosen.remove(s["seat_id"])
                    elif len(chosen) >= MAX_SEATS:
                        st.session_state.seat_msg = f"You can select up to {MAX_SEATS} seats."
                    else:
                        chosen.append(s["seat_id"])
                    st.rerun()
        st.caption("Highlighted = your seat · ✕ = taken or held by someone else")

    with right:
        with st.container(border=True):
            names = [s["seat_no"] for s in seats if s["seat_id"] in chosen]
            names.sort(key=lambda n: (int(n[:-1]), n[-1]))
            st.write("**Your seats**")
            st.write(", ".join(names) if names else "None yet")
            st.write(f"Fare per seat: ৳ {flight['fare_per_seat']:,.0f}")
            st.write(f"**Total: ৳ {flight['fare_per_seat'] * len(chosen):,.0f}**")
            if not viewing:
                st.info("Your seats will be automatically released after 15 minutes. Please pay before it.")
            if viewing:
                st.caption("You are changing your held seats. The 15-minute timer does not restart.")
                if st.button("Update my seats", disabled=not chosen):
                    try:
                        with st.spinner("Updating your seats..."):
                            update_hold(user["id"], st.session_state.hold_id, fid, chosen)
                        st.session_state.chosen = []
                        st.session_state.view_seats = False
                        st.session_state.selected_flight = None
                        st.rerun()
                    except HoldError as e:
                        st.session_state.seat_msg = str(e)
                        st.rerun()
            elif st.button("Hold seats and continue", disabled=not chosen):
                try:
                    with st.spinner("Holding your seats..."):
                        hold_seats(user["id"], fid, chosen)
                    st.session_state.chosen = []
                    st.session_state.selected_flight = None
                    st.rerun()
                except HoldError as e:
                    st.session_state.seat_msg = str(e) + " The seat map has been refreshed."
                    st.rerun()

def hold_view(user, h):
    st.subheader("Your seats are on hold")
    with st.container(border=True):
        st.write(f"**Booking {h['booking_ref']}**")
        st.write(
            f"{h['flight_no']} · {h['airline']} · {h['origin']} → {h['dest']} · "
            f"{h['departure_time']:%d %b %Y, %H:%M}"
        )
        st.write(f"Seats: {', '.join(h['seats'])}")
        st.write(f"**Total: ৳ {h['total_amount']:,.0f}**")
        st.write(f"Your seats will automatically released at **{h['hold_expires_at'].strftime('%-I:%M %p')}**. Please pay before it.")
    st.info("Payment comes in the next slice. Until then you can release the seats.")


    b1, b2, _ = st.columns([1.7, 1.4, 2.5])
    if b1.button("← Back to seat map"):
        st.session_state.view_seats = True
        st.session_state.hold_id = h["booking_id"]
        st.session_state.chosen = list(h["seat_ids"])
        st.session_state.selected_flight = h["flight_id"]
        st.rerun()
    if b2.button("Release seats"):
        with st.spinner("Releasing seats..."):
            release_hold(h["booking_id"], user["id"])
        st.rerun()