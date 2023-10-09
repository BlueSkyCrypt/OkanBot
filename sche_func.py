import traceback
import time
import json
import pprint
import datetime
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import re
import parse
from enum import Enum

ONES = "Ones"
PERYEAR = "PerYear"
PERMONTH = "PerMonth"
PERWEEK = "PerWeek"
PERDAY = "PerDay"
NEXTYEAR = "NextYear"
NEXTMONTH = "NextMonth"
NEXTWEEK = "NextWeek"
NEXTDAY = "NextDay"
NEXTNEXTDAY = "NextNextDay"
NWEEK = "NWeek"

def get_nth_weekday_of_month(target_date, n, weekday):
    first_day = target_date.replace(day=1)

    first_weekday = first_day.weekday()
    if first_weekday <= weekday:
        days_until_target_weekday = weekday - first_weekday + (7 * (n - 1))
    else:
        days_until_target_weekday = 7 - first_weekday + weekday + (7 * (n - 1))

    target_weekday = first_day + timedelta(days=days_until_target_weekday)

    if target_weekday.month != target_date.month:
        target_weekday = target_weekday.replace(day=1)

    return target_weekday

def calculate_ones(item, current_time):
    return datetime.datetime.strptime(item["date"], '%Y-%m-%d %H:%M:%S')

def calculate_perday(item, reg_date):
    alarm_time = datetime.datetime.strptime(item["date"].split(' ')[-1], '%H:%M:%S')
    next_date = reg_date.replace(hour=alarm_time.hour, minute=alarm_time.minute, second=alarm_time.second,microsecond=0)
    if next_date <= reg_date:
        next_date += timedelta(days=1)
    return next_date

def calculate_perweek(item, current_time):
    days_ahead = item["windex"] - current_time.weekday()
    if days_ahead <= 0: 
        days_ahead += 7
    next_date = current_time + timedelta(days_ahead)
    alarm_time = datetime.datetime.strptime(item["date"].split(' ')[-1], '%H:%M:%S')
    return next_date.replace(hour=alarm_time.hour, minute=alarm_time.minute, second=alarm_time.second,microsecond=0)

def calculate_permonth(item, current_time):
    nsyuu = item["nsyuu"]
    windex = item["windex"]
    alarm_date = datetime.datetime.strptime(item["date"].split(' ')[0], '%Y-%m-%d')
    if nsyuu != -1:
        if windex == -1:
            windex = 0
        alarm_date=get_nth_weekday_of_month(current_time,nsyuu,windex)
        return alarm_date
    else:
        next_date = current_time.replace(day=alarm_date.day)
        if next_date < current_time:
            if current_time.month == 12:
                next_date = next_date.replace(month=1, year=current_time.year+1)
            else:
                next_date = next_date.replace(month=current_time.month+1)
        alarm_time = datetime.datetime.strptime(item["date"].split(' ')[-1], '%H:%M:%S')
        return next_date.replace(hour=alarm_time.hour, minute=alarm_time.minute, second=alarm_time.second,microsecond=0)

def calculate_peryear(item, current_time):
    alarm_date = datetime.datetime.strptime(item["date"].split(' ')[0], '%Y-%m-%d')
    next_date = current_time.replace(month=alarm_date.month, day=alarm_date.day)
    if next_date < current_time:
        next_date = next_date.replace(year=current_time.year+1)
    alarm_time = datetime.datetime.strptime(item["date"].split(' ')[-1], '%H:%M:%S')
    return next_date.replace(hour=alarm_time.hour, minute=alarm_time.minute, second=alarm_time.second,microsecond=0)

def calculate_nextday(item, current_time):
    next_date = current_time + timedelta(days=1)
    alarm_time = datetime.datetime.strptime(item["date"].split(' ')[-1], '%H:%M:%S')
    return next_date.replace(hour=alarm_time.hour, minute=alarm_time.minute, second=alarm_time.second,microsecond=0)

def calculate_nextweek(item, current_time):
    reg_date = datetime.datetime.strptime(item["regdate"], '%Y-%m-%d %H:%M:%S')
    days_ahead = item["windex"] - reg_date.weekday()
    if days_ahead <= 0: 
        days_ahead += 7
    next_date = reg_date + timedelta(days=days_ahead)
    alarm_time = datetime.datetime.strptime(item["date"].split(' ')[-1], '%H:%M:%S')
    return next_date.replace(hour=alarm_time.hour, minute=alarm_time.minute, second=alarm_time.second,microsecond=0)

