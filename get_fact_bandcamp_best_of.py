from bs4 import BeautifulSoup
from itertools import chain
import pandas as pd
import requests
from tqdm import tqdm

base_fmt = '[*{}*,]({}) by {}'.format


def album_year_mo_fmt(x):
    return '[*{}*]({}) ({})'.format(x['title'],
                                    x['url'],
                                    pd.to_datetime(x['release_date']).strftime('%-m/%Y'))


def loc_fmt(x):
    if len(x) == 0:
        return ''
    return ' from [{}](https://bandcamp.com/tag/{})'.format(x, x.lower())


def early_tag_fmt(x):
    return '[{},](https://bandcamp.com/tag/{})'.format(x, x.replace(' ', '-').replace('/', '-'))


def last_tag_fmt(x):
    return '[{}](https://bandcamp.com/tag/{})'.format(x, x.replace(' ', '-').replace('/', '-'))


def get_markdown_two(x):
    mkdn = ', '.join(x.ix[:, ['title', 'url', 'release_date'], :].apply(
        album_year_mo_fmt).tolist())

    all_tags = sorted(set(chain(*x.common_tags.values)))

    if len(all_tags) > 0:
        mkdn += ' :: '
        mkdn += ' '.join(early_tag_fmt(x) for x in all_tags[:-1])
        mkdn += ' ' + last_tag_fmt(all_tags[-1])

    return mkdn


def get_markdown(data):
    mkdn = base_fmt(data['title'],
                    data['url'],
                    data['artist'])

    mkdn += loc_fmt(data['location'])

    mkdn += ' ({})'.format(pd.to_datetime(data['release_date']).strftime('%Y'))

    if len(data['common_tags']) > 0:
        mkdn += ' :: '
        mkdn += ' '.join(early_tag_fmt(x) for x in data['common_tags'][:-1])
        mkdn += ' ' + last_tag_fmt(data['common_tags'][-1])

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


def get_data():

    r = requests.get('http://www.factmag.com/tag/the-best-of-bandcamp/')
    bs = BeautifulSoup(r.text, 'lxml')
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


def main():
    df = get_data()
    # missing_df = df.ix[df.title == '', :]
    df = df.ix[df.title != '', :]

    # df.sort_values(['artist', 'release_date', 'title'],
    #                ascending=[True, True, True], inplace=True)
    #
    # all_mkdn = df.apply(get_markdown, axis=1).drop_duplicates().values.tolist()

    all_artists = df.artist.unique()
    all_mkdn = []
    for x in all_artists:
        mkdn = '**{}** &bull; '.format(x)
        mkdn += ', '.join(sorted(set(df.ix[df.artist ==
                                           x, :].apply(album_year_mo_fmt, axis=1).values)))
        all_tags = sorted(
            set(chain(*df.ix[df.artist == x, 'common_tags'].values)))
        if len(all_tags) > 0:
            mkdn += ' &bull; '
            mkdn += ' '.join(early_tag_fmt(x) for x in all_tags[:-1])
            mkdn += ' ' + last_tag_fmt(all_tags[-1])

        all_mkdn.append(mkdn)

    with open('list.md', 'w') as outfile:
        outfile.write('\n\n'.join(all_mkdn))


if __name__ == "__main__":
    main()
