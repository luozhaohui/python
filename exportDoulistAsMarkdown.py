#!/usr/bin/env python
#! encoding=utf-8

# Author        : kesalin@gmail.com
# Blog          : http://kesalin.github.io
# Date          : 2016/07/12
# Description   : 将豆列导出为 Markdown 文件. 
# Version       : 1.0.0.0
# Python Version: Python 2.7.3
#

import os
import time
import datetime
import re
import string
import urllib2
from bs4 import BeautifulSoup

gHeader = {"User-Agent": "Mozilla-Firefox5.0"}

# 书籍信息类
class BookInfo:
    name = ''
    url = ''
    icon = ''
    ratingNums = ''
    ratingPeople = ''
    comment = ''

    def __init__(self, name, url, icon, nums, people, comment):
        self.name = name
        self.url = url
        self.icon = icon
        self.ratingNums = nums
        self.ratingPeople = people
        self.comment = comment 

# 获取 url 内容
def getHtml(url):
    try :
        request = urllib2.Request(url, None, gHeader)
        response = urllib2.urlopen(request)
        data = response.read().decode('utf-8')
    except urllib2.URLError, e :
        if hasattr(e, "code"):
            print "The server couldn't fulfill the request: " + url
            print "Error code: %s" % e.code
        elif hasattr(e, "reason"):
            print "We failed to reach a server. Please check your url: " + url + ", and read the Reason."
            print "Reason: %s" % e.reason
    return data

# 转换 html 转义字符
def decodeHtmlSpecialCharacter(htmlStr):
    specChars = {"&ensp;" : "", \
                 "&emsp;" : "", \
                 "&nbsp;" : "", \
                 "&lt;" : "<", \
                 "&gt" : ">", \
                 "&amp;" : "&", \
                 "&quot;" : "\"", \
                 "&copy;" : "®", \
                 "&times;" : "×", \
                 "&divide;" : "÷", \
                 }
    for key in specChars.keys():
        htmlStr = htmlStr.replace(key, specChars[key])
    return htmlStr

# 导出为 Markdown 格式文件
def exportToMarkdown(doulistTile, doulistAbout, bookInfos):
    path = "{0}.md".format(doulistTile)
    if(os.path.isfile(path)):
        os.remove(path)

    today = datetime.datetime.now()
    todayStr = today.strftime('%Y-%m-%d %H:%M:%S %z')
    file = open(path, 'a')
    file.write('## {0}\n'.format(doulistTile))
    file.write('{0}\n'.format(doulistAbout))
    file.write('## 图书列表\n')
    file.write('### 总计 {0} 本，更新时间：{1}\n'.format(len(bookInfos), todayStr))
    i = 0
    for book in bookInfos:
        file.write('\n### No.{0:d} {1}\n'.format(i + 1, book.name))
        file.write(' > **图书名称**：[{0}]({1})  \n'.format(book.name, book.url))
        file.write(' > **豆瓣链接**：[{0}]({1})  \n'.format(book.url, book.url))
        file.write(' > **豆瓣评分**：{0}  \n'.format(book.ratingNums))
        file.write(' > **评分人数**：{0}  \n'.format(book.ratingPeople))
        file.write(' > **我的评论**：{0}  \n'.format(book.comment))
        i = i + 1
    file.close()

# 解析图书信息
def parseItemInfo(page, bookInfos):
    soup = BeautifulSoup(page, 'html.parser')
    items = soup.find_all("div", "doulist-item")
    for item in items:
        #itemStr = item.prettify().encode('utf-8')
        #print itemStr

        # get book name
        content = item.find("div", "title").contents[1]
        bookName = content.string.strip().encode('utf-8')

        # get book url and icon
        contents = item.find("div", "post")
        hrefStr = contents.find('a').prettify().encode('utf-8')
        #print hrefStr

        bookUrl = ''
        pattern = re.compile(r'(<a href=\")(.*)(\" target=)')
        match = pattern.search(hrefStr)
        if match:
            bookUrl = match.group(2)

        bookIcon = ''
        pattern = re.compile(r'(img src=\")(.*)(\" width=)')
        match = pattern.search(hrefStr)
        if match:
            bookIcon = match.group(2)
        #print " > Book {0} : {1}, {2}".format(bookName, bookUrl, bookIcon)

        # get rating
        ratingNums = ''
        ratingPeople = ''
        contents = item.find("div", "rating")
        for content in contents:
            if content.name != None and content.string != None:
                if content.get("class") != None:
                    ratingNums = content.string.encode('utf-8')
                else:
                    ratingPeople = content.string.encode('utf-8')
                    pattern = re.compile(r'(\()(.*)(\))')
                    match = pattern.search(ratingPeople)
                    if match:
                        ratingPeople = match.group(2)
        #print "   RatingNums: {0}, ratingPeople: {1}".format(ratingNums, ratingPeople)

        # get comment
        comment = ''
        contents = item.find_all("blockquote", "comment")
        comment = contents[0].contents[2].encode('utf-8')
        #print "   Comment: {0}".format(comment)

        # add book info to list
        bookInfo = BookInfo(bookName, bookUrl, bookIcon, ratingNums, ratingPeople, comment)
        bookInfos.append(bookInfo)

# 解析豆列 url
def parse(url):
    page = getHtml(url)
    soup = BeautifulSoup(page, 'html.parser')

    # get doulist title
    doulistTile = soup.html.head.title.string.encode('utf-8')
    print " > 获取豆列：" + doulistTile

    # get doulist about
    content = soup.find("div", "doulist-about")
    #print content.prettify().encode('utf-8')
    doulistAbout = ''
    for child in content.children:
        if child.string != None:
            htmlContent = child.string.strip().encode('utf-8')
            doulistAbout = "{0}\n{1}".format(doulistAbout, htmlContent)
    #print "doulist about:" + doulistAbout


    # get page urls
    pageUrls = []
    content = soup.find("div", "paginator")
    for child in content.children:
        childStr = "{0}".format(child)
        if childStr.startswith('<a href=') == True:
            childStr = decodeHtmlSpecialCharacter(childStr)
            pattern = re.compile(r'(<a href=")(.*)(=">)(\d*)(</a>)')
            match = pattern.search(childStr)
            if match:
                hrefStr = match.group(2)
                pageUrls.append(hrefStr)

    bookInfos = []

    # get books from current page
    #print " scan page : {0}".format(url)
    parseItemInfo(page, bookInfos)

    # get books from follow pages
    for pageUrl in pageUrls:
        #print " scan page : {0}".format(hrefStr)
        page = getHtml(pageUrl)
        parseItemInfo(page, bookInfos)

    total = len(bookInfos)
    print " > 共获取 {0} 本图书信息".format(total)

    exportToMarkdown(doulistTile, doulistAbout, bookInfos)

#=============================================================================
# 程序入口：解析指定豆列
parse("https://www.douban.com/doulist/1133232/")
