import os
import io
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload

SCOPES = ['https://www.googleapis.com/auth/drive.file']

class GoogleDriveStorageService:
    """
    Option 2: Bring Your Own Storage (BYOS) - Google Drive Integration
    ACTIVE DEFAULT (Saves 100% of storage costs).
    """
    def __init__(self):
        self.creds = None
        self.client_id = os.getenv("GDRIVE_CLIENT_ID")
        self.client_secret = os.getenv("GDRIVE_CLIENT_SECRET")
        self._authenticate()
        if self.creds:
            self.service = build('drive', 'v3', credentials=self.creds)
        else:
            self.service = None

    def _authenticate(self):
        if os.path.exists('token.json'):
            self.creds = Credentials.from_authorized_user_file('token.json', SCOPES)
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            elif os.path.exists('credentials.json'):
                flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
                self.creds = flow.run_local_server(port=0)
                with open('token.json', 'w') as token:
                    token.write(self.creds.to_json())

    def upload_file(self, file_path, file_name, folder_id=None):
        if not self.service:
            raise Exception("Google Drive service not initialized.")
        file_metadata = {'name': file_name}
        if folder_id:
            file_metadata['parents'] = [folder_id]
        media = MediaFileUpload(file_path, resumable=True)
        file = self.service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        return file.get('id')

    def download_file(self, file_id, destination_path):
        if not self.service:
            raise Exception("Google Drive service not initialized.")
        request = self.service.files().get_media(fileId=file_id)
        with io.FileIO(destination_path, 'wb') as fh:
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while not done:
                status, done = downloader.next_chunk()
        return destination_path

    def get_metadata(self, file_id):
        if not self.service:
            raise Exception("Google Drive service not initialized.")
        file = self.service.files().get(fileId=file_id, fields="id, name, mimeType, size").execute()
        return file
