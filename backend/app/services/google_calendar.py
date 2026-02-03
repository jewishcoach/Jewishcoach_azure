"""
Google Calendar API integration service
"""
import os
import json
from datetime import datetime, timedelta
from typing import Optional
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# OAuth 2.0 scopes for Google Calendar
SCOPES = ['https://www.googleapis.com/auth/calendar.events']

# Note: You need to set these in .env:
# GOOGLE_CLIENT_ID=your_client_id
# GOOGLE_CLIENT_SECRET=your_client_secret
# GOOGLE_REDIRECT_URI=http://localhost:8000/api/calendar/google/callback


def create_oauth_url(user_id: int) -> str:
    """
    Create Google OAuth URL for user to authorize
    
    Returns the authorization URL that the user should visit
    """
    from google_auth_oauthlib.flow import Flow
    
    client_config = {
        "web": {
            "client_id": os.getenv("GOOGLE_CLIENT_ID"),
            "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/api/calendar/google/callback")]
        }
    }
    
    flow = Flow.from_client_config(
        client_config,
        scopes=SCOPES,
        redirect_uri=os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/api/calendar/google/callback")
    )
    
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        state=str(user_id),  # Pass user_id as state
        prompt='consent'  # Force consent to get refresh token
    )
    
    return authorization_url


def exchange_code_for_tokens(code: str) -> dict:
    """
    Exchange authorization code for access and refresh tokens
    """
    from google_auth_oauthlib.flow import Flow
    
    client_config = {
        "web": {
            "client_id": os.getenv("GOOGLE_CLIENT_ID"),
            "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/api/calendar/google/callback")]
        }
    }
    
    flow = Flow.from_client_config(
        client_config,
        scopes=SCOPES,
        redirect_uri=os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/api/calendar/google/callback")
    )
    
    flow.fetch_token(code=code)
    credentials = flow.credentials
    
    return {
        "token": credentials.token,
        "refresh_token": credentials.refresh_token,
        "token_uri": credentials.token_uri,
        "client_id": credentials.client_id,
        "client_secret": credentials.client_secret,
        "scopes": credentials.scopes
    }


def get_credentials_from_tokens(token_data: dict) -> Credentials:
    """
    Create Credentials object from stored tokens
    """
    credentials = Credentials(
        token=token_data.get("token"),
        refresh_token=token_data.get("refresh_token"),
        token_uri=token_data.get("token_uri"),
        client_id=token_data.get("client_id"),
        client_secret=token_data.get("client_secret"),
        scopes=token_data.get("scopes")
    )
    
    # Refresh if expired
    if credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())
    
    return credentials


async def sync_to_google_calendar(
    user_token_data: str,
    reminders: list,
    past_sessions: list
) -> dict:
    """
    Sync reminders and past coaching sessions to Google Calendar
    
    Args:
        user_token_data: JSON string of user's Google OAuth tokens
        reminders: List of reminder objects
        past_sessions: List of past coaching session objects
    
    Returns:
        dict with sync status and counts
    """
    try:
        token_dict = json.loads(user_token_data)
        credentials = get_credentials_from_tokens(token_dict)
        
        service = build('calendar', 'v3', credentials=credentials)
        
        events_created = 0
        events_skipped = 0
        
        # Sync reminders
        for reminder in reminders:
            try:
                event = {
                    'summary': reminder.title,
                    'description': reminder.description or 'תזכורת לאימון',
                    'start': {
                        'dateTime': reminder.reminder_date.isoformat(),
                        'timeZone': 'Asia/Jerusalem',
                    },
                    'end': {
                        'dateTime': (reminder.reminder_date + timedelta(hours=1)).isoformat(),
                        'timeZone': 'Asia/Jerusalem',
                    },
                    'reminders': {
                        'useDefault': False,
                        'overrides': [
                            {'method': 'popup', 'minutes': 30},
                            {'method': 'email', 'minutes': 60},
                        ],
                    },
                    'source': {
                        'title': 'Jewish Coach AI',
                        'url': 'https://jewishcoach.ai'
                    }
                }
                
                # Handle recurring events
                if reminder.repeat_type != 'once':
                    rrule = _get_rrule(reminder.repeat_type, reminder.repeat_days)
                    if rrule:
                        event['recurrence'] = [rrule]
                
                service.events().insert(calendarId='primary', body=event).execute()
                events_created += 1
                
            except HttpError as e:
                print(f"Error creating reminder event: {e}")
                events_skipped += 1
        
        # Sync past coaching sessions
        for session in past_sessions:
            try:
                event = {
                    'summary': session.title or 'אימון עם בני',
                    'description': f'שיחת אימון • {len(session.messages)} הודעות • שלב: {session.current_phase}',
                    'start': {
                        'dateTime': session.created_at.isoformat(),
                        'timeZone': 'Asia/Jerusalem',
                    },
                    'end': {
                        'dateTime': (session.created_at + timedelta(minutes=30)).isoformat(),
                        'timeZone': 'Asia/Jerusalem',
                    },
                    'colorId': '10',  # Green color for completed sessions
                    'source': {
                        'title': 'Jewish Coach AI',
                        'url': 'https://jewishcoach.ai'
                    }
                }
                
                service.events().insert(calendarId='primary', body=event).execute()
                events_created += 1
                
            except HttpError as e:
                print(f"Error creating session event: {e}")
                events_skipped += 1
        
        return {
            "status": "success",
            "events_created": events_created,
            "events_skipped": events_skipped,
            "synced_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "events_created": 0,
            "events_skipped": 0
        }


def _get_rrule(repeat_type: str, repeat_days: Optional[list] = None) -> Optional[str]:
    """
    Convert repeat_type to RRULE string for Google Calendar
    """
    if repeat_type == 'daily':
        return 'RRULE:FREQ=DAILY'
    elif repeat_type == 'weekly':
        if repeat_days:
            # Convert to Google Calendar format (SU,MO,TU,WE,TH,FR,SA)
            day_map = ['SU', 'MO', 'TU', 'WE', 'TH', 'FR', 'SA']
            days_str = ','.join([day_map[d] for d in repeat_days if 0 <= d <= 6])
            return f'RRULE:FREQ=WEEKLY;BYDAY={days_str}'
        return 'RRULE:FREQ=WEEKLY'
    elif repeat_type == 'biweekly':
        return 'RRULE:FREQ=WEEKLY;INTERVAL=2'
    elif repeat_type == 'monthly':
        return 'RRULE:FREQ=MONTHLY'
    return None



