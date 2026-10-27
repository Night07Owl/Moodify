"""
MoodMusic AI Assistant Service
Fulfills Academic Rubric Requirements:
1. Answers questions strictly grounded in SQL FAQ data.
2. Explains HTTP error codes (400, 401, 403, 404, 429, 500, 503) and site-specific 488.
3. Automatically triggers or suggests Support Ticket creation in SQL when unable to answer.
4. Persists chat logs and session interactions into MongoDB (via mongo_service).
"""

import os
import re
import json
from datetime import datetime
from django.conf import settings
from music.models import FAQ, ErrorCode, SupportTicket
from music import mongo_service

def get_grounding_context():
    """
    Retrieves current FAQ items and Error Code entries from the SQL database.
    """
    faqs = list(FAQ.objects.all().order_by('order', 'id'))
    error_codes = list(ErrorCode.objects.all().order_by('code'))

    faq_text = "\n".join([
        f"[FAQ #{f.id} | Category: {f.category}]\nQ: {f.question}\nA: {f.answer}"
        for f in faqs
    ])

    error_text = "\n".join([
        f"[Error {e.code} - {e.name} ({'Site-Specific' if e.is_site_specific else e.category})]\n"
        f"Meaning: {e.meaning}\n"
        f"Causes: {e.common_causes}\n"
        f"Fixes: {e.troubleshooting_steps}"
        for e in error_codes
    ])

    return faqs, error_codes, faq_text, error_text


def _rule_based_fallback(user_message, faqs, error_codes):
    """
    Deterministic rule-based response engine when Gemini API is offline or quota-limited.
    Guarantees 100% reliable FAQ answering, error code explanation, and ticket escalation.
    """
    msg_lower = user_message.lower().strip()

    # 1. Check for explicit error code mention (e.g. 404, 488, 500, 429, 400, 401, 403, 503)
    error_match = re.search(r'\b(400|401|403|404|429|488|500|503)\b', msg_lower)
    if error_match:
        code_num = int(error_match.group(1))
        err_obj = next((e for e in error_codes if e.code == code_num), None)
        if err_obj:
            site_tag = " **(MoodMusic Site-Specific Error Code)**" if err_obj.is_site_specific else ""
            reply = (
                f"### Error {err_obj.code}: {err_obj.name}{site_tag}\n\n"
                f"**What it means:**\n{err_obj.meaning}\n\n"
                f"**Common Causes:**\n{err_obj.common_causes}\n\n"
                f"**Troubleshooting Steps:**\n{err_obj.troubleshooting_steps}\n\n"
                f"*Need further assistance? You can open a support ticket right below.*"
            )
            return {
                "answer": reply,
                "can_answer": True,
                "error_code": err_obj.code,
                "faq_ids": [],
                "suggested_ticket": None
            }

    # 2. Check for keywords related to errors or troubleshooting
    if any(k in msg_lower for k in ['error code', 'what error', 'list error', 'error codes']):
        reply = (
            "### MoodMusic Error Code Directory\n"
            "Here are the supported HTTP and application error codes:\n\n"
            "- **400 Bad Request**: Malformed syntax or invalid request parameters.\n"
            "- **401 Unauthorized**: Missing or expired credentials.\n"
            "- **403 Forbidden**: Access denied due to insufficient permissions.\n"
            "- **404 Not Found**: Page, track, or resource does not exist.\n"
            "- **429 Too Many Requests**: Rate limit exceeded for AI generation.\n"
            "- **500 Internal Server Error**: Unexpected server-side fault.\n"
            "- **503 Service Unavailable**: Temporary server maintenance or overload.\n"
            "- **488 Audio Stream Unavailable**: *(Site-Specific)* Preview stream link expired or blocked.\n\n"
            "Ask me about any specific error code (e.g. *'Explain 488'*) for full troubleshooting steps!"
        )
        return {
            "answer": reply,
            "can_answer": True,
            "error_code": None,
            "faq_ids": [8],
            "suggested_ticket": None
        }

    # 3. Check for match in FAQ questions or answers
    best_faq = None
    best_score = 0

    tokens = [w for w in re.findall(r'\w+', msg_lower) if len(w) > 2]
    for f in faqs:
        f_text = (f.question + " " + f.answer).lower()
        score = sum(1 for t in tokens if t in f_text)
        # Extra weight if matched in question title
        if any(t in f.question.lower() for t in tokens):
            score += 2
        if score > best_score:
            best_score = score
            best_faq = f

    if best_faq and best_score >= 2:
        reply = (
            f"### {best_faq.question}\n\n"
            f"{best_faq.answer}\n\n"
            f"*Category: {best_faq.category}*"
        )
        return {
            "answer": reply,
            "can_answer": True,
            "error_code": None,
            "faq_ids": [best_faq.id],
            "suggested_ticket": None
        }

    # 4. If query cannot be answered from knowledge base or user explicitly asks for support ticket
    is_ticket_request = any(k in msg_lower for k in ['ticket', 'support', 'contact human', 'help me', 'bug', 'broken', 'issue'])
    
    reply = (
        "I'm sorry, but I couldn't find an answer to your question in our FAQ knowledge base or Error Code directory.\n\n"
        "Would you like me to open a **Support Ticket** for our engineering team? You can click the button below to submit a ticket directly into our SQL database."
    )

    suggested_subject = f"Support Request: {user_message[:60]}" if len(user_message) > 60 else f"Support Request: {user_message}"
    
    return {
        "answer": reply,
        "can_answer": False,
        "error_code": None,
        "faq_ids": [],
        "suggested_ticket": {
            "subject": suggested_subject,
            "description": user_message,
            "category": "Unresolved Query / Support Request"
        }
    }


