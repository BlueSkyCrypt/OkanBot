import functions_framework
from janome.tokenizer import Tokenizer
import pytz
import sche_func
import sche_db
import pprint
import math
import json
import emoji
import collections
import os
import logging
import sys
import time
import typing as t
import logging
import google.cloud.logging
import numpy as np
import re
from PIL import Image
from urllib import request
from google.cloud import storage
from wordcloud import WordCloud
from datetime import datetime, timedelta, timezone
from atproto import Client
from atproto.xrpc_client import models
from dateutil.parser import parse

client = google.cloud.logging.Client()
client.setup_logging()

logging.basicConfig(level=logging.FATAL, format="%(asctime)s - %(levelname)s - %(message)s")

HANDLE = os.getenv("ATP_USERNAME")
PASSWORD = os.getenv("ATP_PASSWORD")
OUTPATH = "/tmp/"
if os.name == 'nt':
    OUTPATH="./out/"

tkn = Tokenizer("./userdic.csv", udic_type="simpledic", udic_enc="utf8")

class OkanBotMessage(t.TypedDict):
    content: t.Optional[str]
    did: t.Optional[str]
    name: t.Optional[str]

FONTNAME='NotoSansCJK-Regular.ttc'
FONTPATH=OUTPATH+FONTNAME

# ファイルを取得する関数
def get_font_ifnoexists():
    if os.path.exists(FONTPATH) == True:
        return
    storage_client = storage.Client()
    bucket = storage_client.bucket("okanfont")
    blob = bucket.blob(FONTNAME)
    file_contents = blob.download_as_string()
    with open(FONTPATH, 'wb') as file:
        file.write(file_contents)

def get_notifications(client: Client):
    response = client.app.bsky.notification.list_notifications()
    return response.notifications

def update_seen(client: Client, seenAt: datetime):
    response = client.app.bsky.notification.update_seen({"seenAt": seenAt.isoformat()})
    return

def filter_mentions_and_replies_from_notifications(ns: t.List["models.AppBskyNotificationListNotifications.Notification"]) -> t.List[models.AppBskyNotificationListNotifications.Notification]:
    return [n for n in ns if n.reason in ("mention")]

def filter_unread_notifications(ns: t.List["models.AppBskyNotificationListNotifications.Notification"], seen_at: datetime) -> t.List["models.AppBskyNotificationListNotifications.Notification"]:
    return [n for n in ns if seen_at - timedelta(minutes=2) < parse(n.indexed_at)]


def get_thread(client: Client, uri: str) -> "models.AppBskyFeedDefs.FeedViewPost":
    return client.app.bsky.feed.get_post_thread({"uri": uri})

def is_already_replied_to(feed_view: models.AppBskyFeedDefs.FeedViewPost, did: str) -> bool:
    replies = feed_view.thread.replies
    if replies is None:
        return False
    else:
        return any([reply.post.author.did == did for reply in replies])

def flatten_posts(thread: "models.AppBskyFeedDefs.ThreadViewPost") -> t.List[t.Dict[str, any]]:
    posts = [thread.post]

    parent = thread.parent
    if parent is not None:
        posts.extend(flatten_posts(parent))

    return posts

def get_openai_chat_message_name(name: str) -> str:
    return name.replace(".", "_")

def posts_to_sorted_messages(posts: t.List[models.AppBskyFeedDefs.PostView], assistant_did: str) -> t.List[OkanBotMessage]:
    sorted_posts = sorted(posts, key=lambda post: post.indexed_at)
    messages = []
    for post in sorted_posts:
        messages.append(OkanBotMessage(content=post.record.text, did=post.author.did,name=get_openai_chat_message_name(post.author.handle)))
    return messages

def thread_to_messages(thread: "models.AppBskyFeedGetPostThread.Response", did: str) -> t.List[OkanBotMessage]:
    if thread is None:
        return []
    posts = flatten_posts(thread.thread)
    messages = posts_to_sorted_messages(posts, did)
    return messages


def reply_to(notification,response) -> t.Union[models.AppBskyFeedPost.ReplyRef, models.AppBskyFeedDefs.ReplyRef]:
    if response != None:
        parent = {
        "cid": response.cid,
        "uri": response.uri,
        }
        return {"root": parent,"parent": parent}

    parent = {
        "cid": notification.cid,
        "uri": notification.uri,
        }
    if notification.record.reply is None:
        return {"root": parent, "parent": parent}
    else:
        return {"root": notification.record.reply.root, "parent": parent}

