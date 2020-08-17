#!/usr/bin/env python
#! encoding=utf-8

# Author        : kesalin@gmail.com
# Blog          : http://luozhaohui.github.io
# Date          : 2016/07/13
# Description   : 抓取豆瓣上指定标签的书籍并导出为 Markdown 文件，多线程版本.
# Version       : 1.0.0.0
# Python Version: Python 3.7.3
# Python Queue  : https://docs.python.org/2/library/queue.html
# Beautiful Soup: http://beautifulsoup.readthedocs.io/zh_CN/v4.4.0/#

import os
import time
import timeit
import datetime
import re
import string
import math
import json
import requests
import queue

from threading import Thread
from bs4 import BeautifulSoup, NavigableString, Tag

username = 'your_username'  # 填写你的豆瓣账号用户名
password = 'your_password'  # 填写你的豆瓣账号密码

# 生成Session对象，用于保存Cookie
session = requests.Session()

gHeaders = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.113 Safari/537.36',
}


def login_douban(username, password):
    """
    登录豆瓣
    :return:
    """
    # 登录URL
    login_url = 'https://accounts.douban.com/j/mobile/login/basic'
    # 请求头
    headers = gHeaders
    headers['Referer'] = 'https://accounts.douban.com/passport/login?source=main'
    # 传递用户名和密码
    data = {
        'name': username,
        'password': password,
        'remember': 'false'
    }
    try:
        r = session.post(login_url, headers=headers, data=data)
        r.raise_for_status()
    except:
        print('登录请求失败')
        return 0
    # 打印请求结果
    # print(r.text)
    return 1


def getHtml(url):
    data = ''
    try:
        r = session.get(url, headers=gHeaders)
        r.raise_for_status()
        data = r.text
    except:
        print("We failed to reach a server. Please check your url: " +
              url + ", and read the Reason.")
    return data


def slow_down():
    time.sleep(2)         # slow down a little


# 书籍信息类
class BookInfo:

    def __init__(self, name, url, icon, num, people, comment, ISBN=''):
        self.name = name
        self.url = url
        self.icon = icon
        self.ratingNum = num
        self.ratingPeople = people
        self.comment = comment
        self.compositeRating = num
        self.ISBN = ISBN

    def __hash__(self):
        return hash(self.url)

    def __eq__(self, other):
        if self.url == other.url:
            return True
        return False

    def __sortByCompositeRating(self, other):
        val = self.compositeRating - other.compositeRating
        if val < 0:
            return 1
        elif val > 0:
            return -1
        else:
            val = self.ratingPeople - other.ratingPeople
            if val < 0:
                return 1
            elif val > 0:
                return -1
            else:
                return 0

    def __cmp__(self, other):
        return self.__sortByCompositeRating(other)


# 导出为 Markdown 格式文件
def exportToMarkdown(filename, books, total):
    path = "{0}.md".format(filename)
    if(os.path.isfile(path)):
        os.remove(path)

    today = datetime.datetime.now()
    todayStr = today.strftime('%Y-%m-%d %H:%M:%S %z')
    file = open(path, 'a')
    file.write('\n## 我想读的书)\n\n')
    file.write('### 总计 {0:d} 本，更新时间：{1}\n'.format(total, todayStr))

    i = 0
    for book in books:
        file.write('\n### No.{0:d} {1}\n'.format(i + 1, book.name))
        file.write(' > **ISBN**： {0}  \n'.format(book.ISBN))
        file.write(' > **图书名称**： [{0}]({1})  \n'.format(book.name, book.url))
        file.write(' > **豆瓣链接**： [{0}]({1})  \n'.format(book.url, book.url))
        file.write(' > **豆瓣评分**： {0}  \n'.format(book.ratingNum))
        file.write(' > **评分人数**： {0} 人  \n'.format(book.ratingPeople))
        file.write(' > **内容简介**： {0}  \n'.format(book.comment))
        i = i + 1
    file.close()

    path = "{}.json".format(filename)
    if(os.path.isfile(path)):
        os.remove(path)

    books_dict = {}
    for book in books:
        if len(book.ISBN) > 0:
            books_dict[book.ISBN] = book.name
    file = open(path, 'w')
    json.dump(books_dict, file)
    file.close()


