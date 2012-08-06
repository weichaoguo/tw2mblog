#!/usr/bin/python
# -*- coding: utf-8 -*-

#
#Copyright (C) 2012 Vector Guo <vectorguo@gmail.com>
#
#Licensed under the Apache License, Version 2.0 (the "License");
#you may not use this file except in compliance with the License.
#You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
#Unless required by applicable law or agreed to in writing, software
#distributed under the License is distributed on an "AS IS" BASIS,
#WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#See the License for the specific language governing permissions and
#limitations under the License.
#

"""
An 'weibo bot' that sends translate pop tweets from twitter to weibo.com & t.qq.com
used tweepy library & sinaweibopy library & pyqqweibo library.
"""

from __future__ import unicode_literals
import sys
sys.path.insert(0, "..")
import webbrowser
import qqweibo

import tweepy

import weibo1

import ConfigParser
import string, os, time, urllib, re, random
try:
    import json
except ImportError:
    import simplejson as json

import utils

def get_tweepy_api(consumer_key, consumer_key_secret, access_token, access_token_secret):
    auth = tweepy.OAuthHandler(consumer_key, consumer_key_secret)
    auth.set_access_token(access_token, access_token_secret)
    return tweepy.API(auth)
def get_pyqqweibo_api(consumer_key, consumer_key_secret, access_token, access_token_secret):
    auth = qqweibo.OAuthHandler(consumer_key, consumer_key_secret)
    auth.setToken(access_token, access_token_secret)
    return qqweibo.API(auth, parser=qqweibo.ModelParser())
def get_sinaweibopy_api(consumer_key, consumer_key_secret, access_token, access_token_secret):
    access_token = weibo1.OAuthToken(access_token, access_token_secret, '')
    return  weibo1.APIClient(consumer_key, consumer_key_secret, access_token)

# translate contents from English to Chinese
# use youdao fanyi api need a key, others is ok.
def translate_en_zh_cn(key, keyfrom, contents):
    query = {'q':contents}
    return json.loads(urllib.urlopen("http://fanyi.youdao.com/openapi.do?keyfrom="+keyfrom+"&key="+key+"&type=data&doctype=json&version=1.1&"+urllib.urlencode(query)).read())["translation"][0]

def load_api():
    global youdao_key, youdao_keyfrom, tweepy_api, pyqqweibo_api, sinaweibopy_api
    #load APIs & keys
    cf = ConfigParser.ConfigParser()
    cf.read("tw2mbot.conf")
    #read youdao fanyi api key & keyfrom
    youdao_key = cf.get("youdao", "key")
    youdao_keyfrom = cf.get("youdao", "keyfrom")
    #load APIs
    tweepy_api = get_tweepy_api(cf.get("twitter", "consumer_key"), cf.get("twitter", "consumer_key_secret"), cf.get("twitter", "access_token"), cf.get("twitter", "access_token_secret")) 
    pyqqweibo_api = get_pyqqweibo_api(cf.get("tqq", "consumer_key"), cf.get("tqq", "consumer_key_secret"), cf.get("tqq", "access_token"), cf.get("tqq", "access_token_secret")) 
    sinaweibopy_api = get_sinaweibopy_api(cf.get("tsina", "consumer_key"), cf.get("tsina", "consumer_key_secret"), cf.get("tsina", "access_token"), cf.get("tsina", "access_token_secret")) 

def load_conf():
    global rt_chinese, update_limit, collect_limit, refresh_time, names, queue_size, followings, tweet_cache, published
    #load Consts
    cf = ConfigParser.ConfigParser()
    cf.read("tw2mbot.conf")
    # read conf & get apis
    rt_chinese = cf.get("general", "rt_chinese")
    #read youdao fanyi api key & keyfrom
    youdao_key = cf.get("youdao", "key")
    youdao_keyfrom = cf.get("youdao", "keyfrom")
    #read limits
    update_limit = string.atoi(cf.get("general", "update_limit"))
    collect_limit = string.atoi(cf.get("general", "collect_limit"))
    #read refresh time in seconds
    refresh_time = string.atof(cf.get("general", "refresh_time"))
    #read followings
    cf.read("followings.list")
    names = cf.options("followings")
    queue_size = len(names)
    followings = {}
    for name in names:
        followings[name] = cf.get("followings", name)
        # cache the newest tweet for every following guys to publish
        if name not in tweet_cache.keys():
            tweet_cache[name] = None
            published[name] = True

