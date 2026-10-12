import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

import requests
import base64

ORG = "Digination"
PROJECT = "HRDF-2026"
PAT = os.environ.get("AZURE_PAT", "").strip()
USER = os.environ.get("AZURE_USER", "").strip() or "Mohamed Hatem Abo Taleb <mhatem@diginationmea.com>"
WORK_HOURS = 8
DEFAULT_MANAGER = "Khaled Abd El-Rahman Abd El Fattah"
FIXED_HOUR = 21
FIXED_MINUTE = 0
DEFAULT_TITLE = "working  new  task"
CONFIG_PATH = Path(__file__).with_name("user_config.json")


def get_headers_for_create(pat):
    token = base64.b64encode(f":{pat}".encode()).decode()
    return {
        "Authorization": f"Basic {token}",
        "Content-Type": "application/json-patch+json",
    }


def get_headers_for_query(pat):
    token = base64.b64encode(f":{pat}".encode()).decode()
    return {
        "Authorization": f"Basic {token}",
        "Content-Type": "application/json",
    }


def validate_pat(pat):
    if not pat or len(pat.strip()) < 20:
        return False, "PAT looks too short. Please paste the full token."
    return True, ""


def build_finish_date_utc_string(date_value):
    local_tz = datetime.now().astimezone().tzinfo
    local_finish = date_value.replace(
        hour=FIXED_HOUR,
        minute=FIXED_MINUTE,
        second=0,
        microsecond=0,
        tzinfo=local_tz,
    )
    finish_utc = local_finish.astimezone(timezone.utc)
    return finish_utc.strftime("%Y-%m-%dT%H:%M:%SZ"), local_finish


def load_raw_config():
    if not CONFIG_PATH.exists():
        return {}
    try:
        with CONFIG_PATH.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def save_user_config(config):
    with CONFIG_PATH.open("w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=True, indent=2)


def make_profile(user, pat, org=ORG, project=PROJECT, manager=DEFAULT_MANAGER, profile_id=None):
    return {
        "id": profile_id or str(uuid.uuid4()),
        "label": user,
        "user": user,
        "pat": pat,
        "org": org or ORG,
        "project": project or PROJECT,
        "manager": manager or DEFAULT_MANAGER,
    }


def default_profile():
    return make_profile(USER, PAT, ORG, PROJECT, DEFAULT_MANAGER, "default")


def env_profile():
    pat = os.environ.get("AZURE_PAT", "").strip()
    user = os.environ.get("AZURE_USER", "").strip()
    if not pat or not user:
        return None
    return make_profile(
        user,
        pat,
        os.environ.get("AZURE_ORG", "").strip() or ORG,
        os.environ.get("AZURE_PROJECT", "").strip() or PROJECT,
        os.environ.get("AZURE_MANAGER", "").strip() or DEFAULT_MANAGER,
        "env",
    )


def normalize_config(raw=None):
    raw = raw if raw is not None else load_raw_config()
    profiles = list(raw.get("profiles") or [])
    if not profiles:
        hosted = env_profile()
        if hosted:
            profiles = [hosted]
        elif raw.get("pat") or raw.get("user"):
            profiles = [
                make_profile(
                    raw.get("user") or USER,
                    raw.get("pat") or PAT,
                    raw.get("org") or ORG,
                    raw.get("project") or PROJECT,
                    raw.get("manager") or DEFAULT_MANAGER,
                    "default",
                )
            ]
        elif PAT.strip() and USER.strip():
            profiles = [default_profile()]
    active = raw.get("active_profile") or (profiles[0]["id"] if profiles else "")
    if profiles and not any(p.get("id") == active for p in profiles):
        active = profiles[0]["id"]
    config = {"profiles": profiles, "active_profile": active}
    save_user_config(config)
    return config


def get_active_profile(config):
    profiles = config.get("profiles") or []
    active = config.get("active_profile")
    for profile in profiles:
        if profile.get("id") == active:
            return profile
    return profiles[0] if profiles else None


def upsert_profile(config, profile, make_active=True):
    profiles = list(config.get("profiles") or [])
    replaced = False
    for index, existing in enumerate(profiles):
        if existing.get("id") == profile["id"]:
            profiles[index] = profile
            replaced = True
            break
    if not replaced:
        profiles.append(profile)
    config["profiles"] = profiles
    if make_active:
        config["active_profile"] = profile["id"]
    save_user_config(config)
    return config


def set_active_profile(config, profile_id):
    config["active_profile"] = profile_id
    save_user_config(config)
    return get_active_profile(config)


def profile_choices(config):
    return [(p.get("label") or p.get("user") or p.get("id"), p.get("id")) for p in config.get("profiles") or []]


def get_existing_task_id(org, project, user, date, pat):
    query = {
        "query": f"""
        SELECT [System.Id]
        FROM WorkItems
        WHERE
            [System.TeamProject] = '{project}'
            AND [System.AssignedTo] = '{user}'
            AND [System.WorkItemType] = 'Task'
            AND [Microsoft.VSTS.Scheduling.FinishDate] = '{date.strftime("%Y-%m-%d")}'
        """
    }
    url = f"https://dev.azure.com/{org}/{project}/_apis/wit/wiql?api-version=7.0"
    response = requests.post(
        url,
        json=query,
        headers=get_headers_for_query(pat),
        timeout=30,
    )
    if response.status_code != 200:
        return None, response.text
    work_items = response.json().get("workItems", [])
    if not work_items:
        return None, None
    return work_items[0].get("id"), None


def create_task(org, project, user, manager, date, task_title, work_hours, pat):
    existing_task_id, check_error = get_existing_task_id(org, project, user, date, pat)
    if check_error:
        return False, f"Check failed:\n{check_error}"

    finish_utc_string, finish_local_datetime = build_finish_date_utc_string(date)
    if existing_task_id:
        url = f"https://dev.azure.com/{org}/{project}/_apis/wit/workitems/{existing_task_id}?api-version=7.0"
    else:
        url = f"https://dev.azure.com/{org}/{project}/_apis/wit/workitems/$Task?api-version=7.0"

    body = [
        {"op": "add", "path": "/fields/System.Title", "value": task_title},
        {"op": "add", "path": "/fields/System.AssignedTo", "value": user},
        {"op": "add", "path": "/fields/Custom.DirectManager", "value": manager},
        {"op": "add", "path": "/fields/Microsoft.VSTS.Scheduling.OriginalEstimate", "value": work_hours},
        {"op": "add", "path": "/fields/Microsoft.VSTS.Scheduling.CompletedWork", "value": work_hours},
        {"op": "add", "path": "/fields/Microsoft.VSTS.Scheduling.FinishDate", "value": finish_utc_string},
    ]

    if existing_task_id:
        response = requests.patch(url, json=body, headers=get_headers_for_create(pat), timeout=30)
    else:
        response = requests.post(url, json=body, headers=get_headers_for_create(pat), timeout=30)

    if response.status_code in [200, 201]:
        action = "تم التحديث بنجاح" if existing_task_id else "تم الإضافة بنجاح"
        return True, (
            f"{action}\n"
            f"Organization: {org}\n"
            f"Project: {project}\n"
            f"User: {user}\n"
            f"Date: {date.strftime('%Y-%m-%d')}\n"
            f"Fixed Time: {finish_local_datetime.strftime('%I:%M %p')}"
        )

    if response.status_code in [401, 403]:
        return False, (
            "Authentication failed while creating/updating task.\n"
            "Please check PAT token permissions and token expiry."
        )

    return False, f"Error creating task:\n{response.text}"
