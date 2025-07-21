
def small_test_disturbances(): 
    disturbances = []

    disturbances.append({
        "ID": 1,
        "type": "train malfunction",
        "time": "2024-06-01T08:15:00",
        "description": "Emergency Brake Activation"
    })
    disturbances.append({
        "ID": 2,
        "type": "infrastructure malfunction",
        "time": "2024-06-01T09:30:00",
        "description": "Faulty Signal"
    })
    disturbances.append({
        "ID": 3,
        "type": "Maintenance",
        "time": "2024-06-01T11:00:00",
        "description": "track maintenance"
    })
    return disturbances