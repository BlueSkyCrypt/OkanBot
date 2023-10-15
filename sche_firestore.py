import pyt
import datetime
import sche_func
from google.cloud import firestore

class FirestoreJsonHandler:
    def __init__(self, collection_name):
        # 認証情報を設定
        # 以下のコードはGoogle Cloud PlatformのプロジェクトIDを環境変数に設定している場合の例です
        import os

        # Firestoreに接続
        self.db = firestore.Client()

        # コレクションの参照を取得
        self.collection_ref = self.db.collection(collection_name)

    def read_user_json(self, user_id):
        try:
            doc_ref = self.collection_ref.document(user_id)
            doc = doc_ref.get()
            if doc.exists:
                user_data = doc.to_dict()
            else:
                print(f"Error: Document {user_id} does not exist.")
                user_data = {'did':user_id,'sche':[]}
        except Exception as e:
            print(f"Error: Failed to read user data for {user_id}. {e}")
            user_data = {'did':user_id,'sche':[]}
        return user_data

    def write_user_json(self, user_id, user_data):
        try:
            self.collection_ref.document(user_id).set(user_data)
        except Exception as e:
            print(f"Error: Failed to write user data for {user_id}. {e}")

    def read_all_users_json(self):
        all_users_data = {}
        try:
            for doc in self.collection_ref.stream():
                user_id = doc.id
                user_data = doc.to_dict()
                all_users_data[user_id] = user_data
        except Exception as e:
            print(f"Error: Failed to read all users data. {e}")
        return all_users_data

    def write_all_users_json(self, all_users_data):
        try:
            for user_id, user_data in all_users_data.items():
                self.collection_ref.document(user_id).set(user_data)
        except Exception as e:
            print(f"Error: Failed to write all users data. {e}")

def get_alarm_within_300sec(data):
    now = pyt.datetimenow()
    result = {}
    for key in data:
        alarms_within_300sec = []
        for alarm in data[key]:
            if abs((alarm[1] - now).total_seconds()) <= 300:
                alarms_within_300sec.append(alarm[0])
        if len(alarms_within_300sec) > 0:
            result[key] = alarms_within_300sec
    return result

def GetAlarm(handler:FirestoreJsonHandler)->list:
    all_users_data = handler.read_all_users_json()
    sdic = {}
    retdic = {}
    for datas in all_users_data.keys():
        sdic['schedule']=all_users_data[datas]['sche']
        expired,upcomming = sche_func.get_schedule_status_from_dict(sdic)
        retdic[datas] = upcomming
        retdic[datas].extend(expired)
    return get_alarm_within_300sec(retdic)

def GetAll(handler:FirestoreJsonHandler)->list:
    all_users_data = handler.read_all_users_json()
    sdic = {}
    retdic = {}
    for datas in all_users_data.keys():
        sdic['schedule']=all_users_data[datas]['sche']
        expired,upcomming = sche_func.get_schedule_status_from_dict(sdic)
        retdic[datas] = upcomming
        retdic[datas].extend(expired)
    return retdic
