from __future__ import annotations

import json
import sys
from pathlib import Path

from flask import Flask, redirect, render_template, request, url_for

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from database import Database

app = Flask(__name__, template_folder=str(Path(__file__).resolve().parent / "templates"), static_folder=str(Path(__file__).resolve().parent / "static"))


# flask routes run in different threads by default so database connection need to be open per thread
def get_db() -> Database:
    return Database()


@app.route("/")
def index():
    db = get_db()
    try:
        projects = db.get_projects()
        project_cards = []
        for project_id, project_name in projects:
            counts = db.get_project_data_count(project_id)
            project_cards.append(
                {
                    "project_id": project_id,
                    "project_name": project_name,
                    "has_data": counts["target_count"] > 0 or counts["scan_count"] > 0 or counts["result_count"] > 0,
                }
            )
    finally:
        db.close()

    return render_template("index.html", projects=project_cards)


@app.route("/project/<int:project_id>")
def project_detail(project_id: int):
    db = get_db()
    try:
        project = db.get_project(project_id)
        targets = db.get_project_targets(project_id)
        target_stats = {target["target_id"]: db.get_target_data_count(target["target_id"]) for target in targets}
        selected_target_id = request.args.get("target", type=int)

        if selected_target_id is None and targets:
            selected_target_id = targets[0]["target_id"]

        if selected_target_id is not None:
            scans = db.get_target_scans(selected_target_id)
            for scan in scans:
                raw_args = scan.get("args")
                if raw_args:
                    try:
                        scan["args"] = json.loads(raw_args)
                    except json.JSONDecodeError:
                        scan["args"] = raw_args

                results = db.get_scan_results(scan["scan_id"])
                for result in results:
                    raw_value = result.get("value")
                    if raw_value:
                        try:
                            result["value"] = json.loads(raw_value)
                        except json.JSONDecodeError:
                            result["value"] = raw_value
                scan["results"] = results
        else:
            scans = []

        project_stats = db.get_project_data_count(project_id)
    finally:
        db.close()

    project_has_data = project_stats["target_count"] > 0 or project_stats["scan_count"] > 0 or project_stats["result_count"] > 0

    return render_template(
        "project.html",
        project=project,
        targets=targets,
        target_stats=target_stats,
        selected_target_id=selected_target_id,
        scans=scans,
        project_has_data=project_has_data,
    )


@app.route("/delete-project/<int:project_id>", methods=["POST"])
def delete_project(project_id: int):
    db = get_db()
    try:
        db.delete_project_by_id(project_id)
    finally:
        db.close()
    return redirect(url_for("index"))


@app.route("/delete-target/<int:target_id>", methods=["POST"])
def delete_target(target_id: int):
    project_id = request.form.get("project_id", type=int)
    db = get_db()
    try:
        db.delete_target_by_id(target_id)
    finally:
        db.close()

    if project_id is not None:
        return redirect(url_for("project_detail", project_id=project_id))
    return redirect(url_for("index"))


@app.route("/delete-scan/<int:scan_id>", methods=["POST"])
def delete_scan(scan_id: int):
    project_id = request.form.get("project_id", type=int)
    target_id = request.form.get("target_id", type=int)
    db = get_db()
    try:
        db.delete_scan_by_id(scan_id)
    finally:
        db.close()

    if project_id is not None:
        if target_id is not None:
            return redirect(url_for("project_detail", project_id=project_id, target=target_id))
        return redirect(url_for("project_detail", project_id=project_id))
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
