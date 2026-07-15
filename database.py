import logging
import os
import sqlite3
from typing import Union, List, Dict, Any
import json

logger = logging.getLogger(__name__)
logger.propagate = False  # Prevent propagation to the root logger

class Database:
    def __init__(self):
        self.db_path = os.path.join(os.path.dirname(__file__), "webz.db")
        self.__setup_tables()

    def connect(self):
        con = sqlite3.connect(self.db_path)
        con.execute("PRAGMA foreign_keys = ON")
        return con
        

    def __setup_tables(self):
        """
        +--------------+
        |   projects   |
        +--------------+
        | PK proj_id   |
        |    name      |
        +--------------+
            |
            | 1
            v
        +--------------+
        |    target    |
        +--------------+
        | PK targ_id   |
        | FK proj_id   |
        |    address   |
        +--------------+
            |
            | 1
            v
        +--------------+
        |    scans     |
        +--------------+
        | PK scan_id   |
        | FK targ_id   |
        |    tool      |
        |    args      |
        |    time      |
        +--------------+
            |
            | 1
            v
        +--------------+
        |   results    |
        +--------------+
        | PK res_id    |
        | FK scan_id   |
        |    key       |
        |    value     |
        +--------------+
        """
        logger.info("creating tables")
        with self.connect() as con:
            try:
                con.execute("""
                    CREATE TABLE IF NOT EXISTS projects (
                    project_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_name TEXT NOT NULL UNIQUE);
                """)
                logger.info("Projects table configured")

                con.execute("""
                    CREATE TABLE IF NOT EXISTS target (
                    target_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER NOT NULL,
                    address TEXT NOT NULL UNIQUE,
                    FOREIGN KEY (project_id) REFERENCES projects(project_id) ON DELETE CASCADE);
                """)
                logger.info("target table configured")

                con.execute("""
                    CREATE TABLE IF NOT EXISTS scans (
                        scan_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        target_id INTEGER NOT NULL,
                        tool_name TEXT NOT NULL,
                        args TEXT,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (target_id) REFERENCES target(target_id) ON DELETE CASCADE
                    );
                """)
                logger.info("scans table configured")

                con.execute("""
                    CREATE TABLE IF NOT EXISTS results (
                        result_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        scan_id INTEGER NOT NULL,
                        key TEXT NOT NULL,
                        value TEXT NOT NULL,
                        FOREIGN KEY (scan_id) REFERENCES scans(scan_id) ON DELETE CASCADE
                    ); """)
                logger.info("result table configured")
            except Exception as e:
                logger.error(f"Error in creating tables: {e}")
                return

    def get_projects(self) -> List:
        with self.connect() as con:
            response = con.execute("SELECT project_id, project_name FROM projects ORDER BY project_id")
            return response.fetchall()

    def add_new_project(self, name: str) -> int:
        with self.connect() as con:
            try:
                con.execute("INSERT INTO projects(project_name) VALUES(?)", (name,))
                con.commit()
                return 0
            except sqlite3.Error as e:
                logger.error(f"Insert failed: {e}")
                return -1

    def delete_project_by_id(self, id: int) -> bool:
        with self.connect() as con:
            cur = con.execute("DELETE FROM projects WHERE project_id = ?", (id,))
            con.commit()
            return cur.rowcount == 1

    def delete_target_by_id(self, id: int) -> bool:
        with self.connect() as con:
            cur = con.execute("DELETE FROM target WHERE target_id = ?", (id,))
            con.commit()
            return cur.rowcount == 1

    def delete_scan_by_id(self, id: int) -> bool:
        with self.connect() as con:
            cur = con.execute("DELETE FROM scans WHERE scan_id = ?", (id,))
            con.commit()
            return cur.rowcount == 1

    def get_project_data_count(self, project_id: int) -> Dict[str, int]:
        with self.connect() as con:
            cur = con.execute("SELECT COUNT(*) FROM target WHERE project_id = ?", (project_id,))
            target_count = cur.fetchone()[0]

            cur = con.execute(
                """
                SELECT COUNT(*)
                FROM scans
                JOIN target ON scans.target_id = target.target_id
                WHERE target.project_id = ?
                """,
                (project_id,),
            )
            scan_count = cur.fetchone()[0]

            cur = con.execute(
                """
                SELECT COUNT(*)
                FROM results
                JOIN scans ON results.scan_id = scans.scan_id
                JOIN target ON scans.target_id = target.target_id
                WHERE target.project_id = ?
                """,
                (project_id,),
            )
            result_count = cur.fetchone()[0]

            return {
                "target_count": target_count,
                "scan_count": scan_count,
                "result_count": result_count,
            }

    def get_target_data_count(self, target_id: int) -> Dict[str, int]:
        with self.connect() as con:
            cur = con.execute("SELECT COUNT(*) FROM scans WHERE target_id = ?", (target_id,))
            scan_count = cur.fetchone()[0]

            cur = con.execute(
                """
                SELECT COUNT(*)
                FROM results
                JOIN scans ON results.scan_id = scans.scan_id
                WHERE scans.target_id = ?
                """,
                (target_id,),
            )
            result_count = cur.fetchone()[0]

            return {"scan_count": scan_count, "result_count": result_count}

    def get_project(self, id: int) -> Union[List, None]:
        with self.connect() as con:

            cur = con.execute("SELECT project_id, project_name FROM projects WHERE project_id = ?", (id,))
            con.commit()
            result = cur.fetchone()

            if result:
                id, name = result
                logger.info(f"Found project: ID={id}")
                return [id, name]
            else:
                logger.error("Project not found")
                return None

    def save_target(self, project_id: int, target: str):
        with self.connect() as con:
            try:
                cur = con.execute("INSERT OR IGNORE INTO target(project_id, address) VALUES(?, ?)", (project_id, target))
                con.commit()

                cur = con.execute(
                    "SELECT target_id FROM target WHERE project_id = ? AND address = ?",
                    (project_id, target),
                )
                row = cur.fetchone()
                return row[0] if row else None

            except Exception as e:
                logger.error(f"Error in saving target: {e}")

    def save_scan(self, target_id: int, tool_name: str, args: List[Any]):
        with self.connect() as con:
            try:
                cur = con.execute(
                    "INSERT INTO scans (target_id, tool_name, args) VALUES(?,?,?) RETURNING scan_id",
                    (target_id, tool_name, json.dumps(args)),
                )
                row = cur.fetchone()
                con.commit()
                return row[0] if row else None

            except Exception as e:
                logger.error(f"Error in save_scan: {e}")

    def save_result(self, scan_id: int, key: str, value: Any):
        with self.connect() as con:
            query = """
                INSERT INTO results (scan_id, key, value)
                VALUES (?, ?, ?)
            """

            con.execute(query, (scan_id, key, str(value)))
            con.commit()
            logger.info(f"Results for {key} saved/updated for scan_id {scan_id}")

    def get_project_targets(self, project_id: int) -> List[Dict[str, Any]]:
        with self.connect() as con:
            cur = con.execute(
                "SELECT target_id, address FROM target WHERE project_id = ? ORDER BY target_id",
                (project_id,),
            )
            rows = cur.fetchall()
            return [{"target_id": row[0], "address": row[1]} for row in rows]

    def get_target_scans(self, target_id: int) -> List[Dict[str, Any]]:
        with self.connect() as con:
            cur = con.execute(
                """
                SELECT scan_id, tool_name, args, timestamp
                FROM scans
                WHERE target_id = ?
                ORDER BY scan_id DESC
                """,
                (target_id,),
            )
            rows = cur.fetchall()
            return [
                {
                    "scan_id": row[0],
                    "tool_name": row[1],
                    "args": row[2],
                    "timestamp": row[3],
                }
                for row in rows
            ]

    def get_scan_results(self, scan_id: int) -> List[Dict[str, Any]]:
        with self.connect() as con:
            cur = con.execute(
                "SELECT result_id, key, value FROM results WHERE scan_id = ? ORDER BY result_id",
                (scan_id,),
            )
            rows = cur.fetchall()
            return [{"result_id": row[0], "key": row[1], "value": row[2]} for row in rows]

    def close(self):
        pass
        #self.cur.close()
        #self.con.close()
