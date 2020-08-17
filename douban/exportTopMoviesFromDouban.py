#!/usr/bin/env python
#! encoding=utf-8

# Author        : kesalin@gmail.com
# Blog          : http://luozhaohui.github.io
# Date          : 2016/07/13
# Description   : 抓取豆瓣上指定标签的电影并导出为 Markdown 文件，多线程版本.
# Version       : 1.0.0.0
# Python Version: Python 3.7.3
# Beautiful Soup: http://beautifulsoup.readthedocs.io/zh_CN/v4.4.0/#

import os
import time
import timeit
import datetime
import re
import math
import queue
import requests

from threading import Thread
from bs4 import BeautifulSoup

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
    time.sleep(1)         # slow down a little(1 second)


# 电影信息类
class ItemInfo:

    def __init__(self, name, url, icon, num, people, comment):
        self.name = name
        self.url = url
        self.icon = icon
        self.ratingNum = num
        self.ratingPeople = people
        self.comment = comment
        self.compositeRating = num

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
def exportToMarkdown(tag, items, total):
    path = "{0}.md".format(tag)
    if(os.path.isfile(path)):
        os.remove(path)

    today = datetime.datetime.now()
    todayStr = today.strftime('%Y-%m-%d %H:%M:%S %z')
    file = open(path, 'a')
    file.write('## 说明\n\n')
    file.write(
        ' > 本页面是由 Python 爬虫根据电影推荐算法抓取豆瓣电影信息自动生成，列出特定主题排名靠前的一百或两百多部电影。  \n\n')
    file.write(' > 我使用的推荐算法似乎要比豆瓣默认的算法要可靠些，我可以根据特定主题对推荐算法进行调整。大家可以访问 '
               '[豆瓣电影爬虫](https://github.com/luozhaohui/python/blob/master/douban/exportTopMoviesFromDouban.py) 查看推荐算法。'
               '希望能得到大家的反馈与建议，改善算法，提供更精准的电影排名。  \n\n')
    file.write(' > 联系方式：  \n')
    file.write('    + 邮箱：kesalin@gmail.com  \n')
    file.write('    + 微博：[飘飘白云](http://weibo.com/kesalin)  \n')

    file.write('\n## {0} Top {1} 电影\n\n'.format(tag, len(items)))
    file.write('### 总共分析了 {0} 部电影，更新时间：{1}\n'.format(total, todayStr))

    i = 0
    for book in items:
        file.write('\n### No.{0:d} {1}\n'.format(i + 1, book.name))
        file.write(' > **电影名称**： [{0}]({1})  \n'.format(book.name, book.url))
        file.write(' > **豆瓣链接**： [{0}]({1})  \n'.format(book.url, book.url))
        file.write(' > **发行信息**： {0}  \n'.format(book.comment))
        file.write(' > **豆瓣评分**： {0}  \n'.format(book.ratingNum))
        if book.ratingPeople < 0:
            file.write(' > **评分人数**： 尚未上映  \n')
        else:
            file.write(' > **评分人数**： {0} 人  \n'.format(book.ratingPeople))
        i = i + 1
    file.close()

# 解析图书信息


