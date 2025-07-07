import json
from typing import Dict, Optional, Tuple
import progress_store as store


def load_quiz_config() -> Optional[Dict]:
    """Load quiz configuration from steps.json."""
    try:
        with open('steps.json', 'r') as f:
            for step in json.load(f):
                if step.get('type') == 'video_training' and 'quiz_questions' in step.get('config', {}):
                    return step['config']
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error loading quiz config: {e}")
    return None


def get_video_training_message(employee_name: str, step_slug: str) -> str:
    """Generate HTML message for video training step."""
    return f"""
    <div class="video-training">
        <h3>Code of Conduct Training</h3>
        <p>Please watch this important training video about our company's code of conduct:</p>
        
        <div class="video-container" style="margin: 15px 0; text-align: center;">
            <video controls width="100%" style="max-width: 500px; border-radius: 8px;">
                <source src="/video/Code%20of%20Conduct%20training%20video.mp4" type="video/mp4">
                Your browser does not support the video tag.
                <p>Video not available. Please contact IT support.</p>
            </video>
        </div>
        
        <p><strong>After watching the video, I'll ask you some questions to test your understanding.</strong></p>
    </div>
    """


def should_show_code_of_conduct_training(employee_name: str) -> bool:
    """Check if the code of conduct training should be shown."""
    return store.load(employee_name)["steps"].get("complete_code_of_conduct_training", {}).get("status") == "not_started"


def complete_code_of_conduct_training(employee_name: str) -> str:
    """Mark the code of conduct training as completed."""
    store.set_status(employee_name, "complete_code_of_conduct_training", "completed")
    return "Excellent. I have marked your Code of Conduct training as completed. You can now proceed with your account verification."


def handle_code_of_conduct_interaction(user_message: str, employee_name: str, session_data: Dict) -> Tuple[str, bool]:
    """Handle all Code of Conduct interactions."""
    config = load_quiz_config()
    if not config:
        return "", False
    
    message_lower = user_message.lower()
    user_answer = user_message.strip().upper()
    
    # Check for quiz start keywords
    start_keywords = ["ask me the question", "ask me the questions", "start the quiz", 
                     "lets start", "let's start", "ask me", "quiz", "question"]
    
    if any(phrase in message_lower for phrase in start_keywords) and should_show_code_of_conduct_training(employee_name):
        session_data.update({'in_quiz': True, 'quiz_question': 1, 'quiz_score': 0})
        q = config['quiz_questions'][0]
        return f"Question 1 of {len(config['quiz_questions'])}: {q['question']}\n" + "\n".join(q['options']) + "\n\nPlease answer with A, B, C, or D.", True
    
    # Process quiz answers
    if session_data.get('in_quiz') and user_answer in ['A', 'B', 'C', 'D']:
        current_q = session_data.get('quiz_question', 1)
        questions = config['quiz_questions']
        answer_key = config.get('answer_key', {})
        correct = user_answer == answer_key.get(str(current_q))
        if correct:
            session_data['quiz_score'] = session_data.get('quiz_score', 0) + 1
        
        if current_q >= len(questions):
            score = session_data.get('quiz_score', 0)
            percentage = (score / len(questions)) * 100
            session_data.pop('in_quiz', None)
            session_data.pop('quiz_question', None)
            session_data.pop('quiz_score', None)
            if percentage >= config.get('passing_score', 80):
                return f"Congratulations! You have successfully passed with {score}/{len(questions)} ({percentage:.0f}%). COMPLETE_CODE_OF_CONDUCT_TRAINING TRIGGER_ID_STEP", True
            else:
                return f"You scored {score}/{len(questions)} ({percentage:.0f}%). Please review the material and try again. Type 'start quiz' to retry.", True
        
        session_data['quiz_question'] = current_q + 1
        q = questions[current_q]
        feedback = "Correct! " if correct else f"Incorrect. {questions[current_q-1].get('explanation', '')} "
        return feedback + f"Question {current_q + 1} of {len(questions)}: {q['question']}\n" + "\n".join(q['options']) + "\n\nPlease answer with A, B, C, or D.", True
    
    return "", False 