# 解析图书信息
def parseItemInfo(minNum, maxNum, k, page, bookInfos):
    soup = BeautifulSoup(page, 'html.parser')

    # get book name
    bookName = ''
    bookImage = ''
    tag = soup.find("a", 'nbg')
    if tag:
        bookName = tag['title'].strip()
        bookImage = tag['href']
    print(" > name: {0}, bookImage: {1}".format(bookName, bookImage))

    # get description
    description = ''
    content = soup.find("div", "intro")
    if content:
        deses = content.find_all('p')
        for des in deses:
            if des and des.string:
                intro = des.string.strip()
                description = description + intro
    #print(" > description: {0}".format(description))

    # get book url
    bookUrl = ''
    content = soup.find("div", "indent")
    if content:
        tag = content.find("a")
        if tag:
            bookUrl = tag['href']
            bookUrl = bookUrl.replace('/new_offer', '/')
    #print(" > url: {0}".format(bookUrl))

    # get ISBN
    isbn = ''
    content = soup.find("div", "subject clearfix")
    if content:
        brs = content.find_all('br')
        for br in brs:
            span = br.find("span")
            if span and span.string:
                span_str = span.string.strip()
                if span_str == 'ISBN:':
                    if br.contents:
                        for sub in br.contents:
                            if isinstance(sub, NavigableString):
                                sub_str = "{}".format(
                                    sub).strip()
                                if len(sub_str) > 0:
                                    # print("sub: {}".format(sub_str))
                                    isbn = sub_str

    ratingNum = 0.0
    ratingPeople = 0
    content = soup.find("div", "rating_self clearfix")
    if content:
        tag = content.find("strong", "ll rating_num ")
        if tag and tag.string:
            ratingStr = tag.string.strip()
            if len(ratingStr) > 0:
                ratingNum = float(ratingStr)
    content = soup.find("a", "rating_people")
    if content:
        tag = content.find('span')
        if tag:
            ratingStr = tag.string.strip()
            if len(ratingStr) > 0:
                ratingPeople = int(ratingStr)
    #print(" > ratingNum: {0}, ratingPeople: {1}".format(ratingNum, ratingPeople))

    # add book info to list
    bookInfo = BookInfo(bookName, bookUrl, bookImage,
                        ratingNum, ratingPeople, description, isbn)
    bookInfo.compositeRating = computeCompositeRating(
        minNum, maxNum, k, ratingNum, ratingPeople)
    bookInfos.append(bookInfo)


def parseItemUrlInfo(page, urls):
    soup = BeautifulSoup(page, 'html.parser')
    items = soup.find_all("li", "subject-item")
    for item in items:
        # print(item.prettify())

        # get item url
        url = ''
        content = item.find("div", "pic")
        if content:
            tag = content.find('a')
            if tag:
                url = tag['href']
        print(" > url: {0}".format(url))
        urls.append(url)

# =============================================================================
# 生产者-消费者模型
# =============================================================================


class Producer(Thread):
    url = ''

    def __init__(self, t_name, url, queue):
        Thread.__init__(self, name=t_name)
        self.url = url
        self.queue = queue

    def run(self):
        page = getHtml(self.url)
        if page:
            # block util a free slot available
            self.queue.put(page, True)


class Consumer(Thread):
    running = True
    books = []
    queue = None
    minNum = 5
    maxNum = 5000
    k = 0.25

    def __init__(self, t_name, minNum, maxNum, k, queue, books):
        Thread.__init__(self, name=t_name)
        self.queue = queue
        self.books = books
        self.minNum = max(10, min(200, minNum))
        self.maxNum = max(1000, min(maxNum, 20000))
        self.k = max(0.01, min(1.0, k))

    def stop(self):
        self.running = False

    def run(self):
        while True:
            if not self.running and self.queue.empty():
                break

            page = self.queue.get()
            if page:
                parseItemInfo(self.minNum, self.maxNum,
                              self.k, page, self.books)
            self.queue.task_done()


class ParseItemUrlConsumer(Thread):
    running = True
    urls = []

    def __init__(self, t_name, queue, urls):
        Thread.__init__(self, name=t_name)
        self.queue = queue
        self.urls = urls

    def stop(self):
        self.running = False

    def run(self):
        while True:
            if not self.running and self.queue.empty():
                break

            page = self.queue.get()
            if page:
                parseItemUrlInfo(page, self.urls)
            self.queue.task_done()