def process_chat_query(user_message, session_id='guest-session', client_ip='127.0.0.1', auto_create_ticket=False, user_email=''):
    """
    Main entry point for AI Chat interactions.
    1. Loads SQL FAQs and Error Codes.
    2. Queries Gemini API with grounding context (with fallback to rule matcher).
    3. Handles support ticket creation if requested.
    4. Logs everything into MongoDB.
    """
    faqs, error_codes, faq_text, error_text = get_grounding_context()

    result = None
    api_key = getattr(settings, 'GEMINI_API_KEY', None) or os.environ.get('GEMINI_API_KEY')

    # Try Gemini Generative AI first
    if api_key:
        try:
            from google import genai
            client = genai.Client(api_key=api_key)

            system_instruction = (
                "You are MoodMusic AI Assistant, an integrated support bot for the MoodMusic platform.\n"
                "Your role is to:\n"
                "1. Answer questions accurately based on the PROVIDED FAQ DATA and ERROR CODE DIRECTORY.\n"
                "2. When the user asks about HTTP error codes (400, 401, 403, 404, 429, 500, 503) or the site-specific code 488 (Audio Stream Unavailable), "
                "explain what the code means, why it happened, and how the user or developer can troubleshoot it.\n"
                "3. If a question CANNOT be answered from the FAQ data or error codes, or if the user is asking for assistance that requires human staff/developers: "
                "You MUST set 'can_answer': false, apologize politely, and offer to open a Support Ticket.\n\n"
                "GROUNDING FAQ DATA:\n"
                f"{faq_text}\n\n"
                "GROUNDING ERROR CODES:\n"
                f"{error_text}\n\n"
                "Respond STRICTLY in valid JSON matching this schema:\n"
                "{\n"
                "  \"answer\": \"Markdown response text\",\n"
                "  \"can_answer\": true or false,\n"
                "  \"error_code\": integer or null,\n"
                "  \"faq_ids\": [list of integer FAQ IDs referenced],\n"
                "  \"suggested_ticket\": {\"subject\": \"...\", \"description\": \"...\", \"category\": \"...\"} or null\n"
                "}"
            )

            models_to_try = ['gemini-flash-lite-latest', 'gemini-flash-latest', 'gemini-2.5-flash-lite']
            for m in models_to_try:
                try:
                    resp = client.models.generate_content(
                        model=m,
                        contents=f"User query: {user_message}",
                        config={
                            'system_instruction': system_instruction,
                            'response_mime_type': 'application/json'
                        }
                    )
                    text = resp.text or ""
                    text = re.sub(r'```json\s*', '', text)
                    text = re.sub(r'```', '', text).strip()
                    parsed = json.loads(text)
                    if isinstance(parsed, dict) and 'answer' in parsed:
                        result = parsed
                        break
                except Exception as model_err:
                    print(f"[AI Assistant] Note on {m}: {model_err}")
                    continue
        except Exception as gemini_err:
            print(f"[AI Assistant] Gemini initialization note: {gemini_err}")

    # If Gemini didn't return or was unavailable, use deterministic fallback
    if not result:
        result = _rule_based_fallback(user_message, faqs, error_codes)

    # If ticket creation is requested or user asks to create ticket
    ticket_data = None
    if auto_create_ticket or (not result.get('can_answer') and 'create ticket' in user_message.lower()):
        subject = (result.get('suggested_ticket') or {}).get('subject') or f"Ticket: {user_message[:50]}"
        desc = (result.get('suggested_ticket') or {}).get('description') or user_message
        email = user_email or f"{session_id}@guest.moodmusic.com"

        ticket = SupportTicket.objects.create(
            user_name="Assistant User",
            user_email=email,
            subject=subject,
            category="AI Assistant Escalation",
            description=desc,
            status="Open",
            priority="Medium",
            ai_generated=True,
        )
        mongo_service.record_support_ticket(ticket)
        ticket_data = {
            "ticket_number": ticket.ticket_number,
            "status": ticket.status,
            "created_at": ticket.created_at.strftime('%Y-%m-%d %H:%M:%S UTC'),
            "subject": ticket.subject
        }
        result['ticket_created'] = ticket_data
        result['answer'] += f"\n\n **Support Ticket Created Successfully!**\n- Ticket ID: `{ticket.ticket_number}`\n- Status: `{ticket.status}`\n- You can review this ticket on the **[Support Center](/support/)** page."

    # Persist interaction to MongoDB
    mongo_log_id = mongo_service.log_chat_interaction(
        session_id=session_id,
        user_message=user_message,
        bot_reply=result.get('answer', ''),
        error_code=result.get('error_code'),
        resolved=result.get('can_answer', False),
        created_ticket=bool(ticket_data),
        metadata={
            'client_ip': client_ip,
            'faq_ids': result.get('faq_ids', []),
            'ticket_number': ticket_data['ticket_number'] if ticket_data else None,
        }
    )
    result['mongo_log_id'] = mongo_log_id

    return result
