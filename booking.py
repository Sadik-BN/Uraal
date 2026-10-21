import time
import functools
import mysql.connector
from db import get_conn, fetch_all


class HoldError(Exception):
    pass

def retry(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        for attempt in range(3):
            try:
                return func(*args, **kwargs)
            except mysql.connector.errors.DatabaseError as e:
                if e.errno in (1213, 1205) and attempt < 2:
                    time.sleep(0.2 * (attempt + 1))
                    continue
                raise
    return wrapper

@retry
def hold_seats(user_id, flight_id, seat_ids):
    seat_ids = sorted(seat_ids)
    marks = ", ".join(["%s"] * len(seat_ids))
    conn = get_conn()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute(
            "SELECT fare_per_seat, status, "
            "departure_time > DATE_ADD(NOW(), INTERVAL 1 HOUR) AS can_book "
            "FROM flights WHERE flight_id = %s",
            (flight_id,)
        )
        f = cur.fetchone()
        if not f or f["status"] != "ACTIVE":
            raise HoldError("This flight is not available.")
        if not f["can_book"]:
            raise HoldError("Booking closes 1 hour before departure.")

        cur.execute(
            "SELECT COUNT(*) AS n FROM bookings "
            "WHERE user_id = %s AND status = 'HELD' AND hold_expires_at > NOW()",
            (user_id,)
        )
        if cur.fetchone()["n"] > 0:
            raise HoldError("You already have seats on hold.")

        cur.execute(
            f"SELECT seat_id, status FROM seats WHERE flight_id = %s AND seat_id IN ({marks}) "
            "ORDER BY seat_id FOR UPDATE",
            (flight_id, *seat_ids)
        )
        rows = cur.fetchall()
        if len(rows) != len(seat_ids) or any(r["status"] != "AVAILABLE" for r in rows):
            raise HoldError("One of the seats is not available.")

        total = f["fare_per_seat"] * len(seat_ids)
        cur.execute(
            "INSERT INTO bookings (user_id, flight_id, total_amount, status, hold_expires_at) "
            "VALUES (%s, %s, %s, 'HELD', DATE_ADD(NOW(), INTERVAL 15 MINUTE))",
            (user_id, flight_id, total)
        )
        booking_id = cur.lastrowid
        cur.executemany(
            "INSERT INTO booking_seats (booking_id, seat_id) VALUES (%s, %s)",
            [(booking_id, s) for s in seat_ids]
        )
        cur.execute(f"UPDATE seats SET status = 'HELD' WHERE seat_id IN ({marks})", tuple(seat_ids))
        cur.execute(
            "UPDATE bookings SET booking_ref = "
            "CONCAT('BK-', REPLACE(DATE(created_at), '-', ''), '-', LPAD(booking_id, 3, '0')) "
            "WHERE booking_id = %s",
            (booking_id,)
        )
        conn.commit()
        return booking_id
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()

@retry
def expire_old_holds():
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            "UPDATE seats s "
            "JOIN booking_seats bs ON bs.seat_id = s.seat_id "
            "JOIN bookings b ON b.booking_id = bs.booking_id "
            "SET s.status = 'AVAILABLE' "
            "WHERE (b.status = 'HELD' AND b.hold_expires_at < NOW()) "
            "OR (b.status = 'RECHECK' AND b.recheck_deadline < NOW())"
        )
        cur.execute(
            "UPDATE bookings SET status = 'EXPIRED' "
            "WHERE (status = 'HELD' AND hold_expires_at < NOW()) "
            "OR (status = 'RECHECK' AND recheck_deadline < NOW())"
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


def active_hold(user_id):
    rows = fetch_all(
        "SELECT b.booking_id, b.booking_ref, b.total_amount, b.flight_id, b.hold_expires_at, "
        "TIMESTAMPDIFF(SECOND, NOW(), b.hold_expires_at) AS secs_left, "
        "f.flight_no, f.airline, f.departure_time, o.code AS origin, d.code AS dest "
        "FROM bookings b "
        "JOIN flights f ON f.flight_id = b.flight_id "
        "JOIN airports o ON o.airport_id = f.origin_id "
        "JOIN airports d ON d.airport_id = f.dest_id "
        "WHERE b.user_id = %s AND b.status = 'HELD' AND b.hold_expires_at > NOW()",
        (user_id,)
    )
    if not rows:
        return None
    h = rows[0]
    seats = fetch_all(
        "SELECT s.seat_id, s.seat_no FROM booking_seats bs JOIN seats s ON s.seat_id = bs.seat_id "
        "WHERE bs.booking_id = %s",
        (h["booking_id"],)
    )
    names = [s["seat_no"] for s in seats]
    names.sort(key=lambda n: (int(n[:-1]), n[-1]))
    h["seats"] = names
    h["seat_ids"] = [s["seat_id"] for s in seats]
    return h


@retry
def release_hold(booking_id, user_id):
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            "UPDATE seats s "
            "JOIN booking_seats bs ON bs.seat_id = s.seat_id "
            "JOIN bookings b ON b.booking_id = bs.booking_id "
            "SET s.status = 'AVAILABLE' "
            "WHERE b.booking_id = %s AND b.user_id = %s AND b.status = 'HELD'",
            (booking_id, user_id)
        )
        cur.execute(
            "UPDATE bookings SET status = 'CANCELLED', cancel_reason = 'Seats released by user', "
            "cancelled_at = NOW() "
            "WHERE booking_id = %s AND user_id = %s AND status = 'HELD'",
            (booking_id, user_id)
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()

@retry
def update_hold(user_id, booking_id, flight_id, seat_ids):
    seat_ids = sorted(set(seat_ids))
    if not seat_ids or len(seat_ids) > 4:
        raise HoldError("Choose 1 to 4 seats.")
    marks = ", ".join(["%s"] * len(seat_ids))
    conn = get_conn()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute(
            "SELECT b.status, b.hold_expires_at > NOW() AS alive, f.fare_per_seat, "
            "f.departure_time > DATE_ADD(NOW(), INTERVAL 1 HOUR) AS can_book "
            "FROM bookings b JOIN flights f ON f.flight_id = b.flight_id "
            "WHERE b.booking_id = %s AND b.user_id = %s AND b.flight_id = %s FOR UPDATE",
            (booking_id, user_id, flight_id)
        )
        b = cur.fetchone()
        if not b or b["status"] != "HELD" or not b["alive"]:
            raise HoldError("Your hold has expired. Please choose seats again.")
        if not b["can_book"]:
            raise HoldError("Booking closes 1 hour before departure.")

        cur.execute("SELECT seat_id FROM booking_seats WHERE booking_id = %s", (booking_id,))
        old = {r["seat_id"] for r in cur.fetchall()}
        new = set(seat_ids)

        cur.execute(
            f"SELECT seat_id, status FROM seats WHERE flight_id = %s AND "
            f"(seat_id IN ({marks}) OR seat_id IN (SELECT seat_id FROM booking_seats WHERE booking_id = %s)) "
            "ORDER BY seat_id FOR UPDATE",
            (flight_id, *seat_ids, booking_id)
        )
        status = {r["seat_id"]: r["status"] for r in cur.fetchall()}
        for s in new - old:
            if status.get(s) != "AVAILABLE":
                raise HoldError("Sorry, one of the new seats was just taken. Please choose again.")

        drop = sorted(old - new)
        add = sorted(new - old)
        if drop:
            m = ", ".join(["%s"] * len(drop))
            cur.execute(f"UPDATE seats SET status = 'AVAILABLE' WHERE seat_id IN ({m})", tuple(drop))
            cur.execute(
                f"DELETE FROM booking_seats WHERE booking_id = %s AND seat_id IN ({m})",
                (booking_id, *drop)
            )
        if add:
            m = ", ".join(["%s"] * len(add))
            cur.executemany(
                "INSERT INTO booking_seats (booking_id, seat_id) VALUES (%s, %s)",
                [(booking_id, s) for s in add]
            )
            cur.execute(f"UPDATE seats SET status = 'HELD' WHERE seat_id IN ({m})", tuple(add))

        cur.execute(
            "UPDATE bookings SET total_amount = %s WHERE booking_id = %s",
            (b["fare_per_seat"] * len(new), booking_id)
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()

@retry
def cancel_flight(flight_id):
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            "UPDATE flights SET status = 'CANCELLED' WHERE flight_id = %s AND status = 'ACTIVE'",
            (flight_id,)
        )
        cur.execute(
            "UPDATE bookings SET status = 'FLIGHT_CANCELLED' "
            "WHERE flight_id = %s AND status IN ('HELD', 'PENDING', 'CONFIRMED', 'RECHECK')",
            (flight_id,)
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


MIN_RECHECK_MIN = 30


class PayError(Exception):
    pass


@retry
def submit_payment(user_id, booking_id, txn_id):
    txn_id = txn_id.strip().upper()
    if not txn_id.isalnum() or not 8 <= len(txn_id) <= 14:
        raise PayError("Enter a valid transaction ID (8 to 14 letters or numbers).")
    conn = get_conn()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute(
            "SELECT b.status, "
            "b.hold_expires_at > NOW() AS hold_alive, "
            "b.recheck_deadline > NOW() AS recheck_alive, "
            "f.departure_time > DATE_ADD(NOW(), INTERVAL 1 HOUR) AS can_book "
            "FROM bookings b JOIN flights f ON f.flight_id = b.flight_id "
            "WHERE b.booking_id = %s AND b.user_id = %s FOR UPDATE",
            (booking_id, user_id)
        )
        b = cur.fetchone()
        if not b:
            raise PayError("Booking not found.")
        if b["status"] == "HELD" and b["hold_alive"]:
            if not b["can_book"]:
                raise PayError("Booking closes 1 hour before departure.")
        elif b["status"] == "RECHECK" and b["recheck_alive"]:
            pass
        else:
            raise PayError("This booking can no longer accept a payment.")

        cur.execute("SELECT COALESCE(MAX(attempt_no), 0) + 1 AS n FROM payments WHERE booking_id = %s", (booking_id,))
        attempt = cur.fetchone()["n"]
        try:
            cur.execute(
                "INSERT INTO payments (booking_id, txn_id, attempt_no) VALUES (%s, %s, %s)",
                (booking_id, txn_id, attempt)
            )
        except mysql.connector.IntegrityError:
            raise PayError("This transaction ID has already been used.")
        cur.execute(
            "UPDATE bookings SET status = 'PENDING', hold_expires_at = NULL, recheck_deadline = NULL "
            "WHERE booking_id = %s",
            (booking_id,)
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


@retry
def confirm_payment(admin_id, payment_id):
    conn = get_conn()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute(
            "SELECT p.booking_id, p.status AS pstatus, b.status AS bstatus "
            "FROM payments p JOIN bookings b ON b.booking_id = p.booking_id "
            "WHERE p.payment_id = %s FOR UPDATE",
            (payment_id,)
        )
        r = cur.fetchone()
        if not r or r["pstatus"] != "PENDING" or r["bstatus"] != "PENDING":
            raise PayError("This payment is no longer pending.")
        bid = r["booking_id"]
        cur.execute(
            "UPDATE payments SET status = 'CONFIRMED', verified_by = %s, verified_at = NOW() "
            "WHERE payment_id = %s",
            (admin_id, payment_id)
        )
        cur.execute("UPDATE bookings SET status = 'CONFIRMED' WHERE booking_id = %s", (bid,))
        cur.execute(
            "UPDATE seats s JOIN booking_seats bs ON bs.seat_id = s.seat_id "
            "SET s.status = 'BOOKED' WHERE bs.booking_id = %s",
            (bid,)
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


@retry
def reject_payment(admin_id, payment_id, message, hours=24, release=False):
    conn = get_conn()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute(
            "SELECT p.booking_id, p.status AS pstatus, b.status AS bstatus, "
            "TIMESTAMPDIFF(MINUTE, NOW(), DATE_SUB(f.departure_time, INTERVAL 1 HOUR)) AS room "
            "FROM payments p "
            "JOIN bookings b ON b.booking_id = p.booking_id "
            "JOIN flights f ON f.flight_id = b.flight_id "
            "WHERE p.payment_id = %s FOR UPDATE",
            (payment_id,)
        )
        r = cur.fetchone()
        if not r or r["pstatus"] != "PENDING" or r["bstatus"] != "PENDING":
            raise PayError("This payment is no longer pending.")
        bid = r["booking_id"]
        cur.execute(
            "UPDATE payments SET status = 'REJECTED', admin_message = %s, "
            "verified_by = %s, verified_at = NOW() WHERE payment_id = %s",
            (message[:300], admin_id, payment_id)
        )
        if release or r["room"] < MIN_RECHECK_MIN:
            cur.execute(
                "UPDATE seats s JOIN booking_seats bs ON bs.seat_id = s.seat_id "
                "SET s.status = 'AVAILABLE' WHERE bs.booking_id = %s",
                (bid,)
            )
            cur.execute(
                "UPDATE bookings SET status = 'REJECTED', cancel_reason = %s, cancelled_at = NOW() "
                "WHERE booking_id = %s",
                (message[:200], bid)
            )
        else:
            cur.execute(
                "UPDATE bookings b JOIN flights f ON f.flight_id = b.flight_id "
                "SET b.status = 'RECHECK', "
                "b.recheck_deadline = LEAST(DATE_ADD(NOW(), INTERVAL %s HOUR), "
                "DATE_SUB(f.departure_time, INTERVAL 1 HOUR)) "
                "WHERE b.booking_id = %s",
                (int(hours), bid)
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()