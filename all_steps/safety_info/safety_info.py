import json
import os
from datetime import datetime
from typing import Tuple, Dict, Any
import progress_store as store


def save_phone_number(employee_name: str, phone: str) -> None:
    """Save employee phone number to JSON file."""
    json_path = os.path.join(os.path.dirname(__file__), "phonenumber.json")
    
    try:
        with open(json_path, 'r') as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        data = {"employees": {}, "metadata": {"total_records": 0}}
    
    data["employees"][employee_name] = {
        "phone_number": phone,
        "collected_date": datetime.now().isoformat()
    }
    data["metadata"]["total_records"] = len(data["employees"])
    data["metadata"]["last_updated"] = datetime.now().isoformat()
    
    with open(json_path, 'w') as f:
        json.dump(data, f, indent=2)


def should_show_safety_step(employee_name: str) -> bool:
    """Check if safety information step should start."""
    progress = store.load(employee_name)
    return progress["steps"].get("complete_code_of_conduct_training", {}).get("status") == "completed" and progress["steps"].get("safety_information_collection", {}).get("status") == "not_started"


def handle_safety_interaction(user_message: str, employee_name: str, session_data: Dict[str, Any]) -> Tuple[str, bool]:
    """Handle safety information interactions."""
    current_step = session_data.get('safety_step')
    
    # Start safety information collection
    if not current_step and should_show_safety_step(employee_name):
        session_data['safety_step'] = 'asking_phone'
        return "Safety Information\n\nBefore you start your onboarding, let's keep you safe first!\n\nPlease provide your phone number:", True
    
    # Process phone number input and complete
    if current_step == 'asking_phone':
        phone_number = user_message.strip()
        if phone_number and len(phone_number) >= 10:
            session_data.pop('safety_step', None)
            store.set_status(employee_name, "safety_information_collection", "completed")
            save_phone_number(employee_name, phone_number)
            return f"Phone number saved: {phone_number}\n\nYour safety information has been recorded. SAFETY_INFO_COMPLETE", True
        else:
            return "Please provide a valid phone number.", True
    
    return "", False


def trigger_safety_process(employee_name: str, session_data: Dict[str, Any]) -> str:
    """Trigger safety information process after code of conduct completion."""
    if should_show_safety_step(employee_name):
        session_data['safety_step'] = 'asking_phone'
        return "Safety Information\n\nBefore you start your onboarding, let's keep you safe first!\n\nPlease provide your phone number:"
    return "" 