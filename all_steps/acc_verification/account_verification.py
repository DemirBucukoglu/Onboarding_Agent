
import random, string
from typing import Tuple, Dict, Any
import progress_store as store


def should_show_account_step(employee_name: str) -> bool:
    """Check if account verification step should start."""
    progress = store.load(employee_name)
    return progress["steps"].get("get_id_badge", {}).get("status") == "completed" and progress["steps"].get("account_verification_and_setup", {}).get("status") == "not_started"


def generate_random_password(length: int = 8) -> str:
    """Generate a random one-time password."""
    return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(length))


def create_company_email(name: str) -> str:
    """Create company email from user's name."""
    username = ''.join(c for c in name.lower().replace(' ', '.') if c.isalnum() or c == '.')
    return f"{username}@company.com"


def handle_account_interaction(user_message: str, employee_name: str, session_data: Dict[str, Any]) -> Tuple[str, bool]:
    """Handle all account verification interactions."""
    current_step = session_data.get('account_step')
    
    # Check for explicit account verification request
    account_keywords = ["account verification", "account setup", "email", "password", "credentials"]
    if any(phrase in user_message.lower() for phrase in account_keywords):
        if should_show_account_step(employee_name):
            session_data['account_step'] = 'asking_name'
            return "Account Verification and Setup\n\nTo create your company account, please provide your full name:", True
    
    # Start account verification process automatically
    if not current_step and should_show_account_step(employee_name):
        session_data['account_step'] = 'asking_name'
        return "Account Verification and Setup\n\nTo create your company account, please provide your full name:", True
    
    # Process user's name input
    if current_step == 'asking_name':
        user_name = user_message.strip()
        if user_name and len(user_name) > 1:  # Basic validation
            session_data.pop('account_step', None)
            store.set_status(employee_name, "account_verification_and_setup", "completed")
            company_email = create_company_email(user_name)
            one_time_password = generate_random_password()
            session_data.update({'user_name': user_name, 'company_email': company_email, 'password': one_time_password})
            return f"Account Created Successfully!\n\nYour Company Account Details:\nEmail: {company_email}\nOne-Time Password: {one_time_password}\n\nPlease save these credentials for your records. Account verification is now complete!", True
        else:
            return "Please provide a valid full name.", True
    
    return "", False


def trigger_account_process(employee_name: str, session_data: Dict[str, Any]) -> str:
    """Trigger account verification process after ID completion."""
    if should_show_account_step(employee_name):
        session_data['account_step'] = 'asking_name'
        return "Account Verification and Setup\n\nTo create your company account, please provide your full name:"
    return "" 