def calculate_nextmonth(item, current_time):
    reg_date = datetime.datetime.strptime(item["regdate"].split(' ')[0], '%Y-%m-%d')
    nsyuu = item["nsyuu"]
    windex = item["windex"]
    alarm_date = datetime.datetime.strptime(item["date"].split(' ')[0], '%Y-%m-%d')
    if nsyuu != -1:
        if windex == -1:
            windex = 0
        alarm_date=get_nth_weekday_of_month(alarm_date,nsyuu,windex)
        print(alarm_date)
        return alarm_date
    else:
        reg_date = datetime.datetime.strptime(item["regdate"], '%Y-%m-%d %H:%M:%S')
        if reg_date.month == 12:
            next_date = reg_date.replace(month=1, year=reg_date.year+1)
        else:
            next_date = reg_date.replace(month=reg_date.month+1)
        alarm_time = datetime.datetime.strptime(item["date"].split(' ')[-1], '%H:%M:%S')
        return next_date.replace(hour=alarm_time.hour, minute=alarm_time.minute, second=alarm_time.second,microsecond=0)

def calculate_nextyear(item, current_time):
    reg_date = datetime.datetime.strptime(item["date"], '%Y-%m-%d %H:%M:%S')
    alarm_time = datetime.datetime.strptime(item["date"].split(' ')[-1], '%H:%M:%S')
    return reg_date.replace(hour=alarm_time.hour, minute=alarm_time.minute, second=alarm_time.second,microsecond=0)

def calculate_nextnextday(item, current_time):
    next_date = current_time + timedelta(days=2)
    alarm_time = datetime.datetime.strptime(item["date"].split(' ')[-1], '%H:%M:%S')
    return next_date.replace(hour=alarm_time.hour, minute=alarm_time.minute, second=alarm_time.second,microsecond=0)

def get_next_alarm_time(item, current_time):
    period = item["period"].lower()
    switch = {
        "ones": calculate_ones,
        "perday": calculate_perday,
        "perweek": calculate_perweek,
        "permonth": calculate_permonth,
        "peryear": calculate_peryear,
        "nextday": calculate_nextday,
        "nextweek": calculate_nextweek,
        "nextyear": calculate_nextyear,
        "nextmonth": calculate_nextmonth,
        "nextnextday": calculate_nextnextday,
    }
    return switch.get(period, lambda item, current_time: None)(item, current_time)

def get_schedule_status_from_dict(data):
    current_time = datetime.datetime.now()
    expired_alarms = []
    upcoming_alarms = []

    for item in data["schedule"]:
        next_alarm_time = get_next_alarm_time(item, current_time)
        if next_alarm_time is None:
            continue
        if next_alarm_time < current_time:
            item['nextalm'] = str(next_alarm_time)
            expired_alarms.append((item, next_alarm_time))
        else:
            item['nextalm'] = str(next_alarm_time)
            upcoming_alarms.append((item, next_alarm_time))

    return expired_alarms, upcoming_alarms

def display_alarms(expired, upcoming):
    print("=== Expired Alarms ===")
    for item, alarm_time in expired:
        print(f"Expired alarm for schedule '{item['message']}'")


def check_nsyuu(input_str: str) -> bool:
    if re.fullmatch(r'第.*曜.*',input_str)!=None:
       return True
    if re.fullmatch(r'第.*週',input_str)!=None:
       return True

def mod_uru(year:int,month:int,day:int):
    if month==2:
        if year/4!=0:
            if day > 28:
                return year,month,28
    return year,month,day

def check_ppi2(input_str: str) -> bool:
    if re.fullmatch(r'[0-3][0-9]日',input_str)==None:
        if re.fullmatch(r'[0-9]日',input_str)==None:
            return False
    return True

def check_gappi(input_str: str) -> bool:
    if "月曜日" in input_str:
        return False
    if "月" in input_str and "日" in input_str:
        return True
    return False


