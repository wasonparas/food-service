from flask import Flask, jsonify
app = Flask(__name__)

RESTAURANTS = [
    {"id": 1, "name": "Kiwi Kitchen", "cuisine": "New Zealand"},
    {"id": 2, "name": "Taco Town", "cuisine": "Mexican"},
    {"id": 3, "name": "Noodle House", "cuisine": "Asian"},
]

@app.get("/health")
def health():
    return jsonify(status="healthy", service="restaurant-service")

@app.get("/restaurants")
def restaurants():
    return jsonify(RESTAURANTS)

@app.get("/restaurants/<int:restaurant_id>")
def restaurant(restaurant_id):
    item = next((r for r in RESTAURANTS if r["id"] == restaurant_id), None)
    if item is None:
        return jsonify(error="restaurant not found"), 404
    return jsonify(item)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
