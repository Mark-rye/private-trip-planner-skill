#!/usr/bin/env python3
"""Validate trip data and render a responsive, self-contained itinerary shell."""

from __future__ import annotations

import argparse
import html
import json
import sys
import math
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path


MODES = {"walk", "transit", "drive", "bike", "ferry", "train", "flight", "other"}
STATUSES = {"verified", "schematic"}
COMPLETE_MODULES = {"route", "overview", "highlights", "accommodation", "restaurants", "transport", "cost_estimate", "booking_dashboard", "budget_report", "practical", "sources"}


def fail(message: str) -> None:
    raise ValueError(message)


def validate(data: dict) -> None:
    if not isinstance(data, dict):
        fail("trip data must be an object")
    if not isinstance(data.get("title"), str) or not data["title"].strip():
        fail("title must be a non-empty string")
    days = data.get("days")
    if not isinstance(days, list) or not days:
        fail("days must be a non-empty list")
    seen_days = set()
    for day in days:
        number = day.get("day")
        if not isinstance(number, int) or number < 1 or number in seen_days:
            fail("each day must have a unique positive integer day")
        seen_days.add(number)
        stops = day.get("stops")
        if not isinstance(stops, list) or not stops:
            fail(f"day {number} must contain at least one stop")
        orders = set()
        for stop in stops:
            order = stop.get("order")
            lat, lng = stop.get("lat"), stop.get("lng")
            if not isinstance(order, int) or order < 1 or order in orders:
                fail(f"day {number} stop order must be a unique positive integer")
            orders.add(order)
            if not isinstance(stop.get("name"), str) or not stop["name"].strip():
                fail(f"day {number} stop {order} needs a name")
            if type(lat) not in (int, float) or not math.isfinite(lat) or not -90 <= lat <= 90:
                fail(f"day {number} stop {order} has invalid latitude")
            if type(lng) not in (int, float) or not math.isfinite(lng) or not -180 <= lng <= 180:
                fail(f"day {number} stop {order} has invalid longitude")
        for leg in day.get("legs", []):
            if leg.get("from") not in orders or leg.get("to") not in orders:
                fail(f"day {number} leg references an unknown stop")
            if leg.get("mode", "other") not in MODES:
                fail(f"day {number} leg has unsupported mode")
            status = leg.get("geometry_status", "schematic")
            if status not in STATUSES:
                fail(f"day {number} leg has unsupported geometry_status")
            geometry = leg.get("geometry")
            if status == "verified" and (not isinstance(geometry, list) or len(geometry) < 2):
                fail(f"day {number} verified leg needs route geometry")
            if status == "verified" and not leg.get("source_url"):
                fail(f"day {number} verified leg needs source_url")
            for key in ("duration_min", "distance_km", "available_min", "transfer_min", "buffer_min"):
                value = leg.get(key)
                if value is not None and (type(value) not in (int, float) or not math.isfinite(value) or value < 0):
                    fail(f"day {number} {key} must be a finite non-negative number")
            if leg.get("available_min") is not None:
                needed = leg.get("transfer_min", 0) + leg.get("buffer_min", 0)
                if leg["available_min"] < needed:
                    fail(f"day {number} connection is infeasible: needs {needed} min, has {leg['available_min']} min")
    bookings = data.get("bookings", [])
    if not isinstance(bookings, list):
        fail("bookings must be a list")
    ids = set()
    for booking in bookings:
        if not isinstance(booking.get("id"), str) or not booking["id"] or booking["id"] in ids:
            fail("bookings need unique non-empty string ids")
        ids.add(booking["id"])
        if booking.get("status") not in {"booked", "pending", "optional", "cancelled"}:
            fail("booking status must be booked, pending, optional or cancelled")
        for key in ("amount", "exchange_rate"):
            value = booking.get(key)
            if value is not None and (type(value) not in (int, float) or not math.isfinite(value) or value < 0):
                fail(f"booking {key} must be a finite non-negative number")
        if booking.get("exchange_rate") == 0:
            fail("exchange_rate must be positive")
        if "paid" in booking and type(booking["paid"]) is not bool:
            fail("paid must be a boolean")
        if booking.get("day") is not None and booking["day"] not in seen_days:
            fail("booking day must reference an existing day")
    by_id = {b["id"]: b for b in bookings}
    for booking in bookings:
        parent = booking.get("included_in")
        visited = {booking["id"]}
        while parent:
            if parent not in by_id or parent in visited:
                fail("included_in must reference a valid package without cycles")
            visited.add(parent)
            parent = by_id[parent].get("included_in")
    for day in days:
        if any(ref not in ids for ref in day.get("booking_ids", [])):
            fail("booking_ids must reference existing bookings")
    if "travelers" in data and (type(data["travelers"]) is not int or data["travelers"] < 1):
        fail("travelers must be a positive integer")
    sections = data.get("guide_sections", [])
    if not isinstance(sections, list):
        fail("guide_sections must be a list")
    for section in sections:
        if not isinstance(section, dict) or not section.get("id") or not section.get("title"):
            fail("guide sections need id and title")
        if not section.get("paragraphs") and not section.get("cards"):
            fail("guide section must contain written content, not only a heading")
    if len({s["id"] for s in sections}) != len(sections):
        fail("guide section ids must be unique")
    if data.get("detail_level") == "complete":
        missing = COMPLETE_MODULES - {s["id"] for s in sections}
        if missing:
            fail("complete guide missing modules: " + ", ".join(sorted(missing)))
        for day in days:
            for field in ("summary", "stay", "meals", "highlights", "culture", "warnings", "alternative"):
                if not day.get(field):
                    fail(f"complete guide day {day['day']} missing {field}")


