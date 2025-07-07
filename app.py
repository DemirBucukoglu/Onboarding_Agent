import os, asyncio, time
from typing import Dict, List, Tuple, Optional
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory
from dotenv import load_dotenv
import semantic_kernel as sk
from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion, OpenAIChatPromptExecutionSettings
from semantic_kernel.contents.chat_history import ChatHistory
import progress_store as store
from pdf.pdfreader import build_memory, ingest_pdf
from all_steps.code_of_conduct.quiz_handler import get_video_training_message, should_show_code_of_conduct_training, complete_code_of_conduct_training, handle_code_of_conduct_interaction
from all_steps.safety_info.safety_info import handle_safety_interaction, trigger_safety_process
from all_steps.ID.ID import handle_id_interaction, trigger_id_process, save_file
from all_steps.acc_verification.account_verification import handle_account_interaction, trigger_account_process
from all_steps.laptop.laptop import handle_laptop_interaction, trigger_laptop_process
from all_steps.mentor_and_team.mentor import handle_mentor_interaction, trigger_mentor_process
from all_steps.policy.policy import handle_policy_interaction, trigger_policy_process

load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'your-secret-key-here')
kernel = sk.Kernel()
kernel.add_service(OpenAIChatCompletion(ai_model_id=os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini"), service_id="chat"))
memory = build_memory()
chat = kernel.get_service("chat")
settings = OpenAIChatPromptExecutionSettings(service_id="chat", temperature=0.2, max_tokens=800)
APP_START_TIME = time.time()
memory_initialized = False

def find_matching_step(user_input: str, progress_steps: Dict) -> Optional[str]:
    for step_config in store.load_steps_config():
        step_slug = store._slug(step_config["title"])
        if step_slug in progress_steps and any(keyword.lower() in user_input.lower() for keyword in step_config.get("keywords", [])):
            return step_slug
    return None

def initialize_memory() -> None:
    global memory_initialized
    if not memory_initialized:
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(ingest_pdf("pdf/policy_book.pdf", memory))
            loop.close()
            memory_initialized = True
        except Exception as e:
            print(f"Error initializing memory: {e}")

def create_welcome_messages(employee_name: str) -> List[Dict[str, str]]:
    if should_show_code_of_conduct_training(employee_name):
        return [{'sender': 'assistant', 'message': f"Welcome to our company, {employee_name}. To proceed with your onboarding process, please complete the mandatory Code of Conduct training. This is the first step in your comprehensive onboarding journey."},
                {'sender': 'assistant', 'message': get_video_training_message(employee_name, "complete_code_of_conduct_training")}]
    return [{'sender': 'assistant', 'message': f"Welcome to our company, {employee_name}. I am your onboarding assistant and will guide you through the onboarding process while tracking your progress. Please let me know how I can assist you today."}]

def process_step_interaction(user_message: str, employee_name: str, session: Dict) -> Tuple[str, bool, Optional[str]]:
    handlers = [(handle_code_of_conduct_interaction, complete_code_of_conduct_training, trigger_safety_process, "COMPLETE_CODE_OF_CONDUCT_TRAINING"),
                (handle_safety_interaction, None, trigger_id_process, "SAFETY_INFO_COMPLETE"),
                (handle_id_interaction, None, trigger_account_process, "ID badge step completed"),
                (handle_account_interaction, None, trigger_laptop_process, "Account verification is now complete"),
                (handle_laptop_interaction, None, trigger_mentor_process, "Laptop ordered from"),
                (handle_mentor_interaction, None, trigger_policy_process, "Team Introduction Complete!"),
                (handle_policy_interaction, None, None, None)]
    
    for handler, completion_func, next_trigger, completion_marker in handlers:
        response, handled = handler(user_message, employee_name, session)
        if handled:
            if completion_marker and completion_marker in response:
                if completion_func:
                    completion_func(employee_name)
                response = response.replace("COMPLETE_CODE_OF_CONDUCT_TRAINING", "").replace("TRIGGER_ID_STEP", "").strip()
                if next_trigger:
                    next_step_message = next_trigger(employee_name, session)
                    if next_step_message:
                        response = f"{response}\n\n{next_step_message}"
                return response, True, None
            return response, True, None
    return "", False, None

async def get_ai_response(employee_name: str, user_message: str) -> str:
    statuses = store.list_statuses(employee_name)
    progress_context = ", ".join(f"{k}:{v}" for k, v in statuses.items())
    try:
        policy_hits = await memory.search(collection="policy-book", query=user_message, limit=4, min_relevance_score=0.6)
        handbook_context = "\n---\n".join(f"Handbook: {hit.text}" for hit in policy_hits) if policy_hits else "No relevant handbook information found."
    except:
        handbook_context = "Handbook search unavailable."
    history = ChatHistory(system_message=f"You are a professional onboarding assistant for {employee_name}. Your role is to help track progress and provide accurate information using the company handbook. Guidelines: Maintain a professional tone, provide concise and helpful responses, and only reference verified progress information. Utilize handbook content when available to provide comprehensive assistance.")
    history.add_user_message(f"[Progress] {progress_context}\n[Handbook] {handbook_context}\n\nEmployee: {user_message}")
    reply = await chat.get_chat_message_content(history, settings=settings)
    return reply.content.strip()

def handle_file_upload(file_field: str, success_message: str, save_function, file_type: str = 'photo'):
    if 'employee_name' not in session:
        return redirect(url_for('index'))
    if file_field not in request.files or request.files[file_field].filename == '':
        flash(f'No {file_type} selected')
        return redirect(url_for('index'))
    file = request.files[file_field]
    employee_name = session['employee_name']
    if save_function(file, employee_name, file_type):
        # Process the file upload through the step interaction system
        response, handled, next_message = process_step_interaction(success_message, employee_name, session)
        if handled:
            chat_history = session.get('chat_history', [])
            chat_history.append({'sender': 'assistant', 'message': response})
            if next_message:
                chat_history.append({'sender': 'assistant', 'message': next_message})
            session['chat_history'] = chat_history
        flash(f'{file_type.title()} uploaded successfully!')
    else:
        flash(f'Error uploading {file_type}. Please try again.')
    return redirect(url_for('index'))

@app.route('/')
def index():
    if session.get('app_start_time', 0) < APP_START_TIME:
        session.clear()
        return render_template('index.html')
    if 'employee_name' not in session:
        return render_template('index.html')
    employee_name = session['employee_name']
    progress = store.load(employee_name)
    chat_history = session.get('chat_history', [])
    return render_template('index.html', progress=progress, chat_history=chat_history)

@app.route('/start', methods=['POST'])
def start_session():
    employee_name = request.form.get('employee_name', '').strip()
    if not employee_name:
        flash('Please enter your name')
        return redirect(url_for('index'))
    session['employee_name'] = employee_name
    session['app_start_time'] = APP_START_TIME
    initialize_memory()
    session['chat_history'] = create_welcome_messages(employee_name)
    return redirect(url_for('index'))

@app.route('/chat', methods=['POST'])
def chat_message():
    if 'employee_name' not in session:
        return redirect(url_for('index'))
    user_message = request.form.get('message', '').strip()
    if not user_message:
        return redirect(url_for('index'))
    employee_name = session['employee_name']
    chat_history = session.get('chat_history', [])
    chat_history.append({'sender': 'user', 'message': user_message})
    
    response, handled, next_message = process_step_interaction(user_message, employee_name, session)
    if handled:
        chat_history.append({'sender': 'assistant', 'message': response})
        if next_message:
            chat_history.append({'sender': 'assistant', 'message': next_message})
        session['chat_history'] = chat_history
        return redirect(url_for('index'))
    
    completion_phrases = ["i done", "i did", "i finished", "i completed", "finished", "completed"]
    if any(phrase in user_message.lower() for phrase in completion_phrases):
        progress = store.load(employee_name)
        matching_step = find_matching_step(user_message, progress["steps"])
        if matching_step:
            store.set_status(employee_name, matching_step, "completed")
            step_title = progress["steps"][matching_step]["title"]
            chat_history.append({'sender': 'assistant', 'message': f"Excellent. I have marked '{step_title}' as completed in your onboarding progress."})
            session['chat_history'] = chat_history
            return redirect(url_for('index'))
    
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        response = loop.run_until_complete(get_ai_response(employee_name, user_message))
        loop.close()
        chat_history.append({'sender': 'assistant', 'message': response})
    except Exception as e:
        print(f"Error getting AI response: {e}")
        chat_history.append({'sender': 'assistant', 'message': "I apologize, but I encountered a technical error. Please try your request again."})
    
    session['chat_history'] = chat_history
    return redirect(url_for('index'))

@app.route('/video/<path:filename>')
def serve_video(filename):
    return send_from_directory('all_steps/code_of_conduct', filename)

@app.route('/upload_photo', methods=['POST'])
def upload_photo():
    return handle_file_upload('photo', 'photo uploaded successfully', save_file)

@app.route('/upload_id_proof', methods=['POST'])
def upload_id_proof():
    return handle_file_upload('id_badge', 'id proof uploaded successfully', save_file, 'id_badge')

@app.route('/download_policy_book')
def download_policy_book():
    if 'employee_name' not in session:
        return redirect(url_for('index'))
    return send_from_directory('pdf', 'policy_book.pdf', as_attachment=True, download_name='Company_Policy_Book.pdf')

if __name__ == '__main__':
    app.run(debug=True, port=5000) 