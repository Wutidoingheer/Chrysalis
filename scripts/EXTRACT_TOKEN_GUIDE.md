# Step-by-Step: Extract Monarch Money Session Token

## Quick Method (Recommended)

### Step 1: Open Monarch Money in Browser
1. Go to https://app.monarchmoney.com
2. Make sure you're logged in

### Step 2: Open Developer Tools
- **Chrome/Edge**: Press `F12` or `Ctrl+Shift+I` (Windows) / `Cmd+Option+I` (Mac)
- **Firefox**: Press `F12` or `Ctrl+Shift+I` (Windows) / `Cmd+Option+I` (Mac)

### Step 3: Go to Network Tab
1. Click on the **Network** tab in Developer Tools
2. Make sure the network monitor is recording (red circle should be active)

### Step 4: Trigger a Request
1. Refresh the page (`F5` or `Ctrl+R`)
2. OR navigate to a different page (like Accounts or Transactions)
3. OR click on any button that loads data

### Step 5: Find the Authorization Token
1. In the Network tab, look for requests to:
   - `api.monarchmoney.com/graphql`
   - `api.monarchmoney.com/auth/`
   - Any request to `monarchmoney.com`

2. Click on one of these requests

3. In the request details, look for:
   - **Request Headers** section
   - Find the **`Authorization`** header
   - It will look like: `Authorization: Token abc123xyz...` or `Authorization: Bearer abc123xyz...`

4. **Copy the entire token value** (the part after "Token " or "Bearer ")

### Step 6: Use the Token
Add it to your `.env` file:
```
MONARCH_SESSION_TOKEN=abc123xyz...
```

Then run:
```bash
python scripts/monarch_use_token.py
```

---

## Alternative Method: From Application/Storage Tab

### Chrome/Edge:
1. Open Developer Tools (`F12`)
2. Go to **Application** tab
3. In the left sidebar, expand **Cookies**
4. Click on `https://app.monarchmoney.com`
5. Look for cookies named:
   - `sessionid`
   - `csrftoken`
   - `auth_token`
   - Any cookie with "token" or "session" in the name

### Firefox:
1. Open Developer Tools (`F12`)
2. Go to **Storage** tab
3. Expand **Cookies**
4. Click on `https://app.monarchmoney.com`
5. Look for session-related cookies

---

## Method 3: Copy as cURL (Advanced)

1. In Network tab, right-click on a GraphQL request
2. Select **Copy** → **Copy as cURL**
3. Paste into a text editor
4. Look for the `-H 'Authorization: Token ...'` line
5. Extract the token value

---

## Troubleshooting

**Can't find Authorization header?**
- Make sure you're looking at the **Request Headers**, not Response Headers
- Try a different request (GraphQL requests are most reliable)
- Make sure you're logged in to Monarch Money

**Token doesn't work?**
- The token might have expired
- Make sure you copied the entire token (they can be long)
- Try extracting a fresh token

**Still having issues?**
- Check if there are multiple Authorization headers
- Try using the token from a GraphQL request specifically
- Make sure there are no extra spaces when copying