def dateobjmatch(input_list: list) -> list:
    sequence = []
    for obj in input_list:
        match len(re.findall("[/]",obj)):
            case 1:
                sequence.append((obj,"月日"))
            case 2:
                sequence.append((obj,"年月日"))
            case _:
                if check_nsyuu(obj) == True:
                    sequence.append((obj,"週"))
                elif check_gappi(obj) == True:
                    sequence.append((obj,"月日"))
                elif obj.isdigit() == True:
                    sequence.append((obj,"YMD"))
                elif check_ppi2(obj) == True:
                    sequence.append((obj,"日"))
                else:
                  match len(re.findall("曜",obj)):
                    case 1:
                        sequence.append((obj,"曜日"))
                    case _:
                        match len(re.findall("[:時分]",obj)):
                            case 1:
                                sequence.append((obj,"時分"))
                            case 2:
                                sequence.append((obj,"時分"))
                            case _:
                                match obj:
                                    case "今日":
                                        sequence.append((obj,"今日"))
                                    case "午前":
                                        sequence.append((obj,"午前"))
                                    case "朝":
                                        sequence.append((obj,"午前"))
                                    case "午後":
                                        sequence.append((obj,"午後"))
                                    case "夕方":
                                        sequence.append((obj,"午後"))
                                    case "明日":
                                        sequence.append((obj,"明日"))
                                    case "明後日":
                                        sequence.append((obj,"明後日"))
                                    case "来週":
                                        sequence.append((obj,"来週"))
                                    case "来月":
                                        sequence.append((obj,"来月"))
                                    case "来年":
                                        sequence.append((obj,"来年"))
                                    case "毎年":
                                        sequence.append((obj,"毎年"))
                                    case "毎月":
                                        sequence.append((obj,"毎月"))
                                    case "毎週":
                                        sequence.append((obj,"毎週"))
                                    case "毎日":
                                        sequence.append((obj,"毎日"))
                                    case _:
                                        if obj != "":
                                            sequence.append((obj,"不明"))
    return sequence

import datetime

def unpack_datetime(dt):
    year, month, day, hour, minute, second = dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second
    return year, month, day, hour, minute, second

def ymdtodatetime(value,current_datetime):
    print(f"Value={value}")
    # 数値を文字列に変換
    value_str = str(value)
    
    # 年、月、日、時、分、秒を初期化
    year = current_datetime.year
    month = 1
    day = 1
    hour = 0
    minute = 0
    second = 0
    
    length = len(value_str)
    print(length)
    if length >= 14:
        year = int(value_str[:4])
        month = int(value_str[4:6])
        day = int(value_str[6:8])
        hour = int(value_str[8:10])
        minute = int(value_str[10:12])
        second = int(value_str[12:14])
    elif length >= 12:
        year = int(value_str[:4])
        month = int(value_str[4:6])
        day = int(value_str[6:8])
        hour = int(value_str[8:10])
        minute = int(value_str[10:12])
        second = 0
    elif length >= 10:
        year = int(value_str[:4])
        month = int(value_str[4:6])
        day = int(value_str[6:8])
        hour = int(value_str[8:10])
        minute = 0
        second = 0
    elif length >= 8:
        year = int(value_str[:4])
        month = int(value_str[4:6])
        day = int(value_str[6:8])
        hour = 0
        minute = 0
        second = 0
    elif length >= 6:
        year = int(value_str[:4])
        month = int(value_str[4:6])
        day = 1
        hour = 0
        minute = 0
        second = 0
    if year < current_datetime.year:
       if length >=10:
           ## . . . . .
	   ##1011071234
           year = current_datetime.year
           month = int(value_str[:2])
           day = int(value_str[2:4])
           hour = int(value_str[4:6])
           minute = int(value_str[6:8])
           second = int(value_str[8:10])
       elif length >= 8:
           year = current_datetime.year
           month = int(value_str[:2])
           day = int(value_str[2:4])
           hour = int(value_str[4:6])
           minute = int(value_str[6:8])
           second = 0
       elif length >= 6:
           year = current_datetime.year
           month = int(value_str[:2])
           day = int(value_str[2:4])
           hour = int(value_str[4:6])
           minute = 0
           second = 0

    # 引数の現在のdatetimeの年を取得
    current_year = current_datetime.year
    
    # 年が2桁の場合、1900年以上の年に設定
    if year < 2000:
        year += 2000
    
    # 年が現在の年より古い場合、日付が現在の年の日付から開始されるように設定
    if year < current_year:
        date_time = current_datetime.replace(year=year, month=month, day=day, hour=hour, minute=minute, second=second)
    else:
        date_time = datetime.datetime(year, month, day, hour, minute, second)
    print(date_time)
    return date_time

