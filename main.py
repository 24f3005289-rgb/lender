import re
import requests
from datetime import datetime
from zoneinfo import ZoneInfo
from fastapi import FastAPI, Request

app = FastAPI()

START_URL = "https://exam.sanand.workers.dev/questionData?email=24f3005289%40ds.study.iitm.ac.in&quizSign=mmJsNQVCEvaftGgrvPbniA2Teytbglg61CrAUbynIGyVasGXPyaXuL3QIjhGdAP9vz79OqcRrW1uAOljJ6YOV%2FL3DRm1R3buRvlTudd6fPWOAPLXAmGw4rh7jgkqSIt0EJeblT6p%2FD6nKCs8DHeWnlMEpFQPxKa3v0MJaEoDcUZPyj2C1exdBBtrvGxxMr5e3W4UTHc5fqXe1SzBz7EXRWSVl1KsvuoSwN%2BS3A2fIiF18Qp8bT8YyA0TT6fMnP1Jj85%2FGfXKNn5SzogHLOwmU5MGwyG4g7mWyTgM9h%2FmAIDka5UzbNdIZMEFvYSXesCI0TLHM8zEn1qehXvz08xvTQ%3D%3D&questionId=q-ledger-agent-server&path=%2Forders&page=1"

RATES_URL = "https://exam.sanand.workers.dev/questionData?email=24f3005289%40ds.study.iitm.ac.in&quizSign=mmJsNQVCEvaftGgrvPbniA2Teytbglg61CrAUbynIGyVasGXPyaXuL3QIjhGdAP9vz79OqcRrW1uAOljJ6YOV%2FL3DRm1R3buRvlTudd6fPWOAPLXAmGw4rh7jgkqSIt0EJeblT6p%2FD6nKCs8DHeWnlMEpFQPxKa3v0MJaEoDcUZPyj2C1exdBBtrvGxxMr5e3W4UTHc5fqXe1SzBz7EXRWSVl1KsvuoSwN%2BS3A2fIiF18Qp8bT8YyA0TT6fMnP1Jj85%2FGfXKNn5SzogHLOwmU5MGwyG4g7mWyTgM9h%2FmAIDka5UzbNdIZMEFvYSXesCI0TLHM8zEn1qehXvz08xvTQ%3D%3D&questionId=q-ledger-agent-server&path=%2Frates"

IST = ZoneInfo("Asia/Kolkata")

orders = []
usd_per_unit = {}


def load_rates():
    global usd_per_unit
    response = requests.get(RATES_URL, timeout=20)
    response.raise_for_status()
    usd_per_unit = response.json()["usd_per_unit"]


def load_orders():
    global orders

    url = START_URL
    seen = set()
    latest = {}

    while url:
        response = requests.get(url, timeout=20)
        response.raise_for_status()
        data = response.json()

        for order in data.get("orders", []):
            order_id = order["id"]

            if (
                order_id not in latest
                or order["updated_at"] > latest[order_id]["updated_at"]
            ):
                latest[order_id] = order

        next_url = data.get("next")

        if not next_url or next_url in seen:
            break

        seen.add(next_url)
        url = next_url

    orders = list(latest.values())


load_rates()
load_orders()


def to_usd(order):
    currency = order.get("currency", "USD")
    amount = float(order.get("amount", 0) or 0)
    rate = float(usd_per_unit.get(currency, 1))
    return amount * rate


def get_date(order):
    value = order["created_at"].replace("Z", "+00:00")
    return datetime.fromisoformat(value).astimezone(IST)


def matches(order, question):
    question = question.lower()
    date = get_date(order)

    year = re.search(r"\b(20\d{2})\b", question)
    if year and date.year != int(year.group(1)):
        return False

    months = {
        "january": 1, "february": 2, "march": 3, "april": 4,
        "may": 5, "june": 6, "july": 7, "august": 8,
        "september": 9, "october": 10, "november": 11, "december": 12
    }

    for month_name, month_number in months.items():
        if month_name in question and date.month != month_number:
            return False

    region = str(order.get("region", "")).lower()
    product = str(order.get("product", "")).lower()
    customer = str(order.get("customer", "")).lower()

    if region and region in question:
        return True

    if product and product in question:
        return True

    if customer and customer in question:
        return True

    return True


def calculate(question):
    question = question.lower()

    if "refund" in question:
        status_needed = "refunded"
    else:
        status_needed = "paid"

    group_field = None

    if "which product" in question or "top product" in question or "best product" in question:
        group_field = "product"
    elif "which customer" in question or "top customer" in question or "best customer" in question:
        group_field = "customer"
    elif "which region" in question or "top region" in question or "best region" in question:
        group_field = "region"

    if group_field:
        totals = {}

        for order in orders:
            if order.get("status") != "paid":
                continue

            if not matches(order, question):
                continue

            name = str(order.get(group_field, ""))
            totals[name] = totals.get(name, 0) + to_usd(order)

        if not totals:
            return ""

        return max(totals, key=totals.get)

    total = 0.0
    count = 0

    for order in orders:
        if order.get("status") != status_needed:
            continue

        if not matches(order, question):
            continue

        total += to_usd(order)
        count += 1

    if "how many" in question or "number of" in question:
        return count

    return round(total, 2)


@app.post("/")
async def answer_question(request: Request):
    body = await request.json()
    question = body.get("question", "")
    return {"answer": calculate(question)}
