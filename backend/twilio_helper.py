import os
from twilio.rest import Client

from twilio.base.exceptions import TwilioRestException
import logging

logger = logging.getLogger(__name__)

def build_sms_body(hospital_name, hospital_phone, hospital_address, alert_id, urgency_level):
    urgency_text = {1: "CRITICAL", 2: "URGENT", 3: "ROUTINE"}.get(urgency_level, "")
    short_id = alert_id[:8].upper()
    return (
        f"AEGIS Health Alert [{short_id}]\n"
        f"Status: {urgency_text}\n"
        f"{hospital_name} has received your triage alert.\n"
        f"Address: {hospital_address}\n"
        f"Contact: {hospital_phone}\n"
        f"Show this SMS or your PDF QR code at reception."
    )

def send_acknowledgement_sms(patient_phone: str, alert_id: str, db):
    alert = db.execute("""
        SELECT a.*, h.name as hospital_name, h.phone as hospital_phone,
               h.address as hospital_address
        FROM alerts a
        JOIN hospitals h ON a.hospital_id = h.id
        WHERE a.id = ?
    """, (alert_id,)).fetchone()

    if not alert:
        return False

    hospital_name = alert["hospital_name"]
    hospital_phone = alert["hospital_phone"] or "Not available"
    hospital_address = alert["hospital_address"] or "Not available"
    urgency_level = alert["urgency_level"]

    message = build_sms_body(hospital_name, hospital_phone, hospital_address, alert_id, urgency_level)

    account_sid = os.environ.get('TWILIO_ACCOUNT_SID')
    auth_token = os.environ.get('TWILIO_AUTH_TOKEN')
    from_number = os.environ.get('TWILIO_PHONE_NUMBER')

    if not account_sid or not auth_token or not from_number:
        print("--------------------------------------------------")
        print("MOCK SMS (Twilio not configured)")
        print(f"To: {patient_phone}")
        print(f"Body:\n{message}")
        print("--------------------------------------------------")
        return False

    try:
        client = Client(account_sid, auth_token)
        client.messages.create(
            body=message,
            from_=from_number,
            to=patient_phone
        )
        return True
    except TwilioRestException as e:
        if e.status == 429:
            logger.warning(f"Twilio rate limit hit for alert {alert_id}")
        else:
            logger.error(f"SMS failed: {e}")
        return False
    except Exception as e:
        logger.error(f"Error sending SMS via Twilio: {e}")
        return False
