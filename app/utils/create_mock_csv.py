import csv
import random
from faker import Faker

fake = Faker()

# Provided data
base_products = [
    ("SW-NCI-ULT-FP", "Subscription, Nutanix Cloud Infrastructure (NCI) Ultimate Software License & Federal Production Software Support Service for 1 CPU Core 1 year"),
    ("SW-NCM-STR-FP", "Subscription, Nutanix Cloud Manager (NCM) Starter Software License & Federal Production Software Support Service for 1 CPU Core 1 year"),
    ("CNS-INF-A-SVC-DEP-STR", "Service, NCI Cluster Deployment or Expansion - Starter Edition. For each quantity purchased, deployment is limited to 1 node at a single physical site."),
    ("United States", "Selected region for Services Delivery"),
    ("AHV", "Nutanix AHV Hypervisor"),
    ("CNS-INF-A-SVC-DEP-STR", "Service, NCI Cluster Deployment or Expansion - Starter Edition. For each quantity purchased, deployment is limited to 1 node at a single physical site."),
    ("SW-NUS-PRO-FP", "Subscription, Nutanix Unified Storage (NUS) Pro Software License & Federal Production Software Support Service for 1 TiB of data stored 1 year"),
    ("CNS-INF-A-SVC-DEP-PRO", "Service, NCI Cluster Deployment or Expansion - Pro Edition. For each quantity purchased, deployment is limited to 1 node at a single physical site. Includes choice of one: NUS Files,"),
    ("SWA-NUS-SEC-FP", "Subscription, Nutanix Unified Storage (NUS) Security add-on Software License & Federal Production Software Support Service for 1 TiB of data stored 1 year"),
    ("U-MEM-64GB-32A1-CM", "Upgrade, Samsung 64GB Memory (3200MHz DDR4 RDIMM)"),
    ("S-HW-UPGRADE", "Hardware support for Upgrade part qualified for NX-core platform"),
    ("RS-HW-FED-PRD-MY", "24/7 Federal Production Level Multi Year HW Support Renewal for Nutanix HCI appliance 1 year"),
    ("RS-NRDK-SSD-3.84TB-MY", "Renewal support for non-returned 3.84TB SSD replacement (per drive) for multi-year 1 year"),
    ("RS-NRDK-HDD-18TB-MY", "Renewal Support for non-returned 18TB HDD replacement (per drive) for multi-year 1 year"),
    ("SWA-NUS-ADR-FP", "Subscription, Nutanix Unified Storage (NUS) Advanced Replication add-on Software License & Federal Production Software Support Service for 1 TiB of data stored 1 year"),
]

# Utility to categorize based on part number prefix
def get_category(part_number):
    if part_number.startswith("SW") or part_number.startswith("SWA"):
        return "software"
    elif part_number.startswith("RS") or part_number.startswith("U-") or part_number.startswith("S-") or part_number.startswith("CNS"):
        return "hardware"
    else:
        return "software" if random.random() < 0.5 else "hardware"



# Start with original 15 (excluding duplicates)
products = []
for part_number, name in base_products:
    products.append({
        "name": name,
        "part_number": part_number,
        "supplier_id": random.randint(1, 5),
        "category": get_category(part_number),
        "origin": "United States",
        "price": round(random.uniform(50.00, 5000.00), 2)
    })

# Generate 100 mock products
for _ in range(100):
    category = random.choice(["hardware", "software"])
    part_prefix = "SW" if category == "software" else "HW"
    part_number = f"{part_prefix}-{fake.lexify(text='??????').upper()}"
    name = fake.bs().capitalize()
    products.append({
        "name": name,
        "part_number": part_number,
        "supplier_id": random.randint(1, 5),
        "category": category,
        "origin": "United States",
        "price": round(random.uniform(50.00, 5000.00), 2)
    })

# Write to CSV
csv_path = "../samples/supplier_products.csv"
with open(csv_path, mode="w", newline="", encoding="utf-8") as file:
    writer = csv.DictWriter(file, fieldnames=["name", "part_number", "supplier_id", "category", "origin", "price"])
    writer.writeheader()
    writer.writerows(products)

csv_path
