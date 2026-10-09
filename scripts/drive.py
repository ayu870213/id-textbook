"""구글 드라이브 폴더에서 가장 최근에 올린 용량표와 가이드를 받는다."""
import io, json, os

from common import BuildError

GSHEET = 'application/vnd.google-apps.spreadsheet'
GDOC = 'application/vnd.google-apps.document'
XLSX = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
DOCX = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'


def fetch_from_drive(folder_id, workdir):
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaIoBaseDownload

    info = json.loads(os.environ['GDRIVE_SA_KEY'])
    creds = service_account.Credentials.from_service_account_info(
        info, scopes=['https://www.googleapis.com/auth/drive.readonly'])
    svc = build('drive', 'v3', credentials=creds, cache_discovery=False)
    files = svc.files().list(
        q=f"'{folder_id}' in parents and trashed = false",
        fields='files(id,name,mimeType,modifiedTime,createdTime)', pageSize=200,
        supportsAllDrives=True, includeItemsFromAllDrives=True).execute().get('files', [])
    sheets = [f for f in files if f['mimeType'] in (GSHEET, XLSX)]
    docs = [f for f in files if f['mimeType'] in (GDOC, DOCX)]
    if not sheets:
        raise BuildError('드라이브 폴더에 스프레드시트(구글 시트 또는 .xlsx)가 없습니다.')
    if not docs:
        raise BuildError('드라이브 폴더에 문서(구글 문서 또는 .docx)가 없습니다.')
    # 가장 최근에 올린 파일을 쓴다. 수정 시각으로 고르면 옛 파일을 드라이브에서 잠깐 고쳐도 그 파일이 선택된다.
    sheet = max(sheets, key=lambda f: f['createdTime'])
    doc = max(docs, key=lambda f: f['createdTime'])
    for kind, picked, cands in (('용량표', sheet, sheets), ('가이드', doc, docs)):
        if len(cands) > 1:
            print(f'{kind}: 후보 {len(cands)}개 중 가장 최근에 올린 "{picked["name"]}" 사용')

    def download(f, export_type, path):
        if f['mimeType'].startswith('application/vnd.google-apps'):
            req = svc.files().export_media(fileId=f['id'], mimeType=export_type)
        else:
            req = svc.files().get_media(fileId=f['id'], supportsAllDrives=True)
        buf = io.FileIO(path, 'wb')
        dl = MediaIoBaseDownload(buf, req)
        done = False
        while not done:
            _, done = dl.next_chunk()
        buf.close()

    xp, dp = os.path.join(workdir, 'src.xlsx'), os.path.join(workdir, 'src.docx')
    download(sheet, XLSX, xp)
    download(doc, DOCX, dp)
    return xp, dp, sheet, doc
