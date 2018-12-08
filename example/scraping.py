# -*- coding: utf-8 -*-
# file_name : scraping.py

import os
import requests
from smtplib import SMTP
from bs4 import BeautifulSoup
from optparse import OptionParser
from collections import OrderedDict
from datetime import datetime
from dateutil.relativedelta import relativedelta

SEARCH_URL = 'http://www.g2b.go.kr:8101/ep/tbid/tbidList.do?taskClCds=&bidNm=%s&searchDtType=1&fromBidDt=%s&toBidDt=%s&fromOpenBidDt=&toOpenBidDt=&radOrgan=1&instNm=&area=&regYn=Y&bidSearchType=1&searchType=1'

DATABASE_FILE = '.db'
sended_title_list = OrderedDict()

def write_db():
    with open(DATABASE_FILE, 'w') as f:
        for k, v in sended_title_list.items():
            f.write("%s$%s\n" % (k, v))

def read_db():
    if not os.path.exists(DATABASE_FILE):
        return

    global sended_title_list
    with open(DATABASE_FILE, 'r') as f:
        for line in f.readlines():
            if line.strip() == '':
                continue

            k = line.split('$')[0].strip()
            v = line.split('$')[1].strip()
            sended_title_list[k] = v

def send_mail(today, content):
    from_addr = '[송신자의 메일 주소]'
    to_addr = '[수신자의 메일 주소]'
    username = '[송신자의 메일 계정 아이디]'
    password = '[송신자의 메일 계정 비밀번호]'
    subject = '[%s] Daily report' % today

    mail_content = 'From: %s\nTo: %s\nSubject: %s\n%s' % (from_addr, to_addr, subject, content)

    server = SMTP('smtp.gmail.com:587')
    server.starttls()
    server.login(username, password)
    server.sendmail(from_addr, to_addr, mail_content.encode('euc-kr'))
    server.quit()

def get_search_date():
    end_date = datetime.now()
    end_date_str = end_date.strftime('%Y/%m/%d')
    start_date = end_date - relativedelta(months=1)
    start_date_str = start_date.strftime('%Y/%m/%d')
    return (start_date_str, end_date_str)

def generate_message(keywords, titles):
    msg = '검색 키워드 - %s\n\n' % keywords
    for title, link in titles.items():
        msg += '%s\n - %s\n\n' % (title, link)

    return msg

def scraping(start_date, end_date, keyword):
    response = requests.get(SEARCH_URL % (keyword, start_date, end_date))
    soup = BeautifulSoup(response.text, 'html5lib')

    titles = soup.select('#resultForm > div.results > table > tbody > tr > td > div > a')

    new_title = OrderedDict()
    for i, title in enumerate(titles):
        # 위의 구분자로 정확한 값을 추출할 수가 없다.
        # 프로그램을 실행시켜보면, 다음과 같이 두 쌍의 데이터가 출력이 된다.
        # - <a href="http://www.g2b.go.kr:8081/ep/invitation/publish/bidInfoDtl.do?bidno=20181133004&amp;bidseq=00&amp;releaseYn=Y&amp;taskClCd=5 ">20181133004-00</a>
        # - <a href="http://www.g2b.go.kr:8081/ep/invitation/publish/bidInfoDtl.do?bidno=20181133004&amp;bidseq=00&amp;releaseYn=Y&amp;taskClCd=5 ">지진해일 경보시스템 소프트웨어 기능개선 용역</a>
        # 첫번째 데이터는 날짜에 대한 값으로 이와 같은 형태가 반복되니, 약간의 로직을 추가하여, 짝수 번째 데이터만 출력되게 한다.
        if i % 2 == 0:
            continue

        if title.text.strip() not in sended_title_list:
            new_title[title.text.strip()] = title.get('href').strip()

    return new_title

def search(keywords):
    if keywords.strip() == '':
        return

    read_db()

    start_date, end_date = get_search_date()
    new_title_list = OrderedDict()
    for keyword in keywords.split(','):
        # keyword 를 인코딩 한 값을 [2:-1] 로 슬라이싱 하지 않으면, b'' 정보도 같이 출력 된다.
        # - str(keyword.encode('euc-kr'))       : b'%bc%d2%c7%c1%c6%ae%bf%fe%be%ee'
        # - str(keyword.encode('euc-kr'))[2:-1] : %bc%d2%c7%c1%c6%ae%bf%fe%be%ee
        # 그리고, Python 에서 기본으로 인코딩 문자를 \x 로 출력하는데, 이를 % 로 변경해줘야 웹 서버에서 인식을 한다.
        encoded_keyword = str(keyword.encode('euc-kr'))[2:-1].replace('\\x', '%')
        new_title_list.update(scraping(start_date, end_date, encoded_keyword))

    if len(new_title_list) == 0:
        print ('There are no update news.')
        return

    global sended_title_list
    sended_title_list.update(new_title_list)
    send_mail(end_date, generate_message(keywords, new_title_list))

    write_db()

def main():
    option = OptionParser(usage='%prog', version='%prog 1.0')
    option.add_option('-k', '--keywords', dest='keywords', type='string', help='Please enter keywords to search')

    (options, args) = option.parse_args()

    if options.keywords is None:
        print ('There are no input arguments.')
        return

    search(options.keywords)


if __name__ == '__main__':
    main()
