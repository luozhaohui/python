#!/usr/bin/env python
# encoding=utf-8

# Author        : kesalin@gmail.com
# Blog          : http://luozhaohui.github.io
# Date          : 2016/12/24
# Description   : Douban Reading Annual Statistics.
# Version       : 1.0.0.0
# Python Version: Python 3.7.3
#
# sudo apt-get install python-matplotlib
# sudo apt-get install python-numpy python-scipy python-matplotlib ipython ipython-notebook python-pandas python-sympy python-nose
#

# data format:
#
# ##No.3 荆棘鸟
# > Name: [荆棘鸟](https://book.douban.com/subject/1086249/)
# > Publish: [澳] 考琳·麦卡洛 / 曾胡 / 译林出版社 / 1998-7 / 28.00元
# > Reading: 三星 2017-09-30 读过 标签: 文学
# > Comment: 澳大利亚的“《飘》”不如美国的《飘》，相当程度低美化了德罗海达庄园的生活。讲述一家三代女人的爱情，单纯的爱，单纯的迷恋，单纯的伤害。翻译很用心很用心。

import os
import re
import sys
import string
import datetime
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontManager
from pylab import mpl
import subprocess

############################################################################################################

# reload(sys)
# sys.setdefaultencoding("utf-8")


class BookInfo:
    def __init__(self, name, url, nums, month, tag, comment, publish):
        self.name = name
        self.url = url
        self.ratingNums = nums
        self.readMonth = month
        self.tag = tag
        self.comment = comment
        self.publish = publish


def get_rating_ref_png_name(year):
    return u'{0}_reading_rate.png'.format(str(year))


def get_rating_save_png_name(year):
    return u'{0}/{1}'.format(str(year), get_rating_ref_png_name(year))


def get_tags_ref_png_name(year):
    return u'{0}_reading_tags.png'.format(str(year))


def get_tags_save_png_name(year):
    return u'{0}/{1}'.format(str(year), get_tags_ref_png_name(year))


def get_raw_data_path(year):
    return u'{0}/{0}reading_raw.md'.format(str(year), str(year))


def get_markdown_path(year):
    return u'{0}/{0}reading.md'.format(str(year), str(year))


def read_file(path):
    lines = []

    if os.path.isfile(path):
        with open(path, 'r', encoding='UTF-8') as handle:
            for line in handle.readlines():
                line = line.strip()
                if len(line) > 0:
                    lines.append(line)
    return lines


def num_to_kanji(num):
    dict = {1: "一星", 2: "两星", 3: "三星", 4: "四星", 5: "五星"}
    if num >= 1 and num <= 5:
        return dict[num]
    else:
        print(" ** error: invalid rating num {0}".format(num))
        return ""


def num_to_stars(num):
    dict = {1: "★", 2: "★★", 3: "★★★", 4: "★★★★", 5: "★★★★★"}
    if num >= 1 and num <= 5:
        return dict[num]
    else:
        print(" ** error: invalid rating num {0}".format(num))
        return "☆"