def parseItemInfo(countryList, tag, minNum, maxNum, k, page, itemInfos):
    soup = BeautifulSoup(page, 'html.parser')
    items = soup.find_all("tr", "item")
    for item in items:
        # print(item.prettify())

        # get name & url & description
        itemName = ''
        itemUrl = ''
        description = ''
        content = item.find("div", "pl2")
        if content:
            href = content.find("a")
            if href:
                # print(href.prettify())
                itemUrl = href['href']
                contents = href.contents
                if contents:
                    itemName = contents[0].strip()
                    itemName = itemName.replace('\n', ' ').replace(
                        ' ', '').replace('/', ' / ')
                span = href.find("span")
                if span and span.string:
                    subTitle = span.string.strip()
                    itemName = '{0}{1}'.format(itemName, subTitle)

            des = content.find("p", 'pl')
            if des and des.string:
                description = des.string.strip()

        # print(" > name: {0}".format(itemName))
        # print(" > itemUrl: {0}".format(itemUrl))
        # print(" > description: {0}".format(description))

        # match the country list?
        if len(countryList):
            validCountry = True
            pattern = re.compile(r'(-)([0-9]*)(\()(.*)(\))')
            match = pattern.search(description)
            if match:
                country = match.group(4)
                if country not in countryList:
                    validCountry = False
                    for c in countryList:
                        pattern = re.compile(r'' + c)
                        match = pattern.search(description)
                        if match:
                            validCountry = True
                            break

            if not validCountry:
                #print(" > description: {0}".format(description))
                continue

        # get url and image
        itemImage = ''
        content = item.find("img")
        if content:
            itemImage = content['src']
        #print(" > image: {0}".format(itemImage))

        # get rating
        ratingNum = 0.0
        ratingPeople = 0
        content = item.find("span", "rating_nums")
        if content and content.string:
            ratingStr = content.string.strip()
            if len(ratingStr) > 0:
                ratingNum = float(ratingStr)
        content = item.find("span", "pl")
        if content:
            ratingStr = content.string.strip()
            if ratingStr == '(尚未上映)':
                ratingPeople = -1
            else:
                pattern = re.compile(r'(\()([0-9]*)(.*)(\))')
                match = pattern.search(ratingStr)
                if match:
                    ratingStr = match.group(2).strip()
                    if len(ratingStr) > 0:
                        ratingPeople = int(ratingStr)
        #print(" > ratingNum: {0}, ratingPeople: {1}".format(ratingNum, ratingPeople))

        # add imte info to list
        itemInfo = ItemInfo(itemName, itemUrl, itemImage,
                            ratingNum, ratingPeople, description)
        itemInfo.compositeRating = computeCompositeRating(
            tag, minNum, maxNum, k, ratingNum, ratingPeople)
        itemInfos.append(itemInfo)

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
    tag = ''
    items = []
    queue = None
    minNum = 5
    maxNum = 5000
    k = 0.25
    countryList = []

    def __init__(self, t_name, tag, countryList, minNum, maxNum, k, queue, items):
        Thread.__init__(self, name=t_name)
        self.queue = queue
        self.items = items
        self.tag = tag
        self.minNum = max(10, min(200, minNum))
        self.maxNum = max(1000, min(maxNum, 20000))
        self.k = max(0.01, min(1.0, k))
        self.countryList = countryList

    def stop(self):
        self.running = False

    def run(self):
        while True:
            if not self.running and self.queue.empty():
                break

            page = self.queue.get()
            if page:
                parseItemInfo(self.countryList, self.tag, self.minNum,
                              self.maxNum, self.k, page, self.items)
            self.queue.task_done()


def spider(tag, countryList, minNum, maxNum, k):
    print('   抓取 [{0}] 电影 ...'.format(tag))
    start = timeit.default_timer()

    # all producers
    q = queue.Queue(20)
    itemInfos = []
    producers = []

    # get first page of doulist
    url = "https://movie.douban.com/tag/{0}".format(tag)
    page = getHtml(url)
    if not page:
        print(' > invalid url {0}'.format(url))
    else:
        nextPageStart = 100000
        lastPageStart = 0

        # get url of other pages in doulist
        soup = BeautifulSoup(page, 'html.parser')
        content = soup.find("div", "paginator")
        if content != None:
            # print(content.prettify())
            for child in content.children:
                if child.name == 'a':
                    pattern = re.compile(r'(start=)([0-9]*)(.*)(&type=)')
                    match = pattern.search(child['href'])
                    if match:
                        index = int(match.group(2))
                        if nextPageStart > index:
                            nextPageStart = index
                        if lastPageStart < index:
                            lastPageStart = index

        # process current page
        #print(" > process page : {0}".format(url))
        q.put(page)

        # create consumer
        consumer = Consumer('Consumer', tag, countryList,
                            minNum, maxNum, k, q, itemInfos)
        consumer.start()

        # create producers
        producers = []
        for pageStart in range(nextPageStart, lastPageStart + nextPageStart, nextPageStart):
            pageUrl = "{0}?start={1:d}&type=T".format(url, pageStart)
            producer = Producer('Producer_{0:d}'.format(
                pageStart), pageUrl, q)
            producer.start()
            producers.append(producer)
            #print(" > process page : {0}".format(pageUrl))
            slow_down()

        # wait for all producers
        for producer in producers:
            producer.join()

        # wait for consumer
        consumer.stop()
        q.put(None)
        consumer.join()

        # summrise
        total = len(itemInfos)
        elapsed = timeit.default_timer() - start
        print("   获取 %d 部 [%s] 电影信息，耗时 %.2f 秒" % (total, tag, elapsed))
        return itemInfos