def booking_summary(data: dict) -> dict:
    """Compute counts and known costs once; options and included costs stay separate."""
    base = data.get("base_currency", "CNY")
    current = [b for b in data.get("bookings", []) if b["status"] in {"booked", "pending"} and not b.get("included_in")]
    totals = {"booked": Decimal(0), "pending": Decimal(0), "paid": Decimal(0)}
    missing = []
    for item in current:
        if item.get("included_in"):
            continue
        amount = item.get("amount")
        rate = 1 if item.get("currency", base) == base else item.get("exchange_rate")
        if amount is None or rate is None:
            missing.append(item["name"] if item.get("name") else item["id"])
            continue
        cost = Decimal(str(amount)) * Decimal(str(rate))
        totals[item["status"]] += cost
        if item.get("paid"):
            totals["paid"] += cost
    total = totals["booked"] + totals["pending"]
    money = lambda value: format(value.quantize(Decimal(".01"), rounding=ROUND_HALF_UP), "f")
    return {
        "currency": base,
        "booked_count": sum(b["status"] == "booked" for b in current),
        "pending_count": sum(b["status"] == "pending" for b in current),
        "total_count": len(current),
        "known_total": money(total),
        "known_booked": money(totals["booked"]),
        "known_pending": money(totals["pending"]),
        "known_paid": money(totals["paid"]),
        "per_person": money(total / data["travelers"]) if data.get("travelers") else None,
        "missing_prices": missing,
    }


def render(data: dict, template: Path) -> str:
    data = dict(data, booking_summary=booking_summary(data))
    payload = json.dumps(data, ensure_ascii=False, allow_nan=False).replace("<", "\\u003c")
    page = template.read_text(encoding="utf-8")
    return page.replace("__TRIP_TITLE__", html.escape(data["title"])).replace("__TRIP_DATA__", payload)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    data = json.loads(args.input.read_text(encoding="utf-8"))
    validate(data)
    if args.validate_only:
        print("trip data is valid")
        return 0
    if not args.output:
        fail("--output is required unless --validate-only is used")
    template = Path(__file__).resolve().parent.parent / "assets" / "map-template.html"
    args.output.write_text(render(data, template), encoding="utf-8")
    print(f"rendered {args.output}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(2)
