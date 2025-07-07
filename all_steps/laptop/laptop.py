from typing import Tuple, Dict, Any
import progress_store as store


# Laptop vendor configurations
LAPTOP_VENDORS = {
    "1": {"name": "Best Buy", "url": "www.bestbuy.com", "price": "$899"},
    "2": {"name": "Amazon", "url": "www.amazon.com", "price": "$1299"},
    "3": {"name": "Walmart", "url": "www.walmart.com", "price": "$599"}
}


def should_show_laptop_step(employee_name: str) -> bool:
    """Check if laptop step should start."""
    progress = store.load(employee_name)
    return progress["steps"].get("account_verification_and_setup", {}).get("status") == "completed" and progress["steps"].get("choose_your_laptop", {}).get("status") == "not_started"


def handle_laptop_interaction(user_message: str, employee_name: str, session_data: Dict[str, Any]) -> Tuple[str, bool]:
    """Handle all laptop purchase interactions."""
    if not should_show_laptop_step(employee_name):
        return "", False
    
    current_step = session_data.get('laptop_step')
    
    # Show laptop options
    if not current_step:
        session_data['laptop_step'] = 'choosing'
        options = ["Choose Your Laptop:\n"]
        for choice, vendor in LAPTOP_VENDORS.items():
            options.append(f"{choice}. {vendor['name']} - {vendor['url']} ({vendor['price']})")
        
        options.append("\nType 1, 2, or 3 to choose.")
        return "\n".join(options), True
    
    # Handle laptop choice
    if current_step == 'choosing':
        choice = user_message.strip()
        if choice in LAPTOP_VENDORS:
            session_data.pop('laptop_step', None)
            store.set_status(employee_name, "choose_your_laptop", "completed")
            return f"Laptop ordered from {LAPTOP_VENDORS[choice]['name']}! It will be handed to you.", True
        return "Please choose 1, 2, or 3.", True
    
    return "", False


def trigger_laptop_process(employee_name: str, session_data: Dict[str, Any]) -> str:
    """Trigger laptop process after account verification completion."""
    if should_show_laptop_step(employee_name):
        return handle_laptop_interaction("", employee_name, session_data)[0]
    return "" 