import os
from typing import Tuple, Dict, Any
import progress_store as store


def should_show_id_step(employee_name: str) -> bool:
    """Check if ID step should start."""
    progress = store.load(employee_name)
    return progress["steps"].get("safety_information_collection", {}).get("status") == "completed" and progress["steps"].get("get_id_badge", {}).get("status") == "not_started"


def get_upload_form(upload_type: str) -> str:
    """Generate upload form for photo or ID badge."""
    if upload_type == "photo":
        return '<div style="background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 10px 0;"><h3>ID Badge Photo Upload</h3><p>Please upload your photo for your company ID badge:</p><form action="/upload_photo" method="post" enctype="multipart/form-data" style="margin: 10px 0;"><input type="file" name="photo" accept="image/*" required style="margin: 10px 0; padding: 10px; border: 1px solid #ccc; border-radius: 4px;"><button type="submit" style="background: #6c757d; color: white; padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer;">Upload Photo</button></form></div>'
    else:
        return '<div style="background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 10px 0;"><h3>Upload Your Completed ID Badge</h3><p>Please upload a photo of your completed ID badge as proof:</p><form action="/upload_id_proof" method="post" enctype="multipart/form-data" style="margin: 10px 0;"><input type="file" name="id_badge" accept="image/*" required style="margin: 10px 0; padding: 10px; border: 1px solid #ccc; border-radius: 4px;"><button type="submit" style="background: #6c757d; color: white; padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer;">Upload ID Badge</button></form></div>'


def save_file(file, employee_name: str, file_type: str) -> bool:
    """Save uploaded file (photo or ID badge)."""
    try:
        photos_dir = os.path.join("all_steps", "ID", "photos")
        os.makedirs(photos_dir, exist_ok=True)
        
        # Create safe filename
        safe_name = employee_name.replace(' ', '_').replace('/', '_').replace('\\', '_')
        filename = f"{safe_name}_{file_type}.jpg"
        file_path = os.path.join(photos_dir, filename)
        
        file.save(file_path)
        return True
    except Exception as e:
        print(f"Error saving {file_type} for {employee_name}: {e}")
        return False


def handle_id_interaction(user_message: str, employee_name: str, session_data: Dict[str, Any]) -> Tuple[str, bool]:
    """Handle all ID interactions."""
    message_lower = user_message.lower()
    current_step = session_data.get('id_step')
    
    # Handle photo upload completion
    if current_step == 'upload' and 'photo uploaded successfully' in message_lower:
        session_data['id_step'] = 'waiting_for_id'
        response = ("Thank you. I have sent your photo to the ID department. "
                   "Once you have your ID badge, please upload it here as proof.\n\n" + 
                   get_upload_form("id_badge"))
        return response, True
    
    # Handle ID proof upload completion
    if current_step == 'waiting_for_id' and 'id proof uploaded successfully' in message_lower:
        session_data.pop('id_step', None)
        store.set_status(employee_name, "get_id_badge", "completed")
        return "Excellent. ID badge step completed. Your ID badge has been verified and recorded.", True
    
    # Start ID process
    if not current_step and should_show_id_step(employee_name):
        session_data['id_step'] = 'upload'
        return get_upload_form("photo"), True
    
    return "", False


def trigger_id_process(employee_name: str, session_data: Dict[str, Any]) -> str:
    """Trigger ID process after quiz completion."""
    if should_show_id_step(employee_name):
        session_data['id_step'] = 'upload'
        return get_upload_form("photo")
    return "" 