# Getting Session Token from Browser

Since the GraphQL login endpoint requires authentication (which is unusual), you may need to extract a session token from your browser.

## Method 1: Extract from Browser DevTools

1. **Open Monarch Money in your browser** (https://app.monarchmoney.com)
2. **Open Developer Tools** (F12 or Right-click → Inspect)
3. **Go to Network tab**
4. **Filter by "graphql" or "api"**
5. **Make any request** (like refreshing the page or navigating)
6. **Find a GraphQL request** and click on it
7. **Look at the Request Headers**:
   - Find the `Authorization` header
   - It should look like: `Token abc123...` or `Bearer abc123...`
8. **Copy the token value** (the part after "Token " or "Bearer ")

## Method 2: Extract from Cookies

1. **Open Developer Tools** (F12)
2. **Go to Application tab** (Chrome) or **Storage tab** (Firefox)
3. **Click on Cookies** → `https://app.monarchmoney.com`
4. **Look for session-related cookies**:
   - `sessionid`
   - `csrftoken`
   - Any cookie with "auth" or "token" in the name
5. **Copy the cookie value**

## Method 3: Use Browser Extension

Some browser extensions can help extract authentication tokens from requests.

## Using the Token

Once you have the token, you can:

1. **Add it to your `.env` file**:
   ```
   MONARCH_SESSION_TOKEN=your_token_here
   ```

2. **Or use it directly in code**:
   ```python
   from monarchmoney import MonarchMoney
   mm = MonarchMoney(token="your_token_here")
   ```

3. **Or save it as a session file**:
   ```python
   from monarchmoney import MonarchMoney
   mm = MonarchMoney()
   mm._token = "your_token_here"
   mm._headers["Authorization"] = f"Token {mm._token}"
   mm.save_session()
   ```

## Note

Session tokens typically last for several months, so you won't need to do this frequently.



