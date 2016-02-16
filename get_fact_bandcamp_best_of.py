from bs4 import BeautifulSoup
from itertools import chain
import pandas as pd
import requests
from tqdm import tqdm

markdown_fmt = '[*{},* by {}]({}) (released {})'.format

def tag_fmt(x):
    return '[https://bandcamp.com/tag/{}]({})'.format(x.replace(' ', '-'), x)

def get_markdown(data):
    mkdn = markdown_fmt(data['title'],
    data['artist'],
    data['url'],
    str(data['release_date']))
    if len(data['tags']) > 0:
        mkdn += ' :: '
        mkdn += ', '.join(tag_fmt(x) for x in data['tags'])

    return mkdn

def get_album_tuple(url):
    try:
        r = requests.get(url)
        bs = BeautifulSoup(r.text)

        # get artist and title
        title, artist = bs.find('meta', {'name': 'title'})[
            'content'].split(', by ')

        # get genre and other tags (location and other things included)
        tags = list(set(x.contents[0]
                        for x in bs.find_all('a', {'class': 'tag'})))

        release_date = pd.to_datetime(
            bs.find('meta', {'itemprop': 'datePublished'})['content'])

        return [url, title, artist, release_date, tags]

    except:
        return [url, '', '', '', []]


def get_bandcamp_from_fact(fact_url):
    r = requests.get(fact_url)
    bs = BeautifulSoup(r.text)
    all_urls = [x['href'].strip() for x in bs.find_all('a')]
    bcamp_urls = [x for x in all_urls if x.find('bandcamp.com') > -1]

    results = []
    for x in tqdm(bcamp_urls, leave=True):
        results.append([fact_url] + get_album_tuple(x))

    return pd.DataFrame.from_records(results, columns=['fact', 'url', 'title', 'artist', 'release_date', 'tags'])


def main():

    r = requests.get('http://www.factmag.com/tag/the-best-of-bandcamp/')
    bs = BeautifulSoup(r.text)
    best_of_urls = list(set(x['href'] for x in bs.find_all('a') if x['href'].find(
        'best') > -1 and x['href'].find('bandcamp') > -1 and x['href'].find('tag') < 0))

    results = []
    for x in tqdm(best_of_urls):
        results.append(get_bandcamp_from_fact(x))

    df = pd.concat(results)

    df['location'] = df.tags.apply(lambda x: [y for y in x if y[0].isupper()]).apply(
        lambda x: x[0] if len(x) > 0 else '')

    df.tags = df.tags.apply(lambda x: [y for y in x if not y[0].isupper()])

    tag_series = pd.Series(list(chain(*df.tags.values)), name='tags')
    tag_set = set(tag_series.value_counts().index[
                  tag_series.value_counts() > 1])
    df['common_tags'] = df.tags.apply(lambda x: [y for y in x if y in tag_set])



    return df
