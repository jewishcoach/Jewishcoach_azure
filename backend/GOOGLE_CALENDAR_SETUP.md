# Google Calendar Integration Setup

## Overview
This guide explains how to set up Google Calendar OAuth integration for the Jewish Coach AI platform.

## Prerequisites
- Google Cloud Console account
- Admin access to the backend server

## Step 1: Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the **Google Calendar API**:
   - Go to "APIs & Services" > "Library"
   - Search for "Google Calendar API"
   - Click "Enable"

## Step 2: Create OAuth 2.0 Credentials

1. Go to "APIs & Services" > "Credentials"
2. Click "Create Credentials" > "OAuth client ID"
3. If prompted, configure the OAuth consent screen:
   - User Type: External
   - App name: Jewish Coach AI
   - User support email: your email
   - Developer contact: your email
   - Add scopes: `https://www.googleapis.com/auth/calendar.events`
4. Create OAuth client ID:
   - Application type: **Web application**
   - Name: Jewish Coach Calendar Integration
   - Authorized redirect URIs:
     - `http://localhost:8000/api/calendar/google/callback` (for development)
     - `https://your-domain.com/api/calendar/google/callback` (for production)
5. Copy the **Client ID** and **Client Secret**

## Step 3: Configure Backend Environment

Add the following to your `.env` file:

```bash
# Google Calendar OAuth
GOOGLE_CLIENT_ID=your_client_id_here
GOOGLE_CLIENT_SECRET=your_client_secret_here
GOOGLE_REDIRECT_URI=http://localhost:8000/api/calendar/google/callback

# Frontend URL (for OAuth callback redirect)
FRONTEND_URL=http://localhost:5173
```

## Step 4: Test the Integration

1. Restart the backend server
2. Go to the Calendar page in the frontend
3. Click "חבר Google" (Connect Google)
4. Authorize the application
5. You should be redirected back to the app
6. Click "סנכרן עכשיו" (Sync Now) to sync your events

## Features

### What Gets Synced?
- **Reminders**: All active coaching reminders
- **Past Sessions**: All completed coaching conversations
- **Recurring Events**: Supports daily, weekly, biweekly, and monthly reminders

### Sync Behavior
- Events are created in the user's primary Google Calendar
- Reminders have 30-minute and 1-hour notifications
- Past sessions are color-coded green
- Each event includes a link back to Jewish Coach AI

## Security Notes

- Tokens are stored encrypted in the database
- Refresh tokens allow automatic token renewal
- Users can disconnect at any time
- Only `calendar.events` scope is requested (read/write events only)

## Troubleshooting

### "Redirect URI mismatch" error
- Make sure the redirect URI in Google Console matches exactly
- Include `/api/calendar/google/callback` at the end
- Protocol (http/https) must match

### "Access denied" error
- Check that the Google Calendar API is enabled
- Verify OAuth consent screen is configured
- Make sure the user has granted calendar access

### Tokens not refreshing
- Check that `GOOGLE_CLIENT_SECRET` is set correctly
- Verify refresh token is stored in database
- Force user to reconnect if needed

## API Endpoints

- `GET /api/calendar/google/auth-url` - Get OAuth authorization URL
- `GET /api/calendar/google/callback` - OAuth callback handler
- `POST /api/calendar/google/sync` - Sync events to Google Calendar
- `DELETE /api/calendar/google/disconnect` - Disconnect integration
- `GET /api/calendar/google/status` - Check connection status



