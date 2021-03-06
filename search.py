from difflib import SequenceMatcher
import ssl
from elasticsearch import Elasticsearch
import cardsFactory
import os
import library
from googlesearch import search
import requests
from bs4 import BeautifulSoup
import urllib2
import google_domain_search
import json

with open(os.path.join(os.path.dirname(__file__),"appsettings.json"), 'r') as Data:
    data = json.load(Data)
    elasticsearchIP = data.get('ElasticsearchIP', '')
    user = data.get('user', '')
    secret = data.get('secret', '')

es = Elasticsearch([elasticsearchIP],
                    send_get_body_as='POST',
                    http_auth=(user, secret),)

SIMILAR_RATE = "70%"

def add_question_to_db(question, answer, link):
    if link == 'Null':
        link = None
    res = es.search(index=library.GROUP, body={"query": {"match_all": {}}})
    index = int(res['hits']['total'])+1
    data = {
        'question': question,
        'answer': answer,
        'link': link,
    }
    res = es.index(index=library.GROUP, doc_type='question', id=index, body=data)
    es.indices.refresh(index=library.GROUP)
    return True


def check_question_db():
    es.indices.delete(index=library.GROUP, ignore=[400, 404])
    for question, property_list in library.QUESTION_DIC.items():
        index = property_list[0]
        answer = property_list[1]
        if len(property_list)==3:
            link = property_list[2]
        else:
            link = None
        data = {
        'question': question,
        'answer': answer,
        'link': link,
        }   
        res = es.index(index=library.GROUP, doc_type='question', id=index, body=data)
    es.indices.refresh(index=library.GROUP)


def similar(stringA, stringB):
    return SequenceMatcher(None, stringA.lower(), stringB.lower()).ratio()


def elasticsearch(parsed_string):
    result_list = []
    res = es.search(index=library.GROUP,  body={'query':{ 'match':{ "question":{'query': parsed_string,"minimum_should_match": SIMILAR_RATE}} }})
    for hit in res['hits']['hits']:
        result_list.append([hit["_source"]['question'], hit["_id"]])
    return result_list


def getTheAns(index, action):
    res = es.get(index=library.GROUP, doc_type='question', id=index)
    if action is None:
        if res['_source']['link'] != None:
            return cardsFactory._text_with_bottom_link_card(res['_source']['question'],res['_source']['answer'], "The link ...", res['_source']['link'])
        else:
            return cardsFactory._text_card(res['_source']['question'],res['_source']['answer']) 
    else:
        if res['_source']['link'] != None:
            return cardsFactory._respons_text_with_bottom_link_card(action,res['_source']['question'],res['_source']['answer'], "The link ...", res['_source']['link'])
        else:
            return cardsFactory._respons_text_card(action,res['_source']['question'],res['_source']['answer'])  


def google_search(search_data):

    response = dict()
    cards = list()
    widgets = list()
    header = {
    'header': {
    'title': 'Google result for '+search_data,
    'subtitle': 'City of Edmonton chatbot',
    'imageUrl': 'http://www.gwcl.ca/wp-content/uploads/2014/01/IMG_4371.png',
    'imageStyle': 'IMAGE'
    }
    }
    button1text = 'Ask support team!'
    button2text = 'No, thanks.'
    button1value = search_data
    button2value = 'didnt_help'
    cards.append(header)
    found = False
    # WARNING!! 1.5 seconds is already small enough, DO NOT change the pause time, otherwise the app will be blocked
    for url in google_domain_search.search_with_customized(search_data, start=0,stop=2, num=3,pause=1.5, domains=['support.google.com']):
        found = True
        title = findTitle(url)
        widgets.append(
            {'buttons': [{'textButton': {'text': title, 'onClick': {'openLink': {'url': url}}}}]}
        )

    if not found:
        text = "Sorry, no answers found. Do you want to ask one of our support team members?"
        widgets.append(
        {'textParagraph': {'text': text}}
        )

    widgets.append(
    {'buttons': [{'textButton': {'text': button1text,'onClick': {'action': {'actionMethodName': "doTextButtonAction",'parameters': [{'key': "param_key",'value': button1value}]}}}}]}
    )
    widgets.append(
    {'buttons': [{'textButton': {'text': button2text,'onClick': {'action': {'actionMethodName': "doTextButtonAction",'parameters': [{'key': "param_key",'value': button2value}]}}}}]}
    )
    cards.append({ 'sections': [{ 'widgets': widgets }]})
    response['cards'] = cards   
    return response


def findTitle(url):
    webpage = urllib2.urlopen(url).read()
    title = str(webpage).split('<title>')[1].split('</title>')[0]
    return html_decode(title)


def html_decode(s):
    htmlCodes = (
            ("'", '&#39;'),
            ('"', '&quot;'),
            ('>', '&gt;'),
            ('<', '&lt;'),
            ('&', '&amp;')
        )
    for code in htmlCodes:
        s = s.replace(code[1], code[0])
    return s


def main(parsed_string, user_input):
    if parsed_string == "":
        parsed_string = user_input

    search_used = "Elastic"
    result_list = elasticsearch(parsed_string)
    return result_list, search_used, library.GROUP
