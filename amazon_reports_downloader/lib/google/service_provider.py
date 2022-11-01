import pickle
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

root_dir = (os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(__file__)), '..')) + '/')


class GoogleServiceProvider(object):
    # If modifying these scopes, delete the file token.pickle.
    scopes = {
        'sheets': ['https://www.googleapis.com/auth/spreadsheets']
    }

    def __init__(self):
        pass

    def get_service(self, user_id, service_type):
        creds = self.get_creds(user_id, service_type)
        service = None
        if service_type == 'sheets':
            service = build('sheets', 'v4', credentials=creds)
        return service

    def get_creds(self, user_id, service_type):

        token_pickle_path = root_dir + "/token/" + service_type.lower() + "/" + user_id.lower() + "/token.pickle"
        creds = None
        # The file token.pickle stores the user's access and refresh tokens, and is
        # created automatically when the authorization flow completes for the first
        # time.
        if os.path.exists(token_pickle_path):
            try:
                with open(token_pickle_path, 'rb') as token:
                    creds = pickle.load(token)
            except:
                pass
        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                secret_path = root_dir + '/token/client_secret.json'
                flow = InstalledAppFlow.from_client_secrets_file(secret_path, self.scopes[service_type])
                creds = flow.run_local_server()
            # Save the credentials for the next run
            with open(token_pickle_path, 'wb+') as token:
                pickle.dump(creds, token)

        return creds

    def get(self):
        pass


if __name__ == '__main__':
    service_provider = GoogleServiceProvider()
    service_provider.get_service('newkbsky@gmail.com', 'sheets')
