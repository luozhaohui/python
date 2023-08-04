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
#
# pip3 install requests
# pip3 install BeautifulSoup4
#
import os
import time
import timeit
import datetime
import re
import string
import math
import requests
import queue

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
    """
    获取页面信息
    """
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


class BookInfo:
    """
    书籍信息类
    """

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


def exportToMarkdown(tag, books, total):
    """
    导出为 Markdown 格式文件
    """

    path = "{0}.md".format(tag)
    if(os.path.isfile(path)):
        os.remove(path)

    today = datetime.datetime.now()
    todayStr = today.strftime('%Y-%m-%d %H:%M:%S %z')
    file = open(path, 'a')
    file.write('## 说明\n\n')
    file.write(' > 本页面是由 Python 爬虫根据图书推荐算法抓取豆瓣图书信息自动生成，列出特定主题排名靠前的一百本图书。  \n\n')
    file.write(' > 我使用的推荐算法似乎要比豆瓣默认的算法要可靠些，因为我喜欢书，尤其是对非虚构类图书有一定了解，'
               '所以我可以根据特定主题对推荐算法进行调整。大家可以访问 '
               '[豆瓣图书爬虫](https://github.com/luozhaohui/python/blob/master/douban/exportTopBooksFromDouban.py) 查看推荐算法。'
               '希望能得到大家的反馈与建议，改善算法，提供更精准的图书排名。  \n\n')
    file.write(' > 联系方式：  \n')
    file.write('    + 邮箱：kesalin@gmail.com  \n')
    file.write('    + 微博：[飘飘白云](http://weibo.com/kesalin)  \n')

    file.write('\n## {0} Top {1} 图书\n\n'.format(tag, len(books)))
    file.write('### 总共分析了 {0} 本图书，更新时间：{1}\n'.format(total, todayStr))

    i = 0
    for book in books:
        file.write('\n### No.{0:d} {1}\n'.format(i + 1, book.name))
        file.write(' > **图书名称**： [{0}]({1})  \n'.format(book.name, book.url))
        file.write(' > **豆瓣链接**： [{0}]({1})  \n'.format(book.url, book.url))
        file.write(' > **豆瓣评分**： {0}  \n'.format(book.ratingNum))
        file.write(' > **评分人数**： {0} 人  \n'.format(book.ratingPeople))
        file.write(' > **内容简介**： {0}  \n'.format(book.comment))
        i = i + 1
    file.close()


def parseItemInfo(tag, minNum, maxNum, k, page, bookInfos):
    """
    解析图书信息
    """

    soup = BeautifulSoup(page, 'html.parser')
    items = soup.find_all("li", "subject-item")
    for item in items:
        # print(item.prettify())

        # get book name
        bookName = ''
        content = item.find("h2")
        if content:
            href = content.find("a")
            if href:
                bookName = href['title'].strip()
                span = href.find("span")
                if span and span.string:
                    subTitle = span.string.strip()
                    bookName = '{0}{1}'.format(bookName, subTitle)
        #print(" > name: {0}".format(bookName))

        # get description
        description = ''
        content = item.find("p")
        if content:
            description = content.string.strip()
        #print(" > description: {0}".format(description))

        # get book url and image
        bookUrl = ''
        bookImage = ''
        content = item.find("div", "pic")
        if content:
            tag = content.find('a')
            if tag:
                bookUrl = tag['href']
            tag = content.find('img')
            if tag:
                bookImage = tag['src']
        #print(" > url: {0}, image: {1}".format(bookUrl, bookImage))

        # get rating
        ratingNum = 0.0
        ratingPeople = 0
        content = item.find("span", "rating_nums")
        if content:
            ratingStr = content.string.strip()
            if len(ratingStr) > 0:
                ratingNum = float(ratingStr)
        content = item.find("span", "pl")
        if content:
            ratingStr = content.string.strip()
            pattern = re.compile(r'(\()([0-9]*)(.*)(\))')
            match = pattern.search(ratingStr)
            if match:
                ratingStr = match.group(2).strip()
                if len(ratingStr) > 0:
                    ratingPeople = int(ratingStr)
        #print(" > ratingNum: {0}, ratingPeople: {1}".format(ratingNum, ratingPeople))

        # add book info to list
        bookInfo = BookInfo(bookName, bookUrl, bookImage,
                            ratingNum, ratingPeople, description)
        bookInfo.compositeRating = computeCompositeRating(
            tag, minNum, maxNum, k, ratingNum, ratingPeople)
        bookInfos.append(bookInfo)


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
    books = []
    queue = None
    minNum = 5
    maxNum = 5000
    k = 0.25

    def __init__(self, t_name, tag, minNum, maxNum, k, queue, books):
        Thread.__init__(self, name=t_name)
        self.queue = queue
        self.books = books
        self.tag = tag
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
                parseItemInfo(self.tag, self.minNum, self.maxNum,
                              self.k, page, self.books)
            self.queue.task_done()