def datesequencefunc(sequence:list,now:datetime) -> dict:
    year=now.year
    month=now.month
    day=now.day
    hour=0
    minute=0
    sec = 0
    msec = 0
    windex=-1
    period=ONES
    memo= ""
    input=""
    inputted=""
    td = 0
    nsyuu = -1

    delta=relativedelta()
    for seq in sequence:
        print(seq)
        match seq[1]:
            case "YMD":
                ymdtime = ymdtodatetime(seq[0],now)
                print("yyyy")
                year,month,day,hour,minute,sec = unpack_datetime(ymdtime)
                print("yyy")
            case "インプット":
                input = seq[0]
            case "メモ":
                memo += seq[0]
            case "不明":
                memo += seq[0]
            case "午後":
                td = 12
            case "曜日":
                windex = "月火水木金土日".index(seq[0].split('曜日')[0][-1])
            case "週":
                res = parse.parse("第{}週",seq[0])
                if res != None:
                    nsyuu = int(res[0])
                hour=0
                minute=0
                sec=0
                msec=0
            case "時分":
                inputted+="HHmm"
                res = parse.parse("{}:{}",seq[0])
                res2 = parse.parse("{}時半",seq[0])
                res3 = parse.parse("{}時",seq[0])
                res2 = parse.parse("{}時半",seq[0])
                if res != None:
                    hour = int(res[0])
                    minute = int(res[1])
                elif res2 !=None:
                    hour = int(res2[0])
                    minute = 30
                elif res3 !=None:
                    hour = int(res3[0])
                    minute = 0
                res = parse.parse("{}時{}分",seq[0])
                if res != None:
                    hour = int(res[0])
                    minute = int(res[1])
            case "月日":
                inputted+="MMDD"
                res = parse.parse("{}/{}",seq[0])
                if res != None:
                    month = int(res[0])
                    day = int(res[1])
                res = parse.parse("{}月{}日",seq[0])
                if res != None:
                    month = int(res[0])
                    day = int(res[1])
                res = parse.parse("{}月{} ",seq[0])
                if res != None:
                    month = int(res[0])
                    day = int(res[1])
            case "日":
                inputted+="DD"
                res =parse.parse("{}日",seq[0])
                if res != None:
                    day = int(res[0])
            case "年月日":
                inputted+="YYMMDD"
                res = parse.parse("{}/{}/{}",seq[0])
                if res != None:
                    year = int(res[0])
                    month = int(res[1])
                    day = int(res[2])
            case "明日":
                period = NEXTDAY
                delta=relativedelta(days=1)
            case "明後日":
                period = NEXTNEXTDAY
                delta=relativedelta(days=2)
            case "今日":
                period = ONES
            case "来週":
                period = NEXTWEEK
            case "来月":
                period = NEXTMONTH
                delta=relativedelta(months=1)
                hour=0
                minute=0
                sec=0
                msec=0
            case "来年":
                period = NEXTYEAR
            case "毎年":
                inputted+="YY"
                period = PERYEAR
                year = 1
            case "毎月":
                period = PERMONTH
                year = 1
                month = 1
                day = 1
            case "毎週":
                period = PERWEEK
                year = 1
                month = 1
                day = 1
            case "毎日":
                period = PERDAY
                year = 1
                month = 1
                day = 1
    if inputted == "YYMMDD":
        hour=0
        minute=0
        sec=0
        msec=0
    if inputted == "DD":
        sec,msec = 0,0
        ckdate = now.replace(year=year,month=month,day=day,hour=hour,minute=minute,second=sec,microsecond=msec)
        if now > ckdate:
            delta=delta+relativedelta(months=+1)
    if inputted.startswith("MMDD"):
        year,month,day = mod_uru(year,month,day)
        try:
            ckdate = now.replace(year=year,month=month,day=day,hour=hour,minute=minute,second=sec,microsecond=msec)
        except Exception as ee:
            day-=1
            ckdate = now.replace(year=year,month=month,day=day,hour=hour,minute=minute,second=sec,microsecond=msec)
        if year != 1:
         if now > ckdate:
              delta=relativedelta(years=+1)
    if period == PERWEEK:
        if windex != -1:
            month = windex+1
    else:
     if windex != -1:
         weekday = now.weekday()
         add_days = 7 - weekday + windex
         delta=delta+relativedelta(days=add_days)
    if hour < 13:
       hour = hour+td
       if hour > 23:
        hour=0
    try:
        retdate = now.replace(year=year,month=month,day=day,hour=hour,minute=minute,second=sec,microsecond=msec)
    except:
        retdate = now.replace(year=year,month=month,day=day-1,hour=hour,minute=minute,second=sec,microsecond=msec)
    if period.startswith("Per") == False:
        retdate = retdate + delta
    retdict ={"period":period,"windex":windex,"nsyuu":nsyuu,"date":str(retdate),"regdate":str(now),"message":memo,"inputstr":input}

    return retdict

