# 🔧 SRE Self-Healing Infrastructure

An  **DevOps project** demonstrating automated infrastructure health monitoring, containerized service checking, Ansible-driven auto-remediation, and compliance reporting.

This project implements a container-native **watchbot** that monitors a local microservice stack, detects failures, runs targeted Ansible playbooks to recover stopped or degraded services, and generates JSON + HTML compliance dashboards.

---

## 🏗️ Architecture

The infrastructure runs entirely inside a Docker Compose network:

```
                    Docker Compose
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
        ▼                  ▼                  ▼
     Demo App         Prometheus         Grafana
  (nginx:alpine)     (Observability)   (Visualization)
        │
        ▼
 Health Engine (Custom Python Service)
        │
        ├── [1] Detect Failure (Via Docker socket, HTTP requests, port sockets, processes, resources)
        │
        ├── [2] Execute Ansible (Subprocess call to remediation.yml)
        │
        ├── [3] Verify Recovery (Re-run checking function)
        │
        └── [4] Report Generation (Writes JSON and HTML status panel)
```

### Key SRE Component Specifications:
* **Demo App**: A lightweight official Nginx container serving a web page and exposing metrics.
* **Observability Stack**: Official Prometheus and Grafana instances configured to scrape metrics from the container network and display dashboards.
* **Health Engine**: A custom Python container that mounts `/var/run/docker.sock` to inspect container health state directly, execute commands inside containers, and run local Ansible commands.

---

## 🩺 Supported Health Checks

The Python engine runs **9 distinct infrastructure health checks**:
1. **Docker Daemon**: Verifies daemon availability and socket responsiveness.
2. **Container Status**: Queries the Docker API to verify if target containers (`demo-app`, `prometheus`, `grafana`, `node-exporter`) are `running` and `healthy`.
3. **HTTP Endpoint Availability**: Makes HTTP requests to target ports (e.g. `demo-app` port 80 and `prometheus` port 9090) verifying `200 OK` status codes.
4. **Disk Usage**: Inspects system disk space percentage against a configurable warning threshold (default 85%).
5. **Memory Usage**: Monitors memory load using python `psutil`.
6. **CPU Usage**: Tracks CPU usage percentage over interval windows.
7. **Internet Connectivity**: Performs socket connections to a public DNS (`1.1.1.1:53`) to check external routing.
8. **Required Ports**: Checks if target ports (80, 9090, 3000, 9100) are open and accepting connections.
9. **Required Processes**: Runs `pgrep` inside target containers (using the Docker SDK) to verify essential processes (e.g., `nginx`) are active.

---

## 🛠️ Remediation & Self-Healing Logic

When a failure is detected, the engine triggers the Ansible remediation playbook:

```bash
ansible-playbook -i ansible/inventory.ini ansible/playbooks/remediation.yml --extra-vars "target=<service> action=<action>"
```

* **Play 1 (Host Daemon / Local connection)**: Triggers container restarts or recreates stopped services using the `community.docker` module via the mounted socket.
* **Play 2 (Container-internal / Docker connection)**: Connects directly inside the container (using `ansible_connection=docker`) to run cleanup commands, truncate large log files, or restore default configurations.

---

## 🚀 Setup & Execution

### Prerequisites:
* Docker & Docker Compose
* Python 3.11+ (for local test development)

### 1. Spin up the Infrastructure
Run Docker Compose from the root directory to build and start the SRE stack:
```bash
docker compose up -d --build
```
This starts the `demo-app`, `prometheus`, `grafana`, `node-exporter`, and starts the `health-engine` container.

### 2. Run the Health Check Engine Manually
To trigger a manual run of the health checks and see the output logs:
```bash
docker compose run --rm health-engine
```

### 3. View the generated SRE Dashboard
Remediation logs are output to the `reports/` directory on the host:
* `reports/health_results.json`: JSON data structure detailing the SRE run results.
* `reports/health_report.html`: A premium visual SRE cockpit HTML report showing the compliance score and service statuses.

---

## 🧪 Simulating Failures (Auto-Remediation Demos)

To showcase the self-healing engine in interviews or demos, you can simulate failures on the fly:

### Demo A: Stopped Container Recovery
1. Manually stop the Nginx Web App:
   ```bash
   docker stop demo-app
   ```
2. Run the SRE Health Engine:
   ```bash
   docker compose run --rm health-engine
   ```
3. **Outcome**: The engine detects that `demo-app` is stopped, runs the Ansible playbook to restart the container, verifies it is responding to HTTP, and writes the status as `Fixed` in the dashboard.

### Demo B: Disk Full / Internal Log Cleanup
1. Write a mock large log file inside the demo-app container:
   ```bash
   docker exec -it demo-app sh -c "dd if=/dev/zero of=/var/log/mock_large.log bs=1M count=100"
   ```
2. Run the SRE Health Engine:
   ```bash
   docker compose run --rm health-engine
   ```
3. **Outcome**: The engine detects high disk utilization, executes the Ansible play targeting `demo-app` using the `docker` connection transport, runs the cleanup task to truncate all `*.log` files, and verifies that disk usage has dropped.

---

## 🧪 Running Unit Tests

The test suite mocks the Docker SDK, HTTP calls, and subprocess execution, allowing tests to run instantly on any host without requiring a running Docker daemon:

```bash
pip install -r requirements.txt
python -m pytest tests/ -v
```

---

## 📈 Observability & Dashboards
* **Prometheus**: Accessible at `http://localhost:9090` to query metric trends.
* **Grafana**: Accessible at `http://localhost:3000` (pre-configured for embed view and anonymous read access).
