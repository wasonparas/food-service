import os
import itertools
import requests
from flask import Flask, jsonify, request

app = Flask(__name__)
RESTAURANT_URL = os.getenv("RESTAURANT_URL", "http://restaurant-service:8080")
orders = []
ids = itertools.count(1001)

@app.get("/health")
def health():
    return jsonify(status="healthy", service="order-service")

@app.post("/orders")
def create_order():
    body = request.get_json(silent=True) or {}
    restaurant_id = body.get("restaurant_id")
    item = body.get("item")
    quantity = body.get("quantity", 1)

    if not isinstance(restaurant_id, int) or not item or not isinstance(quantity, int) or quantity < 1:
        return jsonify(error="restaurant_id (integer), item (string), and quantity (positive integer) are required"), 400

    try:
        response = requests.get(f"{RESTAURANT_URL}/restaurants/{restaurant_id}", timeout=3)
    except requests.RequestException:
        return jsonify(error="restaurant service unavailable"), 503
    if response.status_code == 404:
        return jsonify(error="unknown restaurant_id"), 400
    if response.status_code != 200:
        return jsonify(error="restaurant service error"), 502

    order = {
        "order_id": next(ids),
        "restaurant": response.json()["name"],
        "restaurant_id": restaurant_id,
        "item": item,
        "quantity": quantity,
        "status": "ACCEPTED",
    }
    orders.append(order)
    return jsonify(order), 201

@app.get("/orders")
def list_orders():
    return jsonify(orders)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