def datemodify(tpl:list,now:datetime)->tuple:
   period = tpl[0]
   windex = tpl[1]
   retdate = tpl[2]
   inputted = tpl[3]

   if retdate < now:
       if 'YY' in inputted:
            retdate = retdate + datetime.timedelta(year=1)
       elif 'MM' in inputted:
            retdate = retdate.replace(year=retdate.year+1)

   return (period,windex,retdate,inputted)

def convert_kanji_to_int(string):
    result = string.translate(str.maketrans("零〇一壱二弐三参四五六七八九拾", "00112233456789十", ""))
    convert_table = {"十": "0", "百": "00", "千": "000", "万": "0000", "億": "00000000", "兆": "000000000000", "京": "0000000000000000"}
    unit_list = "|".join(convert_table.keys())
    while re.search(unit_list, result):
        for unit in convert_table.keys():
            zeros = convert_table[unit]
            for numbers in re.findall(f"(\d+){unit}(\d+)", result):
                result = result.replace(numbers[0] + unit + numbers[1], numbers[0] + zeros[len(numbers[1]):len(zeros)] + numbers[1])
            for number in re.findall(f"(\d+){unit}", result):
                result = result.replace(number + unit, number + zeros)
            for number in re.findall(f"{unit}(\d+)", result):
                result = result.replace(unit + number, "1" + zeros[len(number):len(zeros)] + number)
            result = result.replace(unit, "1" + zeros)
    return result

def fix_datestring(input_str:str) -> str:
#    input_str = input_str.replace("日の","日 ")
#    input_str = input_str.replace("日に","日 ")
#    input_str = input_str.replace("分に","分 ")
#    input_str = input_str.replace("時半に","時半 ")
#    input_str = input_str.replace("時に","時 ")
#    input_str = input_str.replace("朝の","朝 ")
#    input_str = input_str.replace("夜の","夜 ")
#    print("IIIII:"+input_str)
    input_str = convert_kanji_to_int(input_str)
    input_str = re.sub('([日朝分半夜時年]+)([のには]+)','\\1 \\2 ',input_str)
    input_str = input_str.replace("朝","朝 ")
    input_str = input_str.replace("来週","来週 ")
    input_str = input_str.replace("明日","明日 ")
    input_str = input_str.replace("明後日","明後日 ")
    input_str = input_str.replace("今月","今月 ")
    input_str = input_str.replace("来月","来月 ")
    input_str =  re.sub('([毎午前来夕後]+)([日週年月後前方]+)','\\1\\2 ',input_str)
#    print("OOOOO:"+input_str)
    return input_str

#re.sub('([a-z]+)@([a-z]+)', '\\2@\\1', s))

def fix_datestring2(input_str:str) -> str:
    re.find(input_str,"[1234567890]時.")

def str_to_datetime(input_str: str) -> json:
    print(input_str)
    save_input = input_str
    bunkatsu = input_str.split("\n")
    input_str=bunkatsu[0]
    memo = "\n".join(bunkatsu[1:])