def spider(tag, minNum, maxNum, k):
    print('   抓取 [{0}] 图书 ...'.format(tag))
    start = timeit.default_timer()

    # all producers
    q = queue.Queue(20)
    bookInfos = []
    producers = []

    # get first page of doulist
    url = "https://book.douban.com/tag/{0}".format(tag)
    page = getHtml(url)
    if not page:
        print(' > invalid url {0}'.format(url))
    else:
        # get url of other pages in doulist
        soup = BeautifulSoup(page, 'html.parser')
        content = soup.find("div", "paginator")
        # print(content.prettify())

        nextPageStart = 0
        lastPageStart = 0
        if content:
            nextPageStart = 100000
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
        consumer = Consumer('Consumer', tag, minNum,
                            maxNum, k, q, bookInfos)
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
        total = len(bookInfos)
        elapsed = timeit.default_timer() - start
        print("   获取 %d 本 [%s] 图书信息，耗时 %.2f 秒" % (total, tag, elapsed))
        return bookInfos


def process(tags, ignore):
    tagList = tags[0].split(',')
    backlist = tags[1]
    minNum = tags[2]
    maxNum = tags[3]
    k = tags[4]

    books = []
    # spider
    for tag in tagList:
        tagBooks = spider(tag.strip(), minNum, maxNum, k)
        books = list(set(books + tagBooks))

    total = len(books)
    print(" > 共获取 {0} 本 [{1}] 不重复图书信息".format(total, tags[0]))

    if tags[0].find("文学") != -1 \
            or tags[0].find("文化") \
            or tags[0].find("绘本") \
            or tags[0] == "小说" \
            or tags[0] == "成长" \
            or tags[0].find("哲学") \
            or tags[0].find("政治"):
        books = list(set(books) - set(ignore))

    # sort
    books = sorted(books, key=lambda x: x.compositeRating, reverse=True)

    # get top 100
    topBooks = books[0:min(130, len(books))]

    # ignore blacklist
    if backlist:
        delList = []
        for book in topBooks:
            for bl in backlist:
                if book.name.find(bl) != -1:
                    delList.append(book.name)
                    break
        topBooks = [book for book in topBooks if book.name not in delList]
    topBooks = topBooks[0:min(100, len(topBooks))]

    # export to markdown
    exportToMarkdown(tagList[0], topBooks, total)
    return books