def get_file_type_and_rename(filename):
    with open(filename, "rb") as f:
        bytes = f.read(16)
    file_type = None
    # JPEGファイルかどうかを判定する
    if bytes[:2] == b"\xFF\xD8":
        file_type = "JPEG"
    # PNGファイルかどうかを判定する
    if bytes[:8] == b"\x89\x50\x4E\x47\x0D\x0A\x1A\x0A":
        file_type = "PNG"
    # その他のファイル形式を判定する
    if file_type is None:
        file_type = binascii.hexlify(bytes).decode("ascii")
    nfilename=""
    match(file_type):
        case "JPEG":
            nfilename=filename+"_icon.jpg"
        case "PNG":
            nfilename=filename+"_icon.png"
        case _:
            pass
    if os.path.exists(nfilename):
        os.remove(nfilename)
    os.rename(filename,nfilename)
    return


def word_count(username,userhandle,client,mcmax,maxposts):
    prof = client.app.bsky.actor.get_profile({"actor":userhandle})
    request.urlretrieve(prof.avatar,OUTPATH+username)
    get_file_type_and_rename(OUTPATH+username)

    posts_count = prof.posts_count
    print("Handle:"+userhandle)
    print("Posts :"+str(posts_count))
    cursor = ""

    if posts_count > maxposts:
        posts_count = maxposts
    words=[]
    r = posts_count // 100 + 1
    for i in range(r):
        params = models.ComAtprotoRepoListRecords.Params(repo=prof.did,collection="app.bsky.feed.post",limit=100,cursor=cursor)
        feeds = client.com.atproto.repo.list_records(params=params)
        for repox in feeds:
                if repox[1] == None:
                    break
                for xx in repox[1]:
                    if type(xx) != str:
                       jjss = json.loads(xx.model_dump_json())
                       text = jjss['value']['text']
                       if text.startswith("@okanbot.bsky.social") == True:
                           continue
                       for token in tkn.tokenize(text):
                           if len(token.surface)>2:
                             token.surface = emoji.replace_emoji(token.surface)
                             if token.surface.isascii()==False:
                               if token.part_of_speech.startswith('名詞') == True:
                                   if token.part_of_speech.startswith('名詞,接尾') == False:
                                       if token.part_of_speech.startswith('名詞,サ変') == False:
                                           if token.part_of_speech.startswith('名詞,非自立') == False:
                                               words.append(token.surface)
        cursor = feeds.cursor

    print("Cursor:"+str(cursor))
    c = collections.Counter(words)
    return (c.most_common(mcmax*4),c.most_common(mcmax))

def create_wordcloud_ja(word_list,userhandle,cmapin='tab20',bgcolor='white',fgcolor=""):
    get_font_ifnoexists()
    fontpath = FONTPATH
    stop_words_ja = ['もの', 'こと', 'とき', 'そう', 'たち', 'これ', 'よう', 'これら', 'それ', 'すべて']
    word_chain = ""
    for tpltpl in word_list:
        word_chain = word_chain + tpltpl[0] + " "

    word_color_func=None

    if fgcolor != "":
      word_color_func = lambda *args, **kwargs: fgcolor

    wordcloud = None
    if word_color_func != None:
     wordcloud = WordCloud(background_color=bgcolor,
                           color_func=word_color_func,
                           font_path=fontpath,
                           width=3000,
                           height=1000,
                           prefer_horizontal=0.8,
                           mask = None,
                           colormap = cmapin,
                           contour_width=1,
                           contour_color="black",
                           stopwords=set(stop_words_ja)).generate(word_chain)
    else:
     wordcloud = WordCloud(background_color=bgcolor,
                           font_path=fontpath,
                           width=3000,
                           height=1000,
                           prefer_horizontal=0.8,
                           mask = None,
                           colormap = cmapin,
                           contour_width=1,
                           contour_color="black",
                           stopwords=set(stop_words_ja)).generate(word_chain)
    wordcloud.to_file(f"{OUTPATH}{userhandle}.png")


def create_wordcloud_mask(word_list,userhandle,mask,cmapin='tab20',bgcolor='white',fgcolor="")->np.ndarray:
    get_font_ifnoexists()
    fontpath = FONTPATH
    stop_words_ja = ['もの', 'こと', 'とき', 'そう', 'たち', 'これ', 'よう', 'これら', 'それ', 'すべて']
    word_chain = ""
    for tpltpl in word_list:
        word_chain = word_chain + tpltpl[0] + " "

    word_color_func=None

    if fgcolor != "":
      word_color_func = lambda *args, **kwargs: fgcolor

    wordcloud = WordCloud(background_color=bgcolor,
                           color_func=word_color_func,
                           font_path=fontpath,
                           width=3000,
                           height=1000,
                           prefer_horizontal=0.8,
                           mask = mask,
                           colormap = cmapin,
                           contour_width=1,
                           contour_color="black",
                           stopwords=set(stop_words_ja)).generate(word_chain)

    return wordcloud.to_array()