#    if memo == "":
#        memo = "アラーム"
    now = datetime.datetime.now()
    now = now.replace(second=0,microsecond=0)
    day = now.date
    input_str =input_str.translate(str.maketrans({chr(0xFF01 + i): chr(0x21 + i) for i in range(94)}))
    input_str = fix_datestring(input_str)
    input_lists = re.split('[ 　]',input_str)
    try:
        sequence = dateobjmatch(input_lists)
        sequence.append((memo,"メモ"))
        sequence.append((save_input,"インプット"))
        tpl = datesequencefunc(sequence,now)
        retjson = json.loads(json.dumps(tpl))
        return retjson
    except Exception as ee:
        print(ee)
        return None

def d2d(in1:str,in2:datetime,hantei:bool=True) -> json:
    dtdt = str_to_datetime(in1)
    pprint.pprint(dtdt)
    ret = dtdt['date'] == str(in2)
    if ret != hantei:
       print(f"input:{in1}\nin: {dtdt['date']} out: {str(in2)}")
    return dtdt

def test_str_to_datetime(username):
    # 日付のみ指定された場合
    jsbase = {"username":username}
    js = []
    jsbase["schedule"]=js
    js.append(d2d("20231205\n\n誕生日",datetime.datetime(2023,10,5,18,00,0,0)))
    js.append(d2d("10091330\n\nもう家をでな",datetime.datetime(2023,10,5,18,00,0,0)))
