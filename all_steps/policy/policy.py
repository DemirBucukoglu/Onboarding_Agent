from typing import Tuple, Dict, Any
import progress_store as store


def should_show_policy_step(employee_name: str) -> bool:
    """Check if policy step should start."""
    progress = store.load(employee_name)
    return progress["steps"].get("team_introduction_notifications", {}).get("status") == "completed" and progress["steps"].get("receive_policy_book_and_setup_q_a_access", {}).get("status") == "not_started"


def handle_policy_interaction(user_message: str, employee_name: str, session_data: Dict[str, Any]) -> Tuple[str, bool]:
    """Handle policy book and Q&A access interactions."""
    if not should_show_policy_step(employee_name):
        return "", False
    
    # Auto-complete the final step
    session_data.pop('policy_step', None)
    store.set_status(employee_name, "receive_policy_book_and_setup_q_a_access", "completed")
    
    return """CONGRATULATIONS!\n\nFINAL STEP: Policy Book & Q&A Access\n\n<a href="/download_policy_book" download style="background-color: #6c757d; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; font-weight: bold; display: inline-block; margin: 10px 0;">Download Company Policy Book</a>\n\nYou can ask questions now.\n\nYOU'VE COMPLETED ALL ONBOARDING STEPS!\n\nWelcome to the team! If you have any other questions, feel free to ask!""", True


def trigger_policy_process(employee_name: str, session_data: Dict[str, Any]) -> str:
    """Trigger policy process after team introduction completion."""
    if should_show_policy_step(employee_name):
        return handle_policy_interaction("", employee_name, session_data)[0]
    return "" 