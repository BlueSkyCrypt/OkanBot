import decouple
import functions_framework
from janome.tokenizer import Tokenizer
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
from wordcloud import WordCloud
from datetime import datetime, timedelta, timezone

from atproto import Client
from atproto.xrpc_client import models
from dateutil.parser import parse
from dotenv import load_dotenv

load_dotenv(verbose=True)
logging.basicConfig(level=logging.FATAL, format="%(asctime)s - %(levelname)s - %(message)s")

client = google.cloud.logging.Client()
client.setup_logging()


HANDLE = os.getenv("ATP_USERNAME")
PASSWORD = os.getenv("ATP_PASSWORD")
OUTPATH = "/tmp/"
if os.name == 'nt':
    OUTPATH="./out/"

class OkanBotMessage(t.TypedDict):
    content: t.Optional[str]
    did: t.Optional[str]
    name: t.Optional[str]


def get_notifications(client: Client):
    response = client.app.bsky.notification.list_notifications()
    return response.notifications

def update_seen(client: Client, seenAt: datetime):
    response = client.app.bsky.notification.update_seen({"seenAt": seenAt.isoformat()})
    return

def filter_mentions_and_replies_from_notifications(ns: t.List["models.AppBskyNotificationListNotifications.Notification"]) -> t.List[models.AppBskyNotificationListNotifications.Notification]:
    return [n for n in ns if n.reason in ("mention")]

def filter_unread_notifications(ns: t.List["models.AppBskyNotificationListNotifications.Notification"], seen_at: datetime) -> t.List["models.AppBskyNotificationListNotifications.Notification"]:
    # IndexされてからNotificationで取得できるまでにラグがあるので、最後に見た時刻より少し前ににIndexされたものから取得する
    return [n for n in ns if seen_at - timedelta(minutes=2) < parse(n.indexed_at)]


def get_thread(client: Client, uri: str) -> "models.AppBskyFeedDefs.FeedViewPost":
    return client.app.bsky.feed.get_post_thread({"uri": uri})


# TODO: receive models.AppBskyFeedDefs.ThreadViewPost
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
    # should be '^[a-zA-Z0-9_-]{1,64}$'
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

def reply_to(notification: models.AppBskyNotificationListNotifications.Notification) -> t.Union[models.AppBskyFeedPost.ReplyRef, models.AppBskyFeedDefs.ReplyRef]:
    parent = {
        "cid": notification.cid,
        "uri": notification.uri,
    }
    if notification.record.reply is None:
        return {"root": parent, "parent": parent}
    else:
        return {"root": notification.record.reply.root, "parent": parent}


tkn = Tokenizer("./userdic.csv", udic_type="simpledic", udic_enc="utf8")

def word_count(username,userhandle,client,mcmax,maxposts):
    prof = client.app.bsky.actor.get_profile({"actor":userhandle})
    posts_count = prof.posts_count
    print("Handle:"+userhandle)
    print("Posts :"+str(posts_count))
#    t = Tokenizer(")
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

#ワードクラウド作成関数(日本語テキスト版)
def create_wordcloud_ja(word_list,userhandle):
    fontpath = './NotoSansCJK-Regular.ttc'
    stop_words_ja = ['もの', 'こと', 'とき', 'そう', 'たち', 'これ', 'よう', 'これら', 'それ', 'すべて']
    word_chain = ""
    for tpltpl in word_list:
        word_chain = word_chain + tpltpl[0] + " "
#900x500
#    word_chain = ' '.join(wlist)
    wordcloud = WordCloud(background_color="white",
                          font_path=fontpath,
                          width=3000,
                          height=1000,
                          mask = None,
                          contour_width=1,
                          contour_color="black",
                          stopwords=set(stop_words_ja)).generate(word_chain)
    wordcloud.to_file(f"{OUTPATH}{userhandle}.png")


WCOUNT=15
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
        for pm in post_messages:
            print(pm['name'])
            if "ランク" in pm['content']:
                wctpl = word_count(pm['name'],pm['did'],client,WCOUNT,WMAX)
                wc0 = wctpl[0]
                wc1 = wctpl[1]
                rank = 1
                postdata = pm['name']+f"さんの頻出単語TOP{WCOUNT}\n"
                for word,count in wc1:
                    postdata = postdata + str(rank)+"位:"+word+"_"+str(count)+"回\n"
                    rank+=1
                print(postdata)
                try:
                  create_wordcloud_ja(wc0,pm['name'])
                except Exception as eex:
                  print(eex)
                imagepath= f"{OUTPATH}"+pm['name']+".png"
                try:
                  if os.path.exists(imagepath) == True:
                      print(imagepath)
                      with open(imagepath,"rb") as ff:
                         img_data = ff.read()
                         client.send_image(text=f"{postdata}", image=img_data,image_alt='wordcloud image',reply_to=reply_to(notification))
                      os.remove(imagepath)
                  else:
                    print("no exists image1")
                    client.send_post(text=f"{postdata}", reply_to=reply_to(notification))
                except Exception as ExcExc:
                    print("no exists image2"+str(ExcExc))
                    client.send_post(text=f"{postdata}", reply_to=reply_to(notification))
            else:
                if "ヘルプ" in pm['content']:
                    postdata = "「ランク」\nという文字列であなたの過去2000ポストの頻出単語を出すよ"
                    client.send_post(text=f"{postdata}", reply_to=reply_to(notification))

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
#    while True:
     try:
        seen_at = read_notifications_and_reply(client, seen_at)
     except Exception as e:
        print(f"exception line261 {e}")
        login(client, initial_wait=60)
     finally:
        print('ok')
#        time.sleep(10)
     return 'OK'

if os.name == 'nt':
    fn_main()
