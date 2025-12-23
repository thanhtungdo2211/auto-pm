import logging
import os
from datetime import date, timedelta
from typing import Dict, List

import httpx

from services.query_today_task import (
    get_workspace_projects,
    get_project_issues_yesterday,
)

logger = logging.getLogger(__name__)

PLANE_BASE_URL = os.getenv("PLANE_API_URL", "https://af3142515b93.ngrok-free.app")
WORKSPACE_SLUG = os.getenv("WORKSPACE_SLUG", "thang")
PLANE_API_KEY = os.getenv("PLANE_API_KEY", "plane_api_fe15a1874a304088b027ce4bbe8afc23")


def _parse_manager_ids(raw_ids: str) -> List[str]:
    """
    Split comma/space separated manager Zalo IDs
    """
    if not raw_ids:
        return []
    parts = [p.strip() for p in raw_ids.replace(" ", "").split(",")]
    return [p for p in parts if p]


async def _get_issue_progress_for_day(
    client: httpx.AsyncClient,
    project_id: str,
    issue_id: str,
    day: str,
) -> List[Dict]:
    """
    Fetch daily progress entries for a specific issue on a given day
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
            "Failed to fetch daily progress for issue %s (status=%s)",
            issue_id,
            response.status_code,
        )
    except Exception as exc:  # pragma: no cover - network path
        logger.error("Error fetching daily progress for issue %s: %s", issue_id, exc)
    return []


async def _get_project_issues_all(
    client: httpx.AsyncClient,
    project_id: str,
) -> List[Dict]:
    """
    Fetch all issues for a project (no date filtering)
    """
    url = (
        f"{PLANE_BASE_URL}/api/v1/workspaces/"
        f"{WORKSPACE_SLUG}/projects/{project_id}/issues/"
    )
    headers = {"x-api-key": PLANE_API_KEY}
    try:
        resp = await client.get(url, headers=headers, timeout=30.0)
        resp.raise_for_status()
        return resp.json().get("results", [])
    except Exception as exc:  # pragma: no cover - network path
        logger.error("Error fetching issues for project %s: %s", project_id, exc)
        return []


async def _get_issue_progress_range(
    client: httpx.AsyncClient,
    project_id: str,
    issue_id: str,
    start_date: str,
    end_date: str,
) -> List[Dict]:
    """
    Fetch progress entries for an issue within a date range
    """
    url = (
        f"{PLANE_BASE_URL}/api/workspaces/"
        f"{WORKSPACE_SLUG}/projects/{project_id}/issues/{issue_id}/daily-progress/"
    )
    headers = {"Content-Type": "application/json", "x-api-key": PLANE_API_KEY}
    params = {"start_date": start_date, "end_date": end_date}
    try:
        resp = await client.get(url, headers=headers, params=params, timeout=30.0)
        if resp.status_code == 200:
            return resp.json()
        logger.warning(
            "Failed to fetch progress range for issue %s (status=%s)",
            issue_id,
            resp.status_code,
        )
    except Exception as exc:  # pragma: no cover - network path
        logger.error("Error fetching progress range for issue %s: %s", issue_id, exc)
    return []


async def collect_yesterday_reports() -> Dict:
    """
    Collect all issues that had progress updates yesterday across the workspace.

    Returns:
        {
            "day": "YYYY-MM-DD",
            "items": [
                {
                    "project_name": "...",
                    "issue_name": "...",
                    "issue_id": "...",
                    "progress_entries": [{...}],
                },
                ...
            ],
        }
    """
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    items: List[Dict] = []

    projects = await get_workspace_projects()
    async with httpx.AsyncClient(verify=False) as client:
        for project in projects:
            project_id = project.get("id")
            project_name = project.get("name", "N/A")
            if not project_id:
                continue

            issues = await get_project_issues_yesterday(project_id)
            for issue in issues:
                issue_id = issue.get("id")
                issue_name = issue.get("name", "N/A")
                if not issue_id:
                    continue

                progress_entries = await _get_issue_progress_for_day(
                    client=client,
                    project_id=project_id,
                    issue_id=issue_id,
                    day=yesterday,
                )

                if progress_entries:
                    items.append(
                        {
                            "project_name": project_name,
                            "issue_name": issue_name,
                            "issue_id": issue_id,
                            "progress_entries": progress_entries,
                        }
                    )

    return {"day": yesterday, "items": items}


def format_manager_report(data: Dict) -> str:
    """
    Build a human-friendly summary text for managers
    """
    day = data.get("day")
    items = data.get("items", [])

    if not items:
        return f"Không có báo cáo nào cho ngày {day}."

    lines = [
        f"Báo cáo tổng hợp ngày {day}",
        "────────────────────────────",
    ]

    for idx, item in enumerate(items, start=1):
        lines.append(f"{idx}. [{item['project_name']}] {item['issue_name']}")
        for entry in item.get("progress_entries", []):
            notes = (entry.get("notes") or "").strip()
            if len(notes) > 180:
                notes = notes[:177] + "..."
            progress_pct = entry.get("progress", "N/A")
            time_spent = entry.get("time_spent", "")
            lines.append(f"   - Tiến độ: {progress_pct}%, Thời gian: {time_spent or 'N/A'}")
            if notes:
                lines.append(f"   - Ghi chú: {notes}")
        lines.append("")  # blank line between items

    lines.append("────────────────────────────")
    lines.append("Tự động gửi bởi hệ thống.")
    return "\n".join(lines)


async def collect_progress_grouped_by_project(
    start_date: str | None = None,
    end_date: str | None = None,
) -> Dict:
    """
    Collect daily progress entries grouped by day -> project.
    This mirrors the synchronous helper the user shared, adapted for manager reporting.
    """
    today = date.today()
    start = start_date or (today - timedelta(days=1)).isoformat()
    end = end_date or start

    grouped: Dict[str, Dict[str, Dict[str, List[Dict]]]] = {}

    projects = await get_workspace_projects()
    async with httpx.AsyncClient(verify=False) as client:
        for project in projects:
            project_id = project.get("id")
            project_name = project.get("name", "N/A")
            if not project_id:
                continue

            issues = await _get_project_issues_all(client, project_id)
            for issue in issues:
                issue_id = issue.get("id")
                issue_name = issue.get("name", "N/A")
                if not issue_id:
                    continue

                progress_entries = await _get_issue_progress_range(
                    client=client,
                    project_id=project_id,
                    issue_id=issue_id,
                    start_date=start,
                    end_date=end,
                )

                for progress in progress_entries:
                    day = progress.get("day") or start
                    day_bucket = grouped.setdefault(day, {})
                    proj_bucket = day_bucket.setdefault(
                        project_name, {"project_id": project_id, "issues": []}
                    )
                    proj_bucket["issues"].append(
                        {
                            "issue_id": issue_id,
                            "issue_name": issue_name,
                            "issue_sequence_id": progress.get("issue_sequence_id"),
                            "progress": progress,
                        }
                    )

    return grouped


def format_grouped_report(grouped: Dict) -> str:
    """
    Format grouped data (day -> project -> issues) into a concise manager message.
    """
    if not grouped:
        return "Không có báo cáo nào trong khoảng thời gian đã chọn."

    days = sorted(grouped.keys(), reverse=True)
    lines: List[str] = []

    for day in days:
        lines.append(f"📅 {day}")
        lines.append("────────────────────────────")
        for project_name, project_data in grouped[day].items():
            lines.append(f"• Dự án: {project_name}")
            for issue in project_data.get("issues", []):
                progress = issue.get("progress", {})
                pct = progress.get("progress", "N/A")
                notes = (progress.get("notes") or "").strip()
                if len(notes) > 160:
                    notes = notes[:157] + "..."
                lines.append(
                    f"  - {issue.get('issue_name', 'N/A')} "
                    f"(#{issue.get('issue_sequence_id')}) — {pct}%"
                )
                if notes:
                    lines.append(f"    Ghi chú: {notes}")
            lines.append("")  # blank line per project
        lines.append("")  # blank line per day

    lines.append("Tự động gửi bởi hệ thống.")
    return "\n".join(lines)


async def send_manager_summary(zalo_service, manager_ids: List[str]) -> Dict:
    """
    Collect yesterday's reports and send to provided manager Zalo IDs.
    """
    if not manager_ids:
        logger.warning("No manager IDs provided; skip sending summary")
        return {"sent": 0, "skipped": True}

    summary_data = await collect_yesterday_reports()
    message = format_manager_report(summary_data)

    sent = 0
    failed = 0

    for manager_id in manager_ids:
        try:
            ok = await zalo_service.send_message(
                user_id=str(manager_id),
                text=message,
                metadata={
                    "type": "yesterday_report_summary",
                    "day": summary_data.get("day"),
                },
            )
            if ok:
                sent += 1
            else:
                failed += 1
        except Exception as exc:  # pragma: no cover - network path
            logger.error("Error sending summary to manager %s: %s", manager_id, exc)
            failed += 1

    return {"sent": sent, "failed": failed, "day": summary_data.get("day")}