def spider(username, minNum, maxNum, k):
    print('   抓取我想读的书 ...')
    start = timeit.default_timer()

    # all producers
    q = queue.Queue(20)
    bookInfos = []
    producers = []

    # get first page of doulist
    wishUrl = "https://book.douban.com/people/{0}/wish".format(username)
    page = getHtml(wishUrl)
    if not page:
        print(' > invalid url {0}'.format(wishUrl))
    else:
        # get url of other pages in doulist
        soup = BeautifulSoup(page, 'html.parser')
        content = soup.find("div", "paginator")
        # print(content.prettify())
        if content is None:
            print("failed to request {}".format(wishUrl))
            return

        nextPageStart = 100000
        lastPageStart = 0
        for child in content.children:
            if child.name == 'a':
                pattern = re.compile(r'(start=)([0-9]*)(.*)(&sort=)')
                match = pattern.search(child['href'])
                if match:
                    index = int(match.group(2))
                    if nextPageStart > index:
                        nextPageStart = index
                    if lastPageStart < index:
                        lastPageStart = index

        # process current page
        q.put(page)

        urls = []
        # create consumer
        consumer = ParseItemUrlConsumer('ParseItemUrlConsumer', q, urls)
        consumer.start()

        # create parge item url producers
        # producers = []
        for pageStart in range(nextPageStart, lastPageStart + nextPageStart, nextPageStart):
            pageUrl = "https://book.douban.com/people/{}/wish?start={:d}&sort=time&rating=all&filter=all&mode=grid".format(
                username, pageStart)
            producer = Producer('Producer_{0:d}'.format(pageStart), pageUrl, q)
            producer.start()
            producers.append(producer)
            print(" > process page : {0}".format(pageUrl))
            slow_down()

        # wait for all producers
        for producer in producers:
            producer.join()

        # wait for consumer
        consumer.stop()
        q.put(None)
        consumer.join()

        urls = list(set(urls))
        bookQueue = queue.Queue(20)
        # producers.clear()
        producers[:] = []

        # create parse item consumer
        consumer = Consumer('Consumer', minNum, maxNum,
                            k, bookQueue, bookInfos)
        consumer.start()

        print(" page urls: ", len(urls))
        # create parge item producers
        for url in urls:
            producer = Producer(url, url, bookQueue)
            producer.start()
            producers.append(producer)
            print(" > process item : {0}".format(url))
            slow_down()

        # wait for all producers
        for producer in producers:
            producer.join()

        # wait for consumer
        consumer.stop()
        q.put(None)
        consumer.join()

        # summrise
        total = len(bookInfos)
        elapsed = timeit.default_timer() - start
        print("   获取 %d 本我想读的书，耗时 %.2f 秒" % (total, elapsed))
        return bookInfos


def process(wishUrl, minNum, maxNum, k):
    # spider
    books = spider(wishUrl, minNum, maxNum, k)
    if books:
        books = list(set(books))

        total = len(books)
        print(" > 共获取 {0} 本我想读的书".format(total))

        # sort
        books = sorted(books)
        # get top 100
        #books = books[0:100]

        # export to markdown
        exportToMarkdown('我想读的书', books, total)

# =============================================================================
# 排序算法
# =============================================================================


def computeCompositeRating(minNum, maxNum, k, num, people):
    people = max(1, min(maxNum, people))
    if people <= minNum:
        people = minNum / 3
    peopleWeight = math.pow(people, k)
    level4 = max(500, maxNum * 1 / 10)
    level5 = max(1000, maxNum * 3 / 10)
    if people < 50:
        return (num * 40 + peopleWeight * 60) / 100.0
    elif people < 100:
        return (num * 50 + peopleWeight * 50) / 100.0
    elif people < 200:
        return (num * 60 + peopleWeight * 40) / 100.0
    elif people < level4:
        return (num * 70 + peopleWeight * 30) / 100.0
    elif people < level5:
        return (num * 80 + peopleWeight * 20) / 100.0
    else:
        return (num * 90 + peopleWeight * 10) / 100.0


# =============================================================================
# 程序入口：抓取指定标签的书籍
# =============================================================================
def run_spider():
    start = timeit.default_timer()

    process(username, 30, 3000, 0.25)

    elapsed = timeit.default_timer() - start
    print("== 总耗时 %.2f 秒 ==" % (elapsed))


if __name__ == '__main__':
    if login_douban(username, password):
        run_spider()
    else:
        print("Invalid username or password.")