def process(tags):
    tagList = tags[0].split(',')
    country = tags[1]
    minNum = tags[2]
    maxNum = tags[3]
    k = tags[4]
    outputNum = max(100, tags[5])

    countryList = []
    if country != "":
        countryList = country.split(',')
        countryList = list(set(countryList + tagList))
        # print(countryList)

    items = []
    # spider
    for tag in tagList:
        tagItems = spider(tag.strip(), countryList, minNum, maxNum, k)
        items = list(set(items + tagItems))

    total = len(items)
    print(" > 共获取 {0} 部 [{1}] 不重复电影信息".format(total, tags[0]))

    # sort
    items = sorted(items)
    # get top 100
    if len(items) > outputNum:
        items = items[0:outputNum]

    # export to markdown
    exportToMarkdown(tagList[0], items, total)

# =============================================================================
# 排序算法
# =============================================================================


def computeCompositeRating(tag, minNum, maxNum, k, num, people):
    people = max(1, min(maxNum, people))
    if people <= minNum:
        people = minNum / 3
    peopleWeight = math.pow(people, k)
    if people < 200:
        return (num * 40 + peopleWeight * 60) / 100.0
    elif people < 500:
        return (num * 50 + peopleWeight * 50) / 100.0
    elif people < 1000:
        return (num * 60 + peopleWeight * 40) / 100.0
    elif people < 5000:
        return (num * 70 + peopleWeight * 30) / 100.0
    elif people < 10000:
        return (num * 80 + peopleWeight * 20) / 100.0
    else:
        return (num * 90 + peopleWeight * 10) / 100.0


# =============================================================================
# 程序入口：抓取指定标签的书籍
# =============================================================================
def run_spider():
    tags = [
        ["经典", "", 100, 50000, 0.25, 300],
        ["剧情,感人", "", 100, 50000, 0.25, 250],
        ["励志", "", 100, 50000, 0.25, 200],
        ["喜剧", "", 100, 50000, 0.25, 300],
        ["搞笑", "", 100, 50000, 0.25, 300],
        ["爱情,情色,浪漫", "", 100, 50000, 0.25, 250],
        ["科幻,魔幻", "", 100, 50000, 0.25, 150],
        ["动作,暴力", "", 100, 50000, 0.25, 200],
        ["史诗", "", 100, 50000, 0.25, 100],
        ["战争", "", 100, 50000, 0.25, 200],
        ["悬疑", "", 100, 50000, 0.25, 200],
        ["犯罪,黑帮", "", 100, 50000, 0.25, 200],
        ["恐怖,惊悚", "", 100, 50000, 0.25, 200],
        ["青春", "", 100, 50000, 0.25, 200],
        ["文艺", "", 100, 50000, 0.25, 200],
        ["童话,童年", "", 100, 50000, 0.25, 200],
        ["纪录片,传记", "", 100, 50000, 0.25, 300],
        ["黑色幽默", "", 100, 50000, 0.25, 200],
        ["亚洲,日本,韩国,印度,泰国,新加坡", "日语,韩语", 100, 50000, 0.25, 300],
        ["欧美,美国,加拿大,欧洲,德国,英国,法国,意大利,西班牙,澳大利亚,俄罗斯,伊朗,巴西,瑞典,丹麦,波兰,捷克,比利时,墨西哥,土耳其",
            "美国,英语,法语,俄语,德语,西班牙语,意大利语", 100, 50000, 0.25, 300],
        ["中国,中国大陆,内地", "大陆,汉语,普通话", 100, 50000, 0.25, 300],
        ["香港", "香港", 100, 50000, 0.25, 300],
        ["台湾", "台湾", 100, 50000, 0.25, 200],
        ["美国", "英语", 100, 50000, 0.25, 300],
        ["英国", "英语", 100, 50000, 0.25, 200],
        ["法国", "法语", 100, 50000, 0.25, 200],
        ["日本", "日语,先行", 100, 50000, 0.25, 300],
        ["韩国", "韩语,朝鲜", 100, 50000, 0.25, 200],
    ]

    start = timeit.default_timer()

    for tag in tags:
        process(tag)

    elapsed = timeit.default_timer() - start
    print("== 总耗时 %.2f 秒 ==" % (elapsed))


if __name__ == '__main__':
    if login_douban(username, password):
        run_spider()
    else:
        print("Invalid username or password.")
