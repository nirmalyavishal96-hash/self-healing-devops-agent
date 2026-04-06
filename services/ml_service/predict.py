import pickle
import numpy as np

# Load model
with open("/app/model.pkl", "rb") as f:
    model = pickle.load(f)


def predict(value):
    data = np.array([[value]])
    result = model.predict(data)

    # -1 = anomaly, 1 = normal
    return "ANOMALY" if result[0] == -1 else "NORMAL"