from typing import Tuple, Dict, Any, List
import progress_store as store

# Configuration
DEFAULT_MENTOR = "Alex"
TEAM_MEMBERS = [
    "john.doe@company.com",
    "sarah.smith@company.com", 
    "mike.johnson@company.com",
    "alex.mentor@company.com",
    "emma.wilson@company.com"
]

def should_show_mentor_step(employee_name: str) -> bool:
    """Check if mentor assignment step should start."""
    progress = store.load(employee_name)
    return progress["steps"].get("choose_your_laptop", {}).get("status") == "completed" and progress["steps"].get("mentor_buddy_assignment", {}).get("status") == "not_started"

def should_show_team_step(employee_name: str) -> bool:
    """Check if team introduction step should start."""
    return store.load(employee_name)["steps"].get("team_introduction_notifications", {}).get("status") == "not_started"

def send_mentor_email(employee_name: str, mentor_name: str) -> None:
    """Send notification email to assigned mentor (placeholder implementation)."""
    print(f"Email sent to {mentor_name} about new employee {employee_name}")

def send_team_notifications(employee_name: str) -> None:
    """Send notifications to team members about new employee (placeholder implementation)."""
    print(f"Team notifications sent for new employee {employee_name}")

def handle_mentor_interaction(user_message: str, employee_name: str, session_data: Dict[str, Any]) -> Tuple[str, bool]:
    """Handle all mentor and team interactions."""
    if any(phrase in user_message.lower() for phrase in ["team", "team introduction", "team members", "notifications"]):
        if should_show_team_step(employee_name):
            store.set_status(employee_name, "team_introduction_notifications", "completed")
            email_list = "\n".join([f"• {email}" for email in TEAM_MEMBERS])
            return f"Team Introduction Complete!\n\nYour Team Members:\n{email_list}\n\nAll team members have been notified about you and will welcome you soon!", True
    
    if should_show_mentor_step(employee_name):
        session_data.pop('mentor_step', None)
        store.set_status(employee_name, "mentor_buddy_assignment", "completed")
        store.set_status(employee_name, "team_introduction_notifications", "completed")
        send_mentor_email(employee_name, DEFAULT_MENTOR)
        send_team_notifications(employee_name)
        email_list = "\n".join([f"• {email}" for email in TEAM_MEMBERS])
        return f"Mentor Assigned & Team Introduced!\n\nYour Mentor: {DEFAULT_MENTOR} - he will reach out to you soon!\n\nYour Team Members:\n{email_list}\n\nAll team members have been notified about you and will welcome you soon!\n\nTeam Introduction Complete!", True
    
    return "", False

def trigger_mentor_process(employee_name: str, session_data: Dict[str, Any]) -> str:
    """Trigger mentor process after laptop completion."""
    if should_show_mentor_step(employee_name):
        return handle_mentor_interaction("", employee_name, session_data)[0]
    return "" 