import base64
import csv #read the list of user in CSV file
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from django.conf import settings

def gmail_credentials():
    # Set up OAuth2 credentials
    path_to_files = str(settings.BASE_DIR) + "/appt_calendar_app/libs/"
    try:
        creds = Credentials.from_authorized_user_file(path_to_files + 'token.json')
    except FileNotFoundError: #-- token.json file does NOT exist --#
        #-- generate token by authorizing via browser (1st time only, I hope so :D) --#
        flow = InstalledAppFlow.from_client_secrets_file(
            path_to_files + 'credentials.json',  #credentials JSON file
            ['https://www.googleapis.com/auth/gmail.send']
            )
        creds = flow.run_local_server(port=0)

    #-- token.json exists --#    
    if creds and creds.valid:
        pass

    #-- token is expired--#      
    elif creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())

    # Save the credentials as token
    with open(path_to_files + 'token.json', 'w') as token_file:
        token_file.write(creds.to_json())

    # return the creds

    return creds

def gmail_compose(mail_subject, email_recipient, mail_body):
    message = {
        'raw': base64.urlsafe_b64encode(
            f'MIME-Version: 1.0\n'
            f'Content-Type: text/html; charset="UTF-8"\n'
            f"From: itbase.tv@gmail.com\n"
            f"To: {email_recipient}\n"
            f"Subject: {mail_subject}\n\n"
            f"{mail_body}"
            .encode("utf-8")
        ).decode("utf-8")
    }
    return message

def gmail_send(creds, message):
# Send the email
    service = build('gmail', 'v1', credentials=creds)
    try:
        service.users().messages().send(userId='me', body=message).execute()
        print('Email sent successfully.')
    except Exception as e:
        print('An error occurred while sending the email:', str(e))

if __name__ == "__main__":

    #-Mail Subject-#
    mail_subject = "Test Email"

    #-Build HTML content in single line with "space" as separater-#
    #mail_body = open('content.html', 'r').read()
    #mail_body = mail_body.replace('\n',' ') 
    mail_body = "Hola nen!"

    #--create mail services--#
    creds = gmail_credentials() 

    email_recipient = 'farrones@yahoo.com'
    mail_content = gmail_compose(mail_subject, email_recipient, mail_body)
    gmail_send(creds, mail_content)
    '''
    #--Read line by line in csv, each line includes one user's mail address, and send mail to them.--#
    with open('user_mail_lists.csv', 'r') as csv_file:
        reader = csv.DictReader(csv_file)
        for user in reader:
           email_recipient = user['user_email']
           #SEND MAIL#            
           mail_content = gmail_compose(mail_subject, email_recipient, mail_body)
           gmail_send(creds, mail_content)
    '''