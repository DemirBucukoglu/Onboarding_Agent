import json, pathlib, re
from typing import Dict, List, Any

# Constants
STEPS_FILE = pathlib.Path("steps.json")
EMPLOYEE_DATA_DIR = pathlib.Path("employee_data")


def _slug(text: str) -> str:
    """Convert text to a URL-safe slug format."""
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def _load_steps() -> List[Dict[str, Any]]:
    """Load steps configuration from steps.json file."""
    if not STEPS_FILE.exists():
        raise FileNotFoundError("steps.json not found.")
    
    with STEPS_FILE.open(encoding="utf-8") as f:
        data = json.load(f)
    
    if not all("title" in step for step in data):
        raise ValueError("Each step in steps.json must have at least a 'title'.")
    
    return data


def _get_progress_file(employee: str) -> pathlib.Path:
    """Get the progress file path for a specific employee."""
    EMPLOYEE_DATA_DIR.mkdir(exist_ok=True)
    return EMPLOYEE_DATA_DIR / f"{_slug(employee)}_onboarding.json"


def _create_blank_progress(employee: str, steps: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Create blank progress structure for a new employee."""
    return {
        "employee": employee,
        "steps": {
            _slug(step["title"]): {
                "title": step["title"],
                "description": step.get("description", ""),
                "type": step.get("type", "standard"),
                "status": "not_started",
                "get_status_api": step.get("get_status_api", ""),
                "complete_api": step.get("complete_api", ""),
                "keywords": step.get("keywords", []),
                "title_keywords": step.get("title_keywords", []),
                "config": step.get("config", {}),
                "depends_on": step.get("depends_on", []),
                "required_before": step.get("required_before", []),
                "user_data": {}
            }
            for step in steps
        },
    }


def load_steps_config() -> List[Dict[str, Any]]:
    """Load the steps configuration from steps.json."""
    return _load_steps()


def load(employee: str) -> Dict[str, Any]:
    """Load progress for a specific employee."""
    steps = _load_steps()
    path = _get_progress_file(employee)
    
    if path.exists():
        with path.open(encoding="utf-8") as f:
            existing_data = json.load(f)
        
        # Update existing progress with new step structure if needed
        updated_data = _create_blank_progress(employee, steps)
        
        # Preserve existing statuses and user data
        for step_slug, step_data in existing_data.get("steps", {}).items():
            if step_slug in updated_data["steps"]:
                updated_data["steps"][step_slug]["status"] = step_data.get("status", "not_started")
                updated_data["steps"][step_slug]["user_data"] = step_data.get("user_data", {})
        
        save(employee, updated_data)
        return updated_data
    
    # Create new progress for employee
    data = _create_blank_progress(employee, steps)
    save(employee, data)
    return data


def save(employee: str, data: Dict[str, Any]) -> None:
    """Save progress data for a specific employee."""
    _get_progress_file(employee).write_text(
        json.dumps(data, indent=2), encoding="utf-8"
    )


def set_status(employee: str, slug: str, status: str) -> None:
    """Set the status for a specific step of an employee."""
    data = load(employee)
    if slug in data["steps"]:
        data["steps"][slug]["status"] = status
        save(employee, data)


def set_user_data(employee: str, slug: str, user_data: Dict[str, Any]) -> None:
    """Set user data for a specific step of an employee."""
    data = load(employee)
    if slug in data["steps"]:
        data["steps"][slug]["user_data"].update(user_data)
        save(employee, data)


def get_user_data(employee: str, slug: str) -> Dict[str, Any]:
    """Get user data for a specific step of an employee."""
    data = load(employee)
    return data["steps"][slug].get("user_data", {}) if slug in data["steps"] else {}


def list_statuses(employee: str) -> Dict[str, str]:
    """Get a dictionary of all step statuses for an employee."""
    return {k: v["status"] for k, v in load(employee)["steps"].items()}


def check_dependencies(employee: str, step_slug: str) -> bool:
    """Check if all dependencies for a step are met."""
    data = load(employee)
    if step_slug not in data["steps"]:
        return False
    
    step = data["steps"][step_slug]
    dependencies = step.get("depends_on", [])
    
    for dep in dependencies:
        dep_slug = _slug(dep)
        if dep_slug not in data["steps"] or data["steps"][dep_slug]["status"] != "completed":
            return False
    
    return True


def get_blocked_steps(employee: str, step_slug: str) -> List[str]:
    """Get steps that are blocked by required_before constraints."""
    data = load(employee)
    if step_slug not in data["steps"]:
        return []
    
    step = data["steps"][step_slug]
    required_before = step.get("required_before", [])
    blocked = []
    
    for req in required_before:
        req_slug = _slug(req)
        if req_slug in data["steps"] and data["steps"][req_slug]["status"] != "completed":
            blocked.append(req_slug)
    
    return blocked
