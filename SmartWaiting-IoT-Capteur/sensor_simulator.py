import random
import csv
import os
import json
import urllib.request
from datetime import datetime

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000/api/occupancy/")

NB_CHAIRS = 25
CSV_FILE = "data/occupancy_history.csv"

os.makedirs("data", exist_ok=True)

occupied_count = 0

for chair_id in range(1, NB_CHAIRS + 1):

    occupied = random.choice([True, False])

    if occupied:
        occupied_count += 1

free_count = NB_CHAIRS - occupied_count

occupancy_rate = round(
    occupied_count / NB_CHAIRS * 100,
    2
)

patient_position = occupied_count + 1

timestamp = datetime.now().strftime(
    "%Y-%m-%d %H:%M:%S"
)

file_exists = os.path.isfile(CSV_FILE)

with open(
        CSV_FILE,
        mode="a",
        newline="",
        encoding="utf-8"
) as file:

    writer = csv.writer(file)

    if not file_exists:
        writer.writerow([
            "timestamp",
            "occupied_chairs",
            "free_chairs",
            "occupancy_rate",
            "patient_position"
        ])

    writer.writerow([
        timestamp,
        occupied_count,
        free_count,
        occupancy_rate,
        patient_position
    ])

current_state = {
    "room_id": "salle_attente_1",
    "timestamp": timestamp,
    "total_chairs": NB_CHAIRS,
    "occupied_chairs": occupied_count,
    "free_chairs": free_count,
    "occupancy_rate": occupancy_rate,
    "patient_position": patient_position
}

with open(
    "data/current_state.json",
    "w",
    encoding="utf-8"
) as file:
    json.dump(
        current_state,
        file,
        indent=4,
        ensure_ascii=False
    )

try:
    data = json.dumps(current_state).encode("utf-8")
    req = urllib.request.Request(
        BACKEND_URL,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=5) as response:
        print(f"\nDonnées envoyées au back-end ({response.status})")
except Exception as e:
    print(f"\nBack-end non joignable : {e}")

print("\n=== SMARTWAITING IoT ===")

print(f"Occupées : {occupied_count}")
print(f"Libres : {free_count}")
print(f"Taux occupation : {occupancy_rate}%")
print(f"Position patient : {patient_position}")

print("\nHistorique enregistré dans :")
print(CSV_FILE)
print("\nEtat actuel enregistré dans :")
print("data/current_state.json")