def computeCompositeRating(tag, minNum, maxNum, k, num, people):
    """
    排序算法
    """

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

    # blacklist
    classicBL = ["新概念英语", "大明宫词", "费恩曼物理学讲义", "经济学原理"]
    japanLibBL = ["苍井优", "知日", "杉浦康平", "设计中的设计", "我的造梦之路",
                  "版式设计原理", "家庭收纳1000例", "无缘社会", "未来ちゃん", "用洗脸盆吃羊肉饭"]
    programBL = ["三双鞋", "触动人心", "破茧成蝶", "MFC", "李开复", "沸腾十五年"]
    techBL = ["哲学家们都干了些什么", "你一定爱读的极简欧洲史", "一课经济学", "定本育儿百科",
              "儿童百科", "宝石"]
    politicsBL = ["剑桥中华人民共和国史", "我为什么要写作", "职场动物进化手册", "王小波",
                  "大明王朝", "观念的水位", "一课经济学", "雪", "毛泽东选集"]
    lawBL = ["七号房的礼物", "走不出的风景", "美国常春藤上的中国蜗牛"]
    philosophyBL = ["鲁迅全集", "人类简史", "孙子兵法", "上帝掷骰子吗", "中国历代政治得失",
                    "洞穴奇案", "规训与惩罚", "韦伯", "古拉格", "顾准", "王小波", "穷查理宝典", "思维的乐趣",
                    "毛泽东选集", "进化心理学", "一只特立独行的猪", "陈寅恪的最后20年", "生命之书", "自私的基因",
                    "金枝", "经济学的思维方式"]
    anthropologyBL = ["考古学", "贫穷的本质", "基因组"]
    pictureBookBL = ["花卉圣经", "窥视印度", "你今天心情不好吗", "猫国物语", "奈良美智横滨手稿",
                     "平如美棠", "一点巴黎", "一个人去跑步", "踮脚张望", "失乐园", "我的路"]

    tags = [
        ["杂文", None, 50, 5000, 0.25],
        ["散文", None, 50, 8000, 0.25],
        ["诗歌", None, 50, 4000, 0.25],
        ["漫画,日本漫画", None, 50, 8000, 0.275],
        ["绘本", pictureBookBL, 20, 5000, 0.25],
        ["科幻,科幻小说", None, 50, 8000, 0.275],
        ["魔幻,魔幻小说,玄幻,玄幻小说", None, 50, 8000, 0.275],
        ["推理,推理小说", None, 50, 8000, 0.275],
        ["武侠", None, 50, 8000, 0.3],
        ["悬疑", None, 50, 8000, 0.3],
        ["言情", None, 50, 8000, 0.3],
        ["青春,青春文学", None, 50, 8000, 0.3],
        ["童话", None, 20, 8000, 0.275],
        ["考古", None, 50, 4000, 0.25],
        ["电影", None, 50, 8000, 0.275],
        ["小说", None, 50, 8000, 0.3],

        ["编程,程序,算法,互联网", programBL, 30, 3000, 0.25],
        ["宗教,佛教", None, 50, 4000, 0.25],
        ["心理,心理学", None, 30, 3000, 0.25],
        ["社会,社会学", None, 30, 5000, 0.275],
        ["政治,政治学,自由主义", politicsBL, 30, 4000, 0.22],
        ["经济,经济学,金融", None, 30, 5000, 0.275],
        ["商业,投资,管理,创业", None, 30, 8000, 0.275],
        ["哲学,西方哲学,自由主义,思想", philosophyBL, 30, 3000, 0.25],
        ["法律,法学,民法,刑法,国际法", lawBL, 50, 4000, 0.25],
        ["文化,人文,思想,国学", None, 30, 8000, 0.275],
        ["历史,中国历史,近代史", None, 30, 8000, 0.3],
        ["人类学", anthropologyBL, 50, 4000, 0.25],
        ["数学", None, 50, 4000, 0.25],
        ["化学", None, 50, 4000, 0.25],
        ["地理,地理学", None, 50, 4000, 0.25],
        ["物理,物理学", None, 50, 4000, 0.25],
        ["生物,生物学", None, 50, 4000, 0.25],
        ["医学,临床医学", None, 50, 4000, 0.25],
        ["科技,科普,科学,神经网络", techBL, 30, 5000, 0.24],
        ["设计,用户体验,交互,交互设计,UCD,UE", None, 30, 3000, 0.25],
        ["成长,教育", None, 50, 5000, 0.25],
        ["名著,外国名著,经典,古典文学", classicBL, 50, 8000, 0.275],
        ["文学,经典,名著,外国名著,外国文学,中国文学,日本文学,当代文学", None, 50, 8000, 0.3],
        ["外国文学,外国名著", None, 50, 8000, 0.3],
        ["日本文学,日本", japanLibBL, 50, 8000, 0.3],
        ["中国文学", None, 50, 8000, 0.3],
        ["逻辑", None, 30, 3000, 0.3],
        ["教育", None, 30, 3000, 0.3],
        ["音乐", None, 30, 3000, 0.3],
    ]

    start = timeit.default_timer()

    ignore = []
    for tag in tags:
        tagName = tag[0]
        books = process(tag, ignore)
        if tagName.find("绘本") != -1 \
                or tagName.find("漫画") != -1 \
                or tagName.find("童话") != -1 \
                or tagName.find("青春") != -1 \
                or tagName.find("言情") != -1 \
                or tagName.find("武侠") != -1 \
                or tagName.find("悬疑") != -1 \
                or tagName.find("推理") != -1 \
                or tagName.find("科幻") != -1 \
                or tagName.find("魔幻") != -1 \
                or tagName.find("编程") != -1 \
                or tagName.find("宗教") != -1:
            ignore = list(set(books + ignore))

    elapsed = timeit.default_timer() - start
    print("== 总耗时 %.2f 秒 ==" % (elapsed))


if __name__ == '__main__':
    if login_douban(username, password):
        run_spider()
    else:
        print("Invalid username or password.")