def drawCircle(height,width,fg,bg):
    arr = np.full((height, width, 3), [fg,fg,fg], dtype=np.uint8)
    center_y = height // 2
    center_x = width // 2
    radius = width/2

    for y in range(height):
        for x in range(width):
            if (y - center_y) ** 2 + (x - center_x) ** 2 < radius ** 2:
                arr[y, x] = [bg,bg,bg]
    return arr

def ImageOverlay(src:np.ndarray,dst:np.ndarray,sx,sy) -> np.ndarray:
    dw,dh,dd = dst.shape
    sw,sh,sd = src.shape

    if sx+dw > sw:
        dw=dw+(sw-(sx+dw))
    if sy+dh > sh:
        dh=dh+(sh-(sy+dh))

    src[sx:sx+dw,sy:sy+dh] = dst[0:dw,0:dh]

    return src

#def create_wordcloud_ja(word_list,userhandle,cmapin='tab20',bgcolor='white',fgcolor=""):

def makeWordCloudWithIcon(word_list,userhandle,iconpath,cmapin='tab20',bgcolor='white',fgcolor=""):
    back = np.full((1000, 3000, 3), [255,255,255], dtype=np.uint8)
    back2 = np.full((1000, 3000, 3), [0,0,0], dtype=np.uint8)
    bw,bh,bd = back.shape
    front = np.array(Image.open(iconpath).convert('RGB').resize((int(bw/3),int(bw/3))))
    fw,fh,fd = front.shape
    whiteCircle=drawCircle(int(bw/3),int(bw/3),0,255)
    wcmask = ImageOverlay(back2,whiteCircle,int((bw-fw)/2),int((bh-fh)/2))
    back = create_wordcloud_mask(word_list,userhandle,wcmask,cmapin=cmapin,bgcolor=bgcolor,fgcolor=fgcolor)
    blackCircle=drawCircle(int(bw/3),int(bw/3),255,0)
    mask = (blackCircle != [255,255,255]).all(axis=2)
    blackCircle[mask] = front[mask]
    return Image.fromarray(ImageOverlay(back,blackCircle,int((bw-fw)/2),int((bh-fh)/2)))

POSTMAX=300

def splitForPost(postdatal:list,max:int=POSTMAX)->list:
    retlist = []
    length = 0
    retstring = ""
    for postline in postdatal:
        linelen = len(postline)
        if len(retstring)+linelen>POSTMAX:
            retlist.append(retstring)
            retstring = ""
            retstring += postline
        else:
            retstring += postline
    retlist.append(retstring)

    return retlist

WCOUNT=30
WMAX=2000

def read_notifications_and_reply(client: Client, last_seen_at: datetime = None) -> datetime:
#    print(f"last_seen_at: {last_seen_at}")
    did = client.me.did
    seen_at = datetime.now(tz=timezone.utc)

    # unread countで判断するアプローチは、たまたまbsky.appで既読をつけてしまった場合に弱い
    ns = get_notifications(client)
    ns = filter_mentions_and_replies_from_notifications(ns)
    if last_seen_at is not None:
        ns = filter_unread_notifications(ns, last_seen_at)

    if (len(ns) == 0):
#        print("No unread notifications")  # avoid to call update_seen unnecessarily.
        return seen_at

    for notification in ns:
        thread = get_thread(client, notification.uri)
        if is_already_replied_to(thread, did):
