import pandas as pd
import os
import joblib

from sklearn.model_selection import train_test_split
from sklearn.tree import DecisionTreeClassifier
from sklearn.metrics import accuracy_score, classification_report

# Load dataset
data = pd.read_csv("dataset/student_data.csv")

print("Dataset Loaded Successfully!")
print("Total Records:", len(data))

# Input and output
X = data[["attendance", "study_hours", "previous_marks", "internal_marks"]]
y = data["performance"]

# Split dataset
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

# Train model
model = DecisionTreeClassifier(random_state=42)
model.fit(X_train, y_train)

# Prediction
predictions = model.predict(X_test)

# Accuracy
accuracy = accuracy_score(y_test, predictions)

print("\nModel Training Completed!")
print("Model Accuracy:", round(accuracy * 100, 2), "%")

print("\nClassification Report:")
print(classification_report(y_test, predictions))

# Save model
os.makedirs("models", exist_ok=True)
joblib.dump(model, "models/student_model.pkl")

print("\nModel saved successfully!")