def kanji_to_num(kanji):
    dict = {"一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5}
    return dict[kanji]


def get_spaces():
    return "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"


def get_book_by_rating(books, rating):
    return [book for book in books if book.ratingNums == rating]


def get_book_by_tag(books, tag):
    return [book for book in books if book.tag == tag]


def output_by_rating_num(file, total, rating, books):
    count = len(books)
    if count > 0:
        file.write(' > {0}图书 {1} 本，占比 {2:2.1f}%  \n'.format(
            num_to_kanji(rating), count, count * 100.0/total))


def output_tags(file, tags, total, year):
    file.write('### 标签统计:\n')
    title = u'{0}年阅读标签统计: 总计 {1} 本'.format(str(year), total)
    generate_pie(tags, title, get_tags_save_png_name(year))
    file.write('![标签统计]({0})\n\n'.format(get_tags_ref_png_name(year)))

    for key, value in tags:
        file.write(' > {0} {1} 本  \n'.format(key, value))


def output_by_rating(file, index, rating, books):
    count = len(books)
    if count == 0:
        return index

    file.write('### {0} 图书: {1} 本\n'.format(num_to_kanji(rating), count))

    books.sort(key=lambda x: (x.ratingNums, x.tag), reverse=True)
    for book in books:
        #print('{0} {1} {2}\n'.format(book.name, book.ratingNums, book.tag))
        file.write('#### No.{0:d} {1}\n'.format(index, book.name))
        file.write(' > 图书名称：[{0}]({1})  \n'.format(book.name, book.url))
        file.write(' > 豆瓣链接：[{0}]({1})  \n'.format(book.url, book.url))
        file.write(' > 出版信息：{0}  \n'.format(book.publish))
        #file.write(' > 标签：{0}{1}评分：**{2}**  \n'.format(book.tag, get_spaces(), num_to_kanji(book.ratingNums)))
        file.write(' > 标签：{0}{1}评分：**{2}**  \n'.format(book.tag,
                                                       get_spaces(), num_to_stars(book.ratingNums)))
        file.write(' > 我的评论：{0}  \n'.format(book.comment))
        file.write('\n')
        index = index + 1
    file.write('\n')
    return index


def output_by_tag(file, books, index, tag):
    count = len(books)
    if count == 0:
        return index

    file.write('### {0}: {1} 本\n'.format(tag, count))

    books.sort(key=lambda x: (x.ratingNums), reverse=True)
    for book in books:
        #print('{0} {1} {2}\n'.format(book.name, book.ratingNums, book.tag))
        file.write('#### No.{0:d} {1}\n'.format(index, book.name))
        file.write(' > 图书名称：[{0}]({1})  \n'.format(book.name, book.url))
        file.write(' > 豆瓣链接：[{0}]({1})  \n'.format(book.url, book.url))
        file.write(' > 出版信息：{0}  \n'.format(book.publish))
        #file.write(' > 标签：{0}{1}评分：**{2}**  \n'.format(book.tag, get_spaces(), num_to_kanji(book.ratingNums)))
        file.write(' > 标签：{0}{1}评分：**{2}**  \n'.format(book.tag,
                                                       get_spaces(), num_to_stars(book.ratingNums)))
        file.write(' > 我的评论：{0}  \n'.format(book.comment))
        file.write('\n')
        index = index + 1
    file.write('\n')
    return index


def generate_pie(items, title, savefilename):
    total = 0
    for key, value in items:
        total += value

    labels = []
    fracs = []
    explode = []
    for key, value in items:
        labels.append(u"{0} {1} 本".format(key, value))
        fracs.append(value * 100.0/total)
        explode.append(0)
    explode[0] = 0.02
    # for label in labels:
    #     print("{0} ".format(label))
    # print(fracs)
    # print(explode)
    show_pie(labels, fracs, explode, title, savefilename)


def show_pie(labels, fracs, explode, title, savefilename):
    plt.figure(figsize=(6, 6))
    ax = plt.axes([0.1, 0.1, 0.8, 0.8])
    plt.pie(fracs, explode=explode, labels=labels,
            autopct='%1.1f%%', shadow=True)
    plt.title(title, bbox={'facecolor': '0.8', 'pad': 12})
    plt.savefig(savefilename)
    # plt.show()
    plt.close()


def analyze_book(books, tags, year):
    path = get_markdown_path(year)
    if os.path.isfile(path):
        os.remove(path)
    file = open(path, 'a', encoding='UTF-8')

    total = len(books)

    rating5 = get_book_by_rating(books, 5)
    rating4 = get_book_by_rating(books, 4)
    rating3 = get_book_by_rating(books, 3)
    rating2 = get_book_by_rating(books, 2)
    rating1 = get_book_by_rating(books, 1)

    file.write('## {0}年阅读统计，本页面由代码自动生成\n'.format(str(year)))
    file.write('## 总计阅读 {0} 本\n'.format(total))
    file.write('### 评价统计:\n')

    rating_dict = {u"五星": len(rating5), u"四星": len(rating4),
                   u"三星": len(rating3), u"两星": len(rating2), u"一星": len(rating1)}
    filter_dict = {key: rating_dict[key]
                   for key in rating_dict.keys() if (rating_dict[key] > 0)}
    #items = sorted(filter_dict.iteritems(), key=lambda d:d[1], reverse = True)
    items = filter_dict.items()
    title = u'{0}年阅读评价统计: 总计 {1} 本'.format(str(year), total)
    generate_pie(items, title, get_rating_save_png_name(year))
    file.write('![评价统计]({0})\n\n'.format(get_rating_ref_png_name(year)))

    output_by_rating_num(file, total, 5, rating5)
    output_by_rating_num(file, total, 4, rating4)
    output_by_rating_num(file, total, 3, rating3)
    output_by_rating_num(file, total, 2, rating2)
    output_by_rating_num(file, total, 1, rating1)

    file.write('\n')

    tags = sorted(tags.items(), key=lambda d: d[1], reverse=True)
    # print(tags)

    output_tags(file, tags, total, year)

    file.write('\n')

    index = 1
    # index = output_by_rating(file, index, 5, rating5)
    # index = output_by_rating(file, index, 4, rating4)
    # index = output_by_rating(file, index, 3, rating3)
    # index = output_by_rating(file, index, 2, rating2)
    # index = output_by_rating(file, index, 1, rating1)

    for key, value in tags:
        index = output_by_tag(file, get_book_by_tag(books, key), index, key)

    file.close()


def is_begin(line):
    pattern = re.compile(r'(##No\.)([0-9]+)(.*)')
    match = pattern.search(line)
    return match != None


def is_end(line, index):
    return len(line) == 0 and index >= 4


def process(datapath, year):
    books = []
    tags = {}

    name = ''
    url = ''
    ratingNums = 0
    readMonth = -1
    tag = ''
    comment = ''
    publish = ''

    index = 0
    lines = read_file(datapath)
    for line in lines:
        index = index + 1

        pattern = re.compile(r'(##No\.)([0-9]+)(.*)')
        match = pattern.search(line)
        if match != None:
            index = 0
            name = ''
            url = ''
            ratingNums = 0
            readMonth = -1
            tag = ''
            comment = ''
            publish = ''
            continue

        pattern = re.compile(r'(> )([a-zA-Z]+)(: )(.*)')
        match = pattern.search(line)
        if match != None:
            itemName = match.group(2)
            itemContent = match.group(4).strip()

            if itemName == 'Name':
                pattern = re.compile(r'(\[)(.*)(\])(\()(.*)(\))')
                match = pattern.search(itemContent)
                if match:
                    name = match.group(2).strip()
                    url = match.group(5)
                    #print(" >> new book {0}, url: {1}".format(name, url))
                else:
                    print(" == error: invalid begin line: {0}".format(line))
                continue

            elif itemName == "Publish":
                publish = itemContent
                continue

            elif itemName == 'Reading':
                pattern = re.compile(
                    r'(.*)(星\s*)(\d{4})(-)(\d{2})(-)(\d{2})(.*)(标签:\s*)(.*)')
                match = pattern.search(itemContent)
                if match:
                    ratingNums = kanji_to_num(match.group(1))
                    readMonth = int(match.group(5))
                    tag = match.group(10)
                    for t in tag.split(' '):
                        if t in tags:
                            tags[t] = tags[t] + 1
                        else:
                            tags[t] = 1

                    #print(" >> rating {0}, month: {1}, tag: {2}".format(ratingNums, readMonth, tag))
                else:
                    print(" == error: invalid rating line: {0}".format(line))
                continue

            elif itemName == 'Comment':
                comment = itemContent

                # end parse item
                book = BookInfo(name, url, ratingNums,
                                readMonth, tag, comment, publish)
                books.append(book)

        if index > 5:
            print(" ** unknown info: {0}".format(line))

    print(" >> total {0} books".format(len(books)))

    analyze_book(books, tags, year)


# =============================================================================
# matplot
# =============================================================================

def get_matplot_zh_font():
    fm = FontManager()
    mat_fonts = set(f.name for f in fm.ttflist)

    output = subprocess.check_output(
        'fc-list :lang=zh -f "%{family}\n"', shell=True)
    zh_fonts = set(f.split(',', 1)[0] for f in output.split('\n'))
    available = list(mat_fonts & zh_fonts)

    print('*' * 10, '可用的字体', '*' * 10)
    for f in available:
        print(f)
    return available


def set_matplot_zh_font():
    # For windows: https://www.cnblogs.com/KeenLeung/p/12427022.html
    # 查找字体路径
    print(matplotlib.matplotlib_fname())
    # 查找字体缓存路径
    print(matplotlib.get_cachedir())

    plt.rcParams['font.sans-serif'] = ['SimHei']
    plt.rcParams['font.serif'] = ['SimHei']

    # For Ubuntu
    # available = get_matplot_zh_font()
    # if len(available) > 0:
    #     mpl.rcParams['font.sans-serif'] = [available[0]]    # 指定默认字体
    #     # 解决保存图像是负号'-'显示为方块的问题
    #     mpl.rcParams['axes.unicode_minus'] = False


# =============================================================================
# 程序入口
# =============================================================================

if __name__ == '__main__':
    set_matplot_zh_font()

    rootDir = os.path.dirname(os.path.abspath(__file__))

    for year in os.listdir(rootDir):
        path = os.path.join(rootDir, year)
        if os.path.isdir(path):
            pattern = re.compile(r'([0-9]{4})')
            match = pattern.search(year)
            if match:
                rawdataPath = get_raw_data_path(year)
                if os.path.exists(rawdataPath):
                    print("process {0}".format(rawdataPath))
                    process(rawdataPath, year)
