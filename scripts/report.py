"""HTML Reporting Dashboard Generator.

Compiles JSON health results into a modern, responsive HTML SRE status dashboard
showing system status, compliance scores, and remediation results.
"""
import argparse
import html
import json
import os
from datetime import datetime, timezone


def load_results(report_dir):
    path = os.path.join(report_dir, "health_results.json")
    with open(path) as f:
        return json.load(f)


def build_html(data):
    results = data["results"]
    timestamp = data["timestamp"]
    score = data["health_score"]
    summary = data["summary"]

    status_colors = {
        "Healthy": "#10b981",  # Emerald Green
        "Fixed": "#3b82f6",    # Blue
        "Failed": "#ef4444"     # Red
    }
    
    status_bg_colors = {
        "Healthy": "#ecfdf5",
        "Fixed": "#eff6ff",
        "Failed": "#fef2f2"
    }

    rows = ""
    for r in results:
        service = html.escape(str(r["service"]))
        status = html.escape(str(r["status"]))
        details = html.escape(str(r["details"]))
        action_taken = html.escape(str(r["action_taken"]))
        verification = html.escape(str(r["verification"]))
        
        color = status_colors.get(r["status"], "#6b7280")
        bg_color = status_bg_colors.get(r["status"], "#f3f4f6")
        
        rows += f"""
        <tr>
            <td style="font-weight: 600; color: #1f2937;">{service}</td>
            <td>
                <span class="status-badge" style="background-color: {bg_color}; color: {color}; border: 1px solid {color}20;">
                    {status}
                </span>
            </td>
            <td class="text-secondary">{details}</td>
            <td class="font-mono text-secondary">{action_taken}</td>
            <td>
                <span style="color: {'#059669' if 'Passed' in verification else '#dc2626' if 'Failed' in verification else '#4b5563'}; font-weight: 500;">
                    {verification}
                </span>
            </td>
        </tr>"""

    # Visual compliance score circle or color
    score_color = "#10b981" if score >= 90 else "#f59e0b" if score >= 70 else "#ef4444"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SRE Cockpit — Self-Healing Infrastructure</title>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    <style>
        :root {{
            --font-main: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
            --font-code: 'JetBrains Mono', monospace;
            --primary: #4f46e5;
            --bg-page: #f8fafc;
            --bg-card: #ffffff;
            --border: #e2e8f0;
            --text-main: #0f172a;
            --text-muted: #64748b;
        }}
        
        body {{
            font-family: var(--font-main);
            background-color: var(--bg-page);
            color: var(--text-main);
            margin: 0;
            padding: 40px 20px;
            -webkit-font-smoothing: antialiased;
        }}

        .container {{
            max-width: 1000px;
            margin: 0 auto;
        }}

        header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 32px;
            border-bottom: 1px solid var(--border);
            padding-bottom: 24px;
        }}

        .brand h1 {{
            font-size: 28px;
            font-weight: 700;
            margin: 0 0 6px 0;
            letter-spacing: -0.5px;
            color: var(--text-main);
        }}

        .brand p {{
            font-size: 14px;
            color: var(--text-muted);
            margin: 0;
        }}

        .timestamp {{
            font-size: 13px;
            background: #e0e7ff;
            color: var(--primary);
            padding: 6px 14px;
            border-radius: 9999px;
            font-weight: 600;
        }}

        .dashboard-grid {{
            display: grid;
            grid-template-columns: 280px 1fr;
            gap: 32px;
        }}

        @media (max-width: 768px) {{
            .dashboard-grid {{
                grid-template-columns: 1fr;
            }}
        }}

        .sidebar {{
            display: flex;
            flex-direction: column;
            gap: 24px;
        }}

        .card {{
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 24px;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.02), 0 10px 20px -5px rgba(0, 0, 0, 0.03);
        }}

        .score-box {{
            text-align: center;
        }}

        .score-circle {{
            width: 140px;
            height: 140px;
            border-radius: 50%;
            border: 8px solid {score_color}15;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            margin: 0 auto 16px auto;
        }}

        .score-value {{
            font-size: 40px;
            font-weight: 700;
            color: {score_color};
            line-height: 1;
        }}

        .score-label {{
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
            color: var(--text-muted);
            letter-spacing: 1px;
            margin-top: 4px;
        }}

        .stats-list {{
            display: flex;
            flex-direction: column;
            gap: 12px;
            margin-top: 8px;
        }}

        .stat-item {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 14px;
            font-weight: 500;
        }}

        .stat-item span:first-child {{
            color: var(--text-muted);
        }}

        .stat-item span:last-child {{
            font-weight: 600;
        }}

        .badge {{
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: 600;
        }}

        .main-content {{
            overflow: hidden;
        }}

        .main-content h2 {{
            font-size: 18px;
            font-weight: 700;
            margin: 0 0 20px 0;
            color: var(--text-main);
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            text-align: left;
        }}

        th {{
            background-color: #f1f5f9;
            color: var(--text-muted);
            font-size: 11px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            padding: 12px 16px;
            border-bottom: 1px solid var(--border);
        }}

        td {{
            padding: 16px;
            border-bottom: 1px solid var(--border);
            font-size: 13.5px;
            vertical-align: middle;
        }}

        tr:last-child td {{
            border-bottom: none;
        }}

        .status-badge {{
            display: inline-flex;
            align-items: center;
            font-size: 12px;
            font-weight: 600;
            padding: 4px 10px;
            border-radius: 6px;
        }}

        .text-secondary {{
            color: #475569;
        }}

        .font-mono {{
            font-family: var(--font-code);
            font-size: 12px;
        }}

        footer {{
            margin-top: 48px;
            text-align: center;
            font-size: 12px;
            color: var(--text-muted);
            border-top: 1px solid var(--border);
            padding-top: 24px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="brand">
                <h1>SRE Dashboard</h1>
                <p>Self-Healing Infrastructure Control Panel</p>
            </div>
            <div class="timestamp">
                Last checked: {html.escape(timestamp)}
            </div>
        </header>

        <div class="dashboard-grid">
            <div class="sidebar">
                <div class="card score-box">
                    <div class="score-circle">
                        <div class="score-value">{score}%</div>
                        <div class="score-label">Compliance</div>
                    </div>
                    <div class="stats-list">
                        <div class="stat-item">
                            <span>Healthy Services</span>
                            <span style="color: #10b981;">{summary["healthy"]}</span>
                        </div>
                        <div class="stat-item">
                            <span>Remediated (Fixed)</span>
                            <span style="color: #3b82f6;">{summary["fixed"]}</span>
                        </div>
                        <div class="stat-item">
                            <span>Failed Services</span>
                            <span style="color: #ef4444;">{summary["failed"]}</span>
                        </div>
                        <div class="stat-item" style="border-top: 1px solid #f1f5f9; padding-top: 10px; margin-top: 4px;">
                            <span>Total Checks</span>
                            <span>{summary["total"]}</span>
                        </div>
                    </div>
                </div>
                
                <div class="card" style="font-size: 13px; line-height: 1.6;">
                    <h3 style="margin-top:0; font-size: 14px; font-weight: 700;">Infrastructure Insights</h3>
                    <p style="color: var(--text-muted); margin-bottom: 0;">
                        This control room displays the active state of Dockerized microservices. If any health check fails, the <strong>Python SRE Engine</strong> automatically triggers an <strong>Ansible playbook</strong> to remediate the service.
                    </p>
                </div>
            </div>

            <div class="main-content card">
                <h2>Health Verification Logs</h2>
                <div style="overflow-x: auto;">
                    <table>
                        <thead>
                            <tr>
                                <th>Service/Metric</th>
                                <th>Status</th>
                                <th>Check Outcome</th>
                                <th>Remediation Action</th>
                                <th>Verification</th>
                            </tr>
                        </thead>
                        <tbody>
                            {rows}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        <footer>
            SRE Cockpit | Powered by Docker + Python + Ansible | Interview Portfolio
        </footer>
    </div>
</body>
</html>"""


def generate_html_report(results, report_dir):
    """Compiles results dict and writes the HTML report."""
    os.makedirs(report_dir, exist_ok=True)
    healthy, fixed, failed, score = 0, 0, 0, 0
    total = len(results) or 1
    
    for r in results:
        if r["status"] == "Healthy":
            healthy += 1
        elif r["status"] == "Fixed":
            fixed += 1
        elif r["status"] == "Failed":
            failed += 1
            
    score = int(((healthy + fixed) / total) * 100)
    
    data = {
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
    
    html_content = build_html(data)
    out_path = os.path.join(report_dir, "health_report.html")
    with open(out_path, "w") as f:
        f.write(html_content)
    return out_path


def main():
    parser = argparse.ArgumentParser(description="Generate an HTML SRE report.")
    parser.add_argument(
        "--report-dir",
        default=os.environ.get("HEALTH_REPORT_DIR", "reports"),
        help="Directory containing health_results.json and where the HTML report is written."
    )
    args = parser.parse_args()

    try:
        data = load_results(args.report_dir)
        html_content = build_html(data)
        out_path = os.path.join(args.report_dir, "health_report.html")
        with open(out_path, "w") as f:
            f.write(html_content)
        print(f"HTML report successfully generated: {out_path}")
    except Exception as e:
        print(f"Failed to generate HTML report: {e}")


if __name__ == "__main__":
    main()
