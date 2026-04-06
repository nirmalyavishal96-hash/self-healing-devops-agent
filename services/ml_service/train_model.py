import numpy as np
import pickle
from sklearn.ensemble import IsolationForest

# TRAIN WITH REALISTIC LOCAL RANGE
# observed values ≈ 0.1 to 1

data = np.random.normal(loc=0.3, scale=0.1, size=(1000, 1))

# Train model
model = IsolationForest(contamination=0.05)
model.fit(data)

# Save model
with open("model.pkl", "wb") as f:
    pickle.dump(model, f)

print("Model trained with realistic baseline!")