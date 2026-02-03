# Quick Fix for 401 Unauthorized

## Problem
Clerk's `getToken()` returns null/invalid JWT → backend rejects all requests with 401.

## Solution
1. Open `http://localhost:5174/` in your browser
2. Look for the **UserButton** (your profile picture) in the top-right corner
3. Click it → select **"Sign out"**
4. **Refresh the page** (F5)
5. Click **"התחל את המסע"** (Start Your Journey)
6. Complete Clerk sign-in flow
7. Try sending a message again

## Why this happens
- Clerk JWT tokens expire
- The session cookie might be stale
- Sign-out/sign-in forces Clerk to issue a fresh JWT

## If this doesn't work
The backend might be missing `CLERK_SECRET_KEY` env var (but that shouldn't block unverified JWT decode).

Check backend logs for any Clerk-related errors:
```bash
tail -f /home/ishai/.cursor/projects/home-ishai-code-Jewishcoach-azure/terminals/39.txt
```