def publish(tweet):
    tweet_text = tweet.text
    content = tweet_text
    #clean & collect links, tags, mentions
    urls = re.findall("http://\S+", tweet_text)
    mentions = re.findall("@\S+", tweet_text)
    tags = re.findall("#[A-Za-z0-9]+", tweet_text)
    for i in range(len(urls)):
        content = content.replace(urls[i], "("+str(i)+")", 1)
    for i in range(len(mentions)):
        content = content.replace(mentions[i], "@"+str(i), 1)
    for i in range(len(tags)):
        content = content.replace(tags[i], "["+str(i)+"]", 1)
    #translation
    trans = translate_en_zh_cn(youdao_key, youdao_keyfrom, content.encode("utf-8", "ignore"))
    #trim 
    trans = trans.strip(' \n\t\r')
    #replace back mentions & tags etc.
    for i in range(len(mentions)):
        trans = trans.replace("@"+str(i), mentions[i]+" ", 1)
    for i in range(len(tags)):
        trans = trans.replace("["+str(i)+"]", tags[i]+"#", 1)
    
    #translate 'RT ' to Chinese
    trans = trans.replace('RT ', rt_chinese.decode("utf-8"), 1)
    
    #recover t.co short urls then shorten with t.cn
    for i in range(len(urls)):
        tcn_url = sinaweibopy_api.get.short_url__shorten(url_long=utils.unshortlink(urls[i], 2))[0]["url_short"]+" "
        trans = trans.replace("("+str(i)+")", tcn_url, 1)
        tweet_text = tweet_text.replace(urls[i], tcn_url, 1)
    
    #add prefix ...
    prefix = "#"+followings[tweet.author.screen_name.lower()].decode("utf-8")+"#:"
    trans = prefix + trans
    tweet_text = prefix + tweet_text
    #print tweet_text
    #print trans
    #updates tsina & tqq
    #interval between updates ...
    interval = 60
    ret = pyqqweibo_api.tweet.add(trans, clientip='127.0.0.1')
    time.sleep(random.randint(interval/2, 2*interval))
    pyqqweibo_api.tweet.show(ret.id).retweet(tweet_text)
    
    ret = sinaweibopy_api.post.statuses__update(status=tweet_text)
    time.sleep(random.randint(interval/2, 2*interval))
    ret_id = string.atol(ret["id"]) if type(ret["id"]) == type(u"") else ret["id"]
    sinaweibopy_api.post.statuses__repost(id=ret_id, status=trans)

def main():
    global tweet_cahce, published
    load_conf()
    load_api()
    cur_order = 0
    last_order = queue_size - 1
    #arbitrary value...
    since_id = 12325135 
    #refresh every 'refresh_time' in seconds
    try:
        while True:
            #collect tweets
            tweets = tweepy_api.home_timeline(since_id=since_id, count=collect_limit)
            for tweet in tweets:
                #save current max id as new since id
                since_id = tweet.id if (tweet.id > since_id) else since_id
                #update tweet cache
                name = tweet.author.screen_name.lower()
                if tweet_cache[name] is None or tweet.id > tweet_cache[name].id:
                    tweet_cache[name] = tweet
                    published[name] = False
            update_counter = 0
            while update_counter < update_limit:
                try:
                    if not published[names[cur_order]]:
                        update_counter = update_counter + 1
                        publish(tweet_cache[names[cur_order]])
                        published[names[cur_order]] = True
                    if cur_order == last_order:
                        cur_order = (cur_order + 1) % queue_size
                        break
                    cur_order = (cur_order + 1) % queue_size
                except:
                    cur_order = (cur_order + 1) % queue_size
                    continue
            last_order = (cur_order + queue_size - 1) % queue_size
            time.sleep(refresh_time)
            load_conf()
            load_api()
    except KeyboardInterrupt:
        return
#globals
global rt_chinese, update_limit, collect_limit, refresh_time, names, queue_size, followings, tweet_cache, published
global youdao_key, youdao_keyfrom, tweepy_api, pyqqweibo_api, sinaweibopy_api
tweet_cache={}
published={}

if __name__ == '__main__':
    main()
