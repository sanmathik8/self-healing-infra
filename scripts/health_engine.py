"""Self-Healing Infrastructure Health Check Engine.

Monitors Docker, containers, HTTP services, ports, processes, system resources,
and internet connectivity. Triggers Ansible playbooks on failure, verifies
recovery, and logs report data.
"""
import argparse
import json
import logging
import os
import socket
import subprocess
from datetime import datetime, timezone
import shutil

# Enable graceful fallback if docker or psutil are missing (e.g. during minimal test setup)
try:
    import docker
except ImportError:
    docker = None

try:
    import requests
except ImportError:
    requests = None

try:
    import psutil
except ImportError:
    psutil = None

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("health_engine")

CHECK_TIMEOUT_SECONDS = 10
REMEDIATION_LIMIT = 3

# ---------------------------------------------------------
# SRE Health Checks
# ---------------------------------------------------------

def check_docker_daemon():
    """1. Checks if the Docker daemon is responsive."""
    if not docker:
        return False, "Docker Python SDK not installed"
    try:
        client = docker.from_env()
        client.ping()
        return True, "Docker daemon is responding"
    except Exception as e:
        return False, f"Docker daemon unresponsive: {e}"


def check_container_status(container_name):
    """2. Checks if a specific container is running and healthy."""
    if not docker:
        return False, "Docker Python SDK not installed"
    try:
        client = docker.from_env()
        container = client.containers.get(container_name)
        state = container.attrs.get("State", {})
        status = state.get("Status", "unknown")
        
        if status == "running":
            health = state.get("Health", {}).get("Status", "none")
            if health == "unhealthy":
                return False, f"Container '{container_name}' is running but unhealthy"
            return True, f"Container '{container_name}' is running (health: {health})"
        return False, f"Container '{container_name}' is in status '{status}'"
    except Exception as e:
        return False, f"Container '{container_name}' status check failed: {e}"


def check_http_endpoint(name, url):
    """3. Checks if an HTTP endpoint returns a 200 OK status."""
    if not requests:
        return False, "requests library not installed"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            return True, f"Endpoint {name} is responsive (200 OK)"
        return False, f"Endpoint {name} returned status code {response.status_code}"
    except Exception as e:
        return False, f"Endpoint {name} check failed: {e}"


def check_disk_usage(threshold_percent=85):
    """4. Checks if disk usage is below a specified threshold."""
    if not psutil:
        # Fallback to shutil
        try:
            total, used, free = shutil.disk_usage("/")
            percent = (used / total) * 100
        except Exception as e:
            return False, f"Disk check fallback failed: {e}"
    else:
        try:
            percent = psutil.disk_usage("/").percent
        except Exception as e:
            return False, f"Disk check failed: {e}"
            
    if percent < threshold_percent:
        return True, f"Disk usage is at {percent:.1f}% (threshold {threshold_percent}%)"
    return False, f"Disk usage is high at {percent:.1f}% (threshold {threshold_percent}%)"


def check_memory_usage(threshold_percent=90):
    """5. Checks if memory usage is below a specified threshold."""
    if not psutil:
        return True, "psutil not installed, skipping memory check"
    try:
        percent = psutil.virtual_memory().percent
        if percent < threshold_percent:
            return True, f"Memory usage is at {percent:.1f}% (threshold {threshold_percent}%)"
        return False, f"Memory usage is high at {percent:.1f}% (threshold {threshold_percent}%)"
    except Exception as e:
        return False, f"Memory check failed: {e}"


def check_cpu_usage(threshold_percent=90):
    """6. Checks if CPU usage is below a specified threshold."""
    if not psutil:
        return True, "psutil not installed, skipping CPU check"
    try:
        percent = psutil.cpu_percent(interval=0.5)
        if percent < threshold_percent:
            return True, f"CPU usage is at {percent:.1f}% (threshold {threshold_percent}%)"
        return False, f"CPU usage is high at {percent:.1f}% (threshold {threshold_percent}%)"
    except Exception as e:
        return False, f"CPU check failed: {e}"