#            print(f"Already replied to {notification.uri}")
            continue

        post_messages = thread_to_messages(thread, did)
        colmap='tab20'
        bgcolor=""
        fgcolor=""
        nounai=False
        for pm in post_messages:
            print(pm['name'])
            if "脳内" in pm['content']:
                nounai=True
            if "白黒" in pm['content']:
                bgcolor = "white"
                fgcolor = "black"
            elif "黒白" in pm['content']:
                bgcolor = "black"
                fgcolor = "white"
            elif "黒" in pm['content']:
                bgcolor = "black"
            else:
                bgcolor = "white"
            if "登録" in pm['content']:
                    pprint.pprint(pm)
                    meirei = pm['content'].replace("@okanbot.bsky.social 登録","")
                    jsbase = {"username":pm['did']}
                    js = []
                    jsbase["schedule"]=js
                    js.append(sche_func.str_to_datetime(meirei))
                    expired,upcomming = sche_func.get_schedule_status_from_dict(jsbase)
                    postdata=""
                    for itm in expired:
                        postdata="あんた、それもう昔の話\n"
                        postdata += itm[0]['nextalm']+" は昔のはなし"
                    for itm in upcomming:
                        postdata="わかった、おかんにまかせといて\n"
                        postdata += itm[0]['nextalm']+" 近辺でメンションするわ"
                        sche_db.write_to_firestore(pm['did'],pm['name'],itm[0])
                    client.send_post(text=f"{postdata}", reply_to=reply_to(notification,None))
            if "ランク" in pm['content'] or "脳内" in pm['content']:
                wctpl = word_count(pm['name'],pm['did'],client,WCOUNT,WMAX)
                wc0 = wctpl[0]
                wc1 = wctpl[1]
                rank = 1
                postdatal = [pm['name']+f"さんの頻出単語TOP{WCOUNT}\n"]
                for word,count in wc1:
                    postdatal.append(str(rank)+"位:"+word+"_"+str(count)+"回\n")
                    rank+=1
                postdata = splitForPost(postdatal)
                try:
                  img=""
                  iconpath=OUTPATH+pm['name']+"_icon.jpg"
                  if os.path.exists(iconpath)!=True:
                      iconpath=OUTPATH+pm['name']+"_icon.png"
                  img = makeWordCloudWithIcon(wc0,pm['name'],iconpath,cmapin=colmap,bgcolor=bgcolor,fgcolor=fgcolor)
                  img.save(f"{OUTPATH}"+pm['name']+".png")
                  os.remove(iconpath)
                except Exception as eex:
                  print(eex)
                imagepath= f"{OUTPATH}"+pm['name']+".png"
                postdata.append(pm['name']+f"さんの頻出単語TOP{WCOUNT*4}イメージ\n")
                replytoctx=None
                endX = len(postdata)
                nowX = 1
                print("POST:"+str(endX))
                for postd in postdata:
                    try:
                        if nowX == endX:
                            if os.path.exists(imagepath) == True:
                                print(imagepath)
                                with open(imagepath,"rb") as ff:
                                    img_data = ff.read()
                                    replytoctx = client.send_image(text=f"{postd}", image=img_data,image_alt='wordcloud image',reply_to=reply_to(notification,replytoctx))
                                os.remove(imagepath)
                            else:
                                replytoctx = client.send_post(text=f"{postd}", reply_to=reply_to(notification,replytoctx))
                        else:
                            replytoctx = client.send_post(text=f"{postd}", reply_to=reply_to(notification,replytoctx))
                    except Exception as ExcExc:
                        replytoctx = client.send_post(text=f"{postd}", reply_to=reply_to(notification,replytoctx))
                    nowX+=1
#            elif "ヘルプ" in pm['content']:
#                postdata = "「ランク」\nという文字列であなたの過去2000ポストの頻出単語を出すよ"
#                client.send_post(text=f"{postdata}", reply_to=reply_to(notification))
#            else:
#                postdata = "ごめんやで、理解できないやで。Hirofumi Ukawaに鋭意対応させるわ"
#                client.send_post(text=f"{postdata}", reply_to=reply_to(notification))

    update_seen(client, seen_at)
    return seen_at


def login(client: Client, initial_wait: int):
    sleep_duration = initial_wait
    max_sleep_duration = 3600  # 1 hour

    while True:
        try:
            client.login(HANDLE, PASSWORD)
            return  # if login is successful, exit the loop
        except Exception as e:
            print(f"An error occurred during login: {e}")
            if sleep_duration > max_sleep_duration:  # if sleep duration has reached the max, exit the system
                print("Max sleep duration reached, exiting system.")
                sys.exit(1)
            time.sleep(sleep_duration)
            sleep_duration *= 2  # double the sleep duration on failure


@functions_framework.http
def main(request):
    request_json = request.get_json(silent=True)
    request_args = request.args
    fn_main()
    return "OK"

def fn_main():
     client = Client()
     login(client, initial_wait=1)
     seen_at = None
     while True:
      try:
         seen_at = read_notifications_and_reply(client, seen_at)
      except Exception as e:
         print(f"exception line261 {e}")
         login(client, initial_wait=60)
      finally:
#         print('ok')
         time.sleep(5)
     return 'OK'

if os.name == 'nt':
    fn_main()
