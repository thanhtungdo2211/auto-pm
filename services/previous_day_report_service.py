import logging
import os
from datetime import date, timedelta
from typing import Dict, List, Optional

import httpx

from services.query_today_task import (
    get_project_issues_yesterday,
    get_workspace_projects,
)

logger = logging.getLogger(__name__)

PLANE_BASE_URL = os.getenv("PLANE_API_URL", "https://af3142515b93.ngrok-free.app")
WORKSPACE_SLUG = os.getenv("WORKSPACE_SLUG", "thang")
PLANE_API_KEY = os.getenv("PLANE_API_KEY", "plane_api_fe15a1874a304088b027ce4bbe8afc23")


async def _fetch_issue_progress_for_day(
    client: httpx.AsyncClient,
    project_id: str,
    issue_id: str,
    day: str,
) -> List[Dict]:
    """
    Lấy danh sách bản ghi daily-progress của một issue trong một ngày cụ thể.
    """
    url = (
        f"{PLANE_BASE_URL}/api/workspaces/"
        f"{WORKSPACE_SLUG}/projects/{project_id}/issues/{issue_id}/daily-progress/"
    )
    headers = {"x-api-key": PLANE_API_KEY, "Content-Type": "application/json"}

    try:
        response = await client.get(url, headers=headers, params={"day": day}, timeout=20.0)
        if response.status_code == 200:
            return response.json()
        logger.warning(
            "Không thể lấy daily-progress cho issue %s (status=%s)",
            issue_id,
            response.status_code,
        )
    except Exception as exc:  # pragma: no cover - đường mạng
        logger.error("Lỗi khi lấy daily-progress cho issue %s: %s", issue_id, exc)
    return []


async def aggregate_previous_day_reports(target_day: Optional[str] = None) -> Dict:
    """
    Tổng hợp báo cáo (daily-progress) của tất cả task trong workspace của ngày hôm trước.
    Bao gồm cả task không có báo cáo (progress_entries rỗng) để manager thấy đủ danh sách.

    Args:
        target_day: ngày cần tổng hợp, mặc định là hôm qua theo ISO date.

    Returns:
        {
            "day": "YYYY-MM-DD",
            "projects": [
                {
                    "project_id": "...",
                    "project_name": "...",
                    "issues": [
                        {
                            "issue_id": "...",
                            "issue_name": "...",
                            "progress_entries": [{...}]
                        }
                    ]
                }
            ],
            "total_projects": <int>,
            "total_issues": <int>
        }
    """
    day = target_day or (date.today() - timedelta(days=1)).isoformat()
    summary: Dict[str, object] = {
        "day": day,
        "projects": [],
        "total_projects": 0,
        "total_issues": 0,
    }

    projects = await get_workspace_projects()
    async with httpx.AsyncClient(verify=False) as client:
        for project in projects:
            project_id = project.get("id")
            if not project_id:
                continue

            project_name = project.get("name", "N/A")
            issues = await get_project_issues_yesterday(project_id)

            project_payload = {
                "project_id": project_id,
                "project_name": project_name,
                "issues": [],
            }

            for issue in issues:
                issue_id = issue.get("id")
                if not issue_id:
                    continue

                issue_name = issue.get("name", "N/A")
                progress_entries = await _fetch_issue_progress_for_day(
                    client=client,
                    project_id=project_id,
                    issue_id=issue_id,
                    day=day,
                )

                project_payload["issues"].append(
                    {
                        "issue_id": issue_id,
                        "issue_name": issue_name,
                        "assignee_ids": issue.get("assignees", []),
                        "has_report": bool(progress_entries),
                        "progress_entries": progress_entries,
                    }
                )

            if project_payload["issues"]:
                summary["projects"].append(project_payload)

    summary["total_projects"] = len(summary["projects"])
    summary["total_issues"] = sum(len(p["issues"]) for p in summary["projects"])
    return summary


def format_previous_day_report(summary: Dict) -> str:
    """
    Chuyển dữ liệu tổng hợp thành chuỗi dễ đọc cho người quản lý.
    """
    day = summary.get("day")
    projects: List[Dict] = summary.get("projects", [])

    if not projects:
        return f"Không có báo cáo daily-progress nào cho ngày {day}."

    lines: List[str] = [
        f"Tổng hợp báo cáo ngày {day}",
        "────────────────────────────",
    ]

    for project in projects:
        project_name = project.get("project_name", "N/A")
        issues = project.get("issues", [])
        lines.append(f"• Dự án: {project_name} ({len(issues)} task)")

        for issue in issues:
            lines.append(f"  - {issue.get('issue_name', 'N/A')} (#{issue.get('issue_id')})")
            for entry in issue.get("progress_entries", []):
                pct = entry.get("progress", "N/A")
                time_spent = entry.get("time_spent") or "N/A"
                notes = (entry.get("notes") or "").strip()
                if len(notes) > 180:
                    notes = notes[:177] + "..."

                lines.append(f"    Tiến độ: {pct}% | Thời gian: {time_spent}")
                if notes:
                    lines.append(f"    Ghi chú: {notes}")

        lines.append("")  # ngăn cách dự án

    lines.append("Báo cáo được tổng hợp tự động.")
    return "\n".join(lines)

