import os
from google_auth_oauthlib.flow import InstalledAppFlow
from dotenv import load_dotenv

load_dotenv()

# The scope required to publish to Blogger
SCOPES = ['https://www.googleapis.com/auth/blogger']

def main():
    client_id = os.getenv("BLOGGER_CLIENT_ID")
    client_secret = os.getenv("BLOGGER_CLIENT_SECRET")
    
    if not client_id or not client_secret:
        print("ERROR: BLOGGER_CLIENT_ID and BLOGGER_CLIENT_SECRET must be set in your .env file.")
        print("Please complete the Google Cloud Console setup first.")
        return

    # Create client config dictionary dynamically
    client_config = {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }

    try:
        print("Opening browser for authentication...")
        flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
        
        # Run local server to capture the auth code (Requires user to login via browser)
        creds = flow.run_local_server(port=0)
        
        print("\n" + "="*50)
        print("✅ AUTHENTICATION SUCCESSFUL!")
        print("="*50)
        print("Please copy the EXACT string below and paste it into your .env file as BLOGGER_REFRESH_TOKEN:\n")
        print(creds.refresh_token)
        print("\n" + "="*50)
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