#    js.append(d2d("20231205\n\n誕生日",datetime.datetime(2023,10,5,18,00,0,0)))
#    js.append(d2d("明日午後1時半\n\nそろそろ家を出る！",datetime.datetime(2023,10,5,18,00,0,0)))
#    js.append(d2d("明日午後13時半\n\nそろそろ家を出る！",datetime.datetime(2023,10,5,18,00,0,0)))
#    js.append(d2d("明日13時半\n\nそろそろ家を出る！",datetime.datetime(2023,10,5,18,00,0,0)))
#    js.append(d2d("今日の7時に大切な用事",datetime.datetime(2023,10,5,18,00,0,0)))
#    js.append(d2d("明日13:30\n家を出る",datetime.datetime(2023,10,5,18,00,0,0)))
#    js.append(d2d("今日 朝の７時に教えて",datetime.datetime(2023,10,5,18,00,0,0)))
#    js.append(d2d("202310051800 \n新アラーム",datetime.datetime(2023,10,5,18,00,0,0)))
#    js.append(d2d("2023100518 \n新アラーム",datetime.datetime(2023,10,5,18,00,0,0)))
#    js.append(d2d("20231005 19:00\n新アラーム",datetime.datetime(2023,10,5,19,00,0,0)))
#    js.append(d2d("8/1"       ,datetime.datetime(2024,8,1,0,0,0,0)))
#    js.append(d2d("10/5 12:46",datetime.datetime(2023,10,5,12,50,0,0)))
#    js.append(d2d("10/5 13:05",datetime.datetime(2023,10,5,13,5,0,0)))
#    js.append(d2d("10/1 １２：３４",datetime.datetime(2023,10,1,12,34,0,0)))
#    js.append(d2d("12月24日",datetime.datetime(2023,12,24,00,00,0,0)))
#    js.append(d2d("12月25日 １２：３４\nクリスマス",datetime.datetime(2023,12,24,12,34,0,0),False))
#    js.append(d2d("毎日 18:00",datetime.datetime(1,1,1,18,00,0,0)))
#    js.append(d2d("来週 火曜日 会議だよ",datetime.datetime(2023,10,3,00,00,0,0)))
#    js.append(d2d("来週 火曜日 19:00",datetime.datetime(2023,10,3,19,00,0,0)))
#    js.append(d2d("来週 水曜日 11:00",datetime.datetime(2023,10,4,11,00,0,0)))
#    js.append(d2d("毎週 月曜日 19:00",datetime.datetime(1,1,1,19,00,0,0)))
#    js.append(d2d("毎週 火曜日 19:00",datetime.datetime(1,2,1,19,00,0,0)))
#    js.append(d2d("毎週 水曜日 10:00",datetime.datetime(1,3,1,10,00,0,0)))
#    js.append(d2d("毎週水曜日 19:00",datetime.datetime(1,3,1,19,00,0,0)))
#    js.append(d2d("毎月 30日 23:59",datetime.datetime(1,1,30,23,59,0,0)))
#    js.append(d2d("毎月 3日 1:59",datetime.datetime(1,1,3,1,59,0,0)))
#    js.append(d2d("毎年 12/31 23:59",datetime.datetime(1,12,31,23,59,0,0)))
#    js.append(d2d("11/31 10:00",datetime.datetime(2024,2,28,10,00,00,0)))
#    js.append(d2d("2/29 10:00",datetime.datetime(2024,2,28,10,00,00,0)))
#    js.append(d2d("毎年 2/29 10:00",datetime.datetime(1,2,28,10,00,00,0)))
#    js.append(d2d("10/1 12:34 会議",datetime.datetime(2023,10,1,12,34,00,0)))
#    js.append(d2d("2024/10/1 12:34 会議",datetime.datetime(2024,10,1,12,34,00,0)))
#    js.append(d2d("毎週水曜日 19:00",datetime.datetime(1,3,1,19,00,00,0)))
#    js.append(d2d("来週火曜日 09:00 ごみの日",datetime.datetime(2023,10,3,9,00,00,0)))
#    js.append(d2d("毎日朝９時\n起床",datetime.datetime(1,1,1,9,0,0,0)))
#    js.append(d2d("毎日午前９時\n起床",datetime.datetime(1,1,1,9,0,0,0)))
#    js.append(d2d("毎日夕方９時\n起床",datetime.datetime(1,1,1,21,0,0,0)))
#    js.append(d2d("毎日夕方12時\n起床\n早起き",datetime.datetime(1,1,1,0,0,0,0)))
#    js.append(d2d("明日 朝８時\n起きろー",datetime.datetime(2023,9,30,8,0,0,0)))
#    js.append(d2d("明後日 朝８時\n起きろー",datetime.datetime(2023,10,1,8,0,0,0)))
#    js.append(d2d("25日\n燃えないゴミ",datetime.datetime(2023,10,25,0,0,0,0)))
#    js.append(d2d("5日\n燃えないゴミ",datetime.datetime(2023,11,5,0,0,0,0)))
#    js.append(d2d("毎月 第１週 火曜日\n燃えないゴミ",datetime.datetime(1,1,1,0,0,0,0)))
#    js.append(d2d("毎月 第２週 火曜日\n燃えないゴミ",datetime.datetime(1,1,1,0,0,0,0)))
#    js.append(d2d("毎月 第３週 火曜日\n燃えないゴミ",datetime.datetime(1,1,1,0,0,0,0)))
#    js.append(d2d("毎月 第４週 火曜日\n燃えないゴミ",datetime.datetime(1,1,1,0,0,0,0)))
#    js.append(d2d("毎月 第５週 火曜日\n燃えないゴミ",datetime.datetime(1,1,1,0,0,0,0)))
#    js.append(d2d("毎月 第６週 火曜日\n燃えないゴミ",datetime.datetime(1,1,1,0,0,0,0)))
#    js.append(d2d("来月 第３週 火曜日\n燃えないゴミ",datetime.datetime(1,1,1,0,0,0,0)))
#    js.append(d2d("来月 第１週 火曜日\n燃えないゴミ",datetime.datetime(1,1,1,0,0,0,0)))
#    js.append(d2d("毎月 10日 火曜日\n燃えないゴミ",datetime.datetime(1,1,10,0,0,0,0)))
#    js.append(d2d("来年 12/5 鵜川誕生日",datetime.datetime(2024,12,5,0,0,0,0)))
#    js.append(d2d("毎年 12/5 ",datetime.datetime(1,12,5,0,0,0,0)))
#    js.append(d2d("2023/10/01 10:00:00過去の時間",datetime.datetime(1,12,5,0,0,0,0)))
    expired,upcomming = get_schedule_status_from_dict(jsbase)
    expired = sorted(expired,key=lambda x: x[0]['nextalm'])
    upcomming = sorted(upcomming,key=lambda x: x[0]['nextalm'])
    pprint.pprint(expired)
    pprint.pprint(upcomming)
    for itm in expired:
        print("EXPIRED:"+itm[0]['inputstr'].replace("\n"," ") + "->" + itm[0]['nextalm'])
    for itm in upcomming:
        print("NEXT:"+itm[0]['inputstr'].replace("\n","_")+"===>"+itm[0]['message'].replace("\n","_")+ "->" + itm[0]['nextalm'])

print(test_str_to_datetime("ukawa.bsky.social"))
