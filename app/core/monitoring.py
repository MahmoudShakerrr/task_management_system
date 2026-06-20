from time import time

monitoring_data = {
    "total_requests": 0,
    "error_count": 0,
    "request_times": [],
    "recent_requests": [],
    "recent_errors": []
}


def log_request(endpoint: str, status_code: int, duration: float):
    monitoring_data["total_requests"] += 1
    monitoring_data["request_times"].append(duration)

    # حفظ آخر 10 requests
    monitoring_data["recent_requests"].append({
        "endpoint": endpoint,
        "status_code": status_code,
        "response_time": duration
    })

    monitoring_data["recent_requests"] = monitoring_data["recent_requests"][-10:]

    # لو error
    if status_code >= 400:
        monitoring_data["error_count"] += 1

        monitoring_data["recent_errors"].append({
            "endpoint": endpoint,
            "status_code": status_code,
            "time": duration
        })

        monitoring_data["recent_errors"] = monitoring_data["recent_errors"][-10:]


def get_monitoring():
    avg_time = (
        sum(monitoring_data["request_times"]) / len(monitoring_data["request_times"])
        if monitoring_data["request_times"] else 0
    )

    error_rate = (
        (monitoring_data["error_count"] / monitoring_data["total_requests"]) * 100
        if monitoring_data["total_requests"] else 0
    )

    return {
        "total_requests": monitoring_data["total_requests"],
        "error_count": monitoring_data["error_count"],
        "error_rate": f"{error_rate:.2f}%",
        "average_response_time": avg_time,
        "recent_requests": monitoring_data["recent_requests"],
        "recent_errors": monitoring_data["recent_errors"],
        "health_status": "OK"
    }


def reset_monitoring():
    monitoring_data["total_requests"] = 0
    monitoring_data["error_count"] = 0
    monitoring_data["request_times"] = []
    monitoring_data["recent_requests"] = []
    monitoring_data["recent_errors"] = []