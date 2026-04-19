from datetime import datetime
from ..database import SessionLocal
from ..models.db_models import SimulatedEmail

def send_pin_email(target_email: str, pin: str):
    """
    Simulates sending a password reset PIN by saving it to the local inbox.
    """
    db = SessionLocal()
    try:
        body = f"Hello,\n\nYour password reset PIN is: {pin}\n\nThis PIN will expire in 15 minutes.\n\nIf you did not request this reset, please ignore this email."
        
        sim_email = SimulatedEmail(
            recipient=target_email,
            subject="Password Reset PIN - Diagram AI",
            body=body
        )
        db.add(sim_email)
        db.commit()
        print(f"DEBUG: Local Email 'Sent' to {target_email} (PIN: {pin})")
        return True
    except Exception as e:
        print(f"Error saving simulated email: {e}")
        db.rollback()
        return False
    finally:
        db.close()

def send_welcome_email(target_email: str, username: str):
    """
    Simulates sending a welcome email by saving it to the local inbox.
    """
    db = SessionLocal()
    try:
        body = f"Hello {username},\n\nWelcome to Diagram AI! We're excited to have you on board.\n\nYou can now start creating diagrams from text and generating code automatically.\n\nHappy Diagramming!\nThe Diagram AI Team"
        
        sim_email = SimulatedEmail(
            recipient=target_email,
            subject="Welcome to Diagram AI!",
            body=body
        )
        db.add(sim_email)
        db.commit()
        print(f"DEBUG: Local Welcome Email 'Sent' to {target_email}")
        return True
    except Exception as e:
        print(f"Error saving simulated welcome email: {e}")
        db.rollback()
        return False
    finally:
        db.close()
