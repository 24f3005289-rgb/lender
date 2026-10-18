def calculate(question):
    question = question.lower()

    if "refund" in question:
        status_needed = "refunded"
    else:
        status_needed = "paid"

    # Which product/customer/region earned the most revenue?
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

    # Normal total revenue / refund / count questions
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
