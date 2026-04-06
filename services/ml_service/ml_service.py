from flask import Flask, request, jsonify
import pickle
import numpy as np

app = Flask(__name__)

# Load model
with open("model.pkl", "rb") as f:
    model = pickle.load(f)


@app.route("/predict", methods=["POST"])
def predict():
    data = request.json
    value = data.get("metric", 0)

    prediction = model.predict([[value]])

    result = "ANOMALY" if prediction[0] == -1 else "NORMAL"

    return jsonify({
        "input": value,
        "result": result
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=6000)