def check_internet_connectivity():
    """7. Checks external network connectivity."""
    try:
        # Connect to Cloudflare DNS IP
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)
        sock.connect(("1.1.1.1", 53))
        sock.close()
        return True, "Internet connectivity is functional"
    except Exception as e:
        return False, f"Internet connection failed: {e}"


def check_required_ports(host, port):
    """8. Checks if a specified port is open and listening."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex((host, port))
        sock.close()
        if result == 0:
            return True, f"Port {host}:{port} is listening"
        return False, f"Port {host}:{port} is NOT listening"
    except Exception as e:
        return False, f"Port check for {host}:{port} failed: {e}"


def check_required_process(container_name, process_name):
    """9. Checks if a required process is running inside a container."""
    if not docker:
        return False, "Docker Python SDK not installed"
    try:
        client = docker.from_env()
        container = client.containers.get(container_name)
        if container.status != "running":
            return False, f"Container '{container_name}' is not running, cannot check process"
        
        # Run pgrep inside the container
        exit_code, output = container.exec_run(["pgrep", "-f", process_name])
        if exit_code == 0:
            return True, f"Process '{process_name}' is running inside '{container_name}'"
        return False, f"Process '{process_name}' is NOT running inside '{container_name}'"
    except Exception as e:
        return False, f"Process check inside '{container_name}' failed: {e}"


# ---------------------------------------------------------
# SRE Execution Engine
# ---------------------------------------------------------

def execute_remediation(playbook_dir, target, action):
    """Executes the Ansible remediation playbook as a subprocess."""
    inventory = os.path.join(playbook_dir, "inventory.ini")
    playbook = os.path.join(playbook_dir, "playbooks", "remediation.yml")
    
    cmd = [
        "ansible-playbook",
        "-i", inventory,
        playbook,
        "--extra-vars", f"target={target} action={action}"
    ]
    
    logger.info("Executing SRE remediation: %s", " ".join(cmd))
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120
        )
        if result.returncode == 0:
            logger.info("Remediation execution completed successfully")
            return True, result.stdout
        else:
            logger.error("Remediation execution failed: %s", result.stderr)
            return False, result.stderr
    except Exception as e:
        logger.error("Error executing remediation subprocess: %s", e)
        return False, str(e)


def run_checks_and_heal(playbook_dir):
    """Iterates through all health checks, executing self-healing if needed."""
    # Define checks to execute
    checks = [
        {"name": "Docker Daemon", "fn": check_docker_daemon, "remediation": None},
        {"name": "Internet Connectivity", "fn": check_internet_connectivity, "remediation": None},
        {"name": "Demo App Container Status", "fn": lambda: check_container_status("demo-app"), "remediation": {"target": "demo-app", "action": "restart"}},
        {"name": "Prometheus Container Status", "fn": lambda: check_container_status("prometheus"), "remediation": {"target": "prometheus", "action": "restart"}},
        {"name": "Grafana Container Status", "fn": lambda: check_container_status("grafana"), "remediation": {"target": "grafana", "action": "restart"}},
        {"name": "Node Exporter Container Status", "fn": lambda: check_container_status("node-exporter"), "remediation": {"target": "node-exporter", "action": "restart"}},
        {"name": "Demo App Port Check", "fn": lambda: check_required_ports("demo-app", 80), "remediation": {"target": "demo-app", "action": "restart"}},
        {"name": "Prometheus Port Check", "fn": lambda: check_required_ports("prometheus", 9090), "remediation": {"target": "prometheus", "action": "restart"}},
        {"name": "Demo App HTTP Endpoint", "fn": lambda: check_http_endpoint("demo-app", "http://demo-app:80/"), "remediation": {"target": "demo-app", "action": "restart"}},
        {"name": "Prometheus HTTP Endpoint", "fn": lambda: check_http_endpoint("prometheus", "http://prometheus:9090/-/healthy"), "remediation": {"target": "prometheus", "action": "restart"}},
        {"name": "Demo App Nginx Process", "fn": lambda: check_required_process("demo-app", "nginx"), "remediation": {"target": "demo-app", "action": "restart"}},
        {"name": "Disk Space Check", "fn": check_disk_usage, "remediation": {"target": "demo-app", "action": "clear_logs"}},
        {"name": "Memory Usage Check", "fn": check_memory_usage, "remediation": None},
        {"name": "CPU Usage Check", "fn": check_cpu_usage, "remediation": None},
    ]

    results = []
    logger.info("Initializing SRE Health Checks...")

    for check in checks:
        name = check["name"]
        fn = check["fn"]
        remedy = check["remediation"]

        healthy, details = fn()
        if healthy:
            logger.info("Check '%s': HEALTHY — %s", name, details)
            results.append({
                "service": name,
                "status": "Healthy",
                "details": details,
                "action_taken": "None",
                "verification": "Passed"
            })
            continue

        # If unhealthy and no remediation defined
        if not remedy:
            logger.error("Check '%s': FAILED — %s (No auto-remediation defined)", name, details)
            results.append({
                "service": name,
                "status": "Failed",
                "details": details,
                "action_taken": "None",
                "verification": "Failed"
            })
            continue

        # Trigger auto-remediation
        logger.warning("Check '%s': FAILED — %s. Attempting auto-remediation...", name, details)
        
        target = remedy["target"]
        action = remedy["action"]
        
        success, output = execute_remediation(playbook_dir, target, action)
        
        if success:
            # Verify recovery
            logger.info("Verifying recovery for '%s'...", name)
            recovered, recovery_details = fn()
            if recovered:
                logger.info("Check '%s': FIXED — Recovery verified: %s", name, recovery_details)
                results.append({
                    "service": name,
                    "status": "Fixed",
                    "details": details,
                    "action_taken": f"Ansible {action} on {target}",
                    "verification": f"Passed: {recovery_details}"
                })
                continue
            else:
                logger.error("Check '%s': FAILED — Recovery check failed after remediation", name)
                details = f"Remediation ran but recovery failed: {recovery_details}"
        else:
            logger.error("Check '%s': FAILED — Ansible remediation execution failed", name)
            details = f"Remediation playbook failed to run: {output}"

        results.append({
            "service": name,
            "status": "Failed",
            "details": details,
            "action_taken": f"Ansible {action} on {target}",
            "verification": "Failed"
        })

    return results


def summarize(results):
    total = len(results) or 1
    healthy = sum(1 for r in results if r["status"] == "Healthy")
    fixed = sum(1 for r in results if r["status"] == "Fixed")
    failed = sum(1 for r in results if r["status"] == "Failed")
    score = int(((healthy + fixed) / total) * 100)
    return healthy, fixed, failed, score


def save_json_report(results, report_dir):
    os.makedirs(report_dir, exist_ok=True)
    healthy, fixed, failed, score = summarize(results)
    
    report_data = {
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "health_score": score,
        "summary": {
            "healthy": healthy,
            "fixed": fixed,
            "failed": failed,
            "total": len(results)
        },
        "results": results
    }
    
    path = os.path.join(report_dir, "health_results.json")
    with open(path, "w") as f:
        json.dump(report_data, f, indent=2)
    return path


def main():
    parser = argparse.ArgumentParser(description="SRE Auto-Remediation Health Engine")
    parser.add_argument(
        "--report-dir",
        default=os.environ.get("HEALTH_REPORT_DIR", "reports"),
        help="Directory to write health reports (default: reports)"
    )
    parser.add_argument(
        "--ansible-dir",
        default="ansible",
        help="Directory containing Ansible configs and playbooks (default: ansible)"
    )
    args = parser.parse_args()

    results = run_checks_and_heal(args.ansible_dir)
    healthy, fixed, failed, score = summarize(results)

    logger.info("Run Summary — Healthy: %d | Fixed: %d | Failed: %d | Score: %d%%", healthy, fixed, failed, score)

    path = save_json_report(results, args.report_dir)
    logger.info("JSON report saved to %s", path)

    # Automatically generate HTML report if report generator is present
    try:
        from scripts.report import generate_html_report
        html_path = generate_html_report(results, args.report_dir)
        logger.info("HTML report saved to %s", html_path)
    except Exception as e:
        logger.warning("Could not auto-generate HTML report: %s", e)


if __name__ == "__main__":
    main()
