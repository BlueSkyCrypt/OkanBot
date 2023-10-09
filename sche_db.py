import firebase_admin
from firebase_admin import credentials, firestore

cred = credentials.ApplicationDefault()
firebase_admin.initialize_app(cred)
db = firestore.client()

def write_to_firestore(did, userhandle, data):
    if not did or not userhandle or not data:
        return False  # 書き込みに失敗した場合はFalseを返す

    collection_name = "sche"

    base = {"schedule":[data]}

    # Firestoreにデータを書き込み
    try:
        db.collection(collection_name).document(did).set(data)
        return True  # 書き込みが成功した場合はTrueを返す
    except Exception as e:
        print(f"Error writing to Firestore: {str(e)}")
        return False  # 書き込みに失敗した場合はFalseを返す

def read_from_firestore(did):
    if not did:
        return None  # 無効な入力の場合はNoneを返す

    collection_name = "sche"

    # Firestoreからデータを読み取り
    doc_ref = db.collection(collection_name).document(did)
    doc = doc_ref.get()

    if doc.exists:
        data = doc.to_dict()
        return data  # データを返す
    else:
        return None  # ドキュメントが存在しない場合はNoneを返す

def read_all_documents():
    collection_name = "sche"

    # Firestoreからすべてのドキュメントをクエリして取得
    docs = db.collection(collection_name).stream()

    # ドキュメントを辞書のリストに変換
    all_data = []
    for doc in docs:
        data = doc.to_dict()
        all_data.append(data)

    return all_data

#all_documents = read_all_documents()
#for document in all_documents:
#    print(document)

#data= {"ukawa4":"Hirofumi3"}
#write_to_firestore("ukawa2", "ukawa", data)
