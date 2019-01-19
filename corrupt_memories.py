#!/usr/bin/env python3
from datetime import datetime
import json
import os
from pprint import pprint
import random
import re
import struct
from subprocess import call
import sys

import flickrapi
import markovify
from mastodon import Mastodon
import nltk
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import requests
import tweepy

with open('config.json') as f:
    config = json.load(f)
apikey = config['flickrkey']
apisecret = config['flickrsecret']
flickr = flickrapi.FlickrAPI(apikey, apisecret, format='parsed-json')

mastodon = Mastodon(
    client_id=config['mast_client'],
    client_secret=config['mast_secret'],
    access_token=config['mast_key'],
    api_base_url=config['mast_base_url']
)

tw_auth = tweepy.OAuthHandler(config['tw_consumer_key'], config['tw_consumer_secret'])
tw_auth.set_access_token(config['tw_token'], config['tw_token_secret'])
tw = tweepy.API(tw_auth)


class POSifiedText(markovify.Text):
    def word_split(self, sentence):
        words = re.split(self.word_split_pattern, sentence)
        words = [w for w in words if len(w) > 0]
        words = ["::".join(tag) for tag in nltk.pos_tag(words)]
        return words

    def word_join(self, words):
        sentence = " ".join(word.split("::")[0] for word in words)
        return sentence


def timestamp():
    return datetime.now().strftime("%y%m%d%H%M%S")

def get_image():
    with open('words.txt') as f:
        rand_word = random.choice(f.read().split())
    print(rand_word)
    p = flickr.photos.search(
        text=rand_word,
        per_page=500,
        page=random.choice(range(1, 11)),
        extras='url_l,tags',
        safesearch=2
    )
    photo = random.choice(p['photos']['photo'])
    purl = photo['url_l']
    if 'food' in photo['tags']:
        return None
    pprint(photo)
    r = requests.get(purl)
    with open('fimage.jpg', 'wb') as f:
        f.write(r.content)
    pic = Image.open('fimage.jpg')
    return pic

def get_text_color(color):
    color = color[1:]
    rgb = (color[0:2], color[2:4], color[4:6])
    rgbstr = b'aabbcc'
    p = struct.unpack('BBB', rgbstr.fromhex(color))
    return p


def get_color():
    letters = 'ABCDEF0123456489'
    color = ''.join([random.choice(letters) for i in range(6)])
    rgb = (color[0:2], color[2:4], color[4:6])
    rgbstr = b'aabbcc'
    p = struct.unpack('BBB', rgbstr.fromhex(color))
    return p

def get_colors():
    letters = 'ABCDEF0123456489'
    color = ''.join([random.choice(letters) for i in range(6)])
    rgb = (color[0:2], color[2:4], color[4:6])
    comp = ['%02X' % (255 - int(a, 16)) for a in rgb]
    complement = ''.join(comp)
    rgbstr = b'aabbcc'
    p = struct.unpack('BBB', rgbstr.fromhex(color))
    c = struct.unpack('BBB', rgbstr.fromhex(complement))
    return (p, c)


def add_pastel(pic, pastel):
    layer = Image.new('RGBA', pic.size, pastel + (128,))
    pic.paste(layer, (0, 0), layer)
    return pic


def select_section(pic):
    x = [i for i in range(pic.size[0] - 500)]
    y = [i for i in range(pic.size[1] - 500)]
    left = random.choice(x)
    right = left + 500
    top = random.choice(y)
    bottom = top + 500
    pic = pic.crop((left, top, right, bottom))
    return pic


def write_text(text, comp):
    text = text.replace('`', '')
    text = text.replace('"', '\\"')
    text = text.replace('!', '\\!')
    font = random.choice([i for i in os.listdir('fonts') if i.endswith('.ttf')])
    gravity = random.choice([
        'NorthWest',
        'North',
        'NorthEast',
        'West',
        'Center',
        'East',
        'SouthWest',
        'South',
        'SouthEast'
    ])
    images = [i for i in os.listdir() if i.startswith('glitch_out')]
    for img in images:
        pic = Image.open(img)
        w, h = pic.size
        w = str(int(w - (w / 10)))
        h = str(int(h - (h / 10)))
        cmd = 'convert -background none -gravity {} -font fonts/{} '.format(gravity, font)
        cmd += '-fill "rgb({},{},{})" -size {}x{} '.format(comp[0], comp[1], comp[2], w, h)
        cmd += 'caption:"{}" {} +swap -gravity center -composite {}'.format(text, img, img)
        print(cmd)
        call(cmd, shell=True)


def get_text():
    with open('cyber.json') as f:
        cyber = json.load(f)
    text_model = POSifiedText.from_json(cyber)
    text = text_model.make_short_sentence(80)
    return text


def glitch_image(pic, count=1):
    angle = random.choice([i for i in range(360)])
    interpol = random.choice([0, 1, 2])
    pic.save('glitch.png', 'PNG')
    cmd = './prismsort.py glitch.png -d -a {} -I {} -i 3 -n {}'.format(angle, interpol, count)
    print(cmd)
    call(cmd, shell=True)
    pic = Image.open('glitch_out0.png')
    return pic


def post_to_mastodon(pic_path, text):
    pic = mastodon.media_post(pic_path)
    mastodon.status_post(text, media_ids=[pic], sensitive=True)


def post_to_twitter(pic_path, text):
    tw.update_with_media(pic_path, text)


def make_gif():
    cmd = 'convert -delay 10 -loop 0 `ls -v glitch_out*` new.gif'
    call(cmd, shell=True)
    pic = Image.open('new.gif')

def cleanup():
    images = [i for i in os.listdir() if i.endswith(('.jpg', '.png', '.gif'))]
    for i in images:
        os.remove(i)

def main():
    pic = None
    while not pic:
        try:
            pic = get_image()
        except:
            continue
    pic.filter(ImageFilter.SHARPEN)
    combo = []
    while not combo:
        pastel = get_color()
        pic2 = add_pastel(pic, pastel)
        pic2 = select_section(pic2)
        bg_pic = pic2.resize((1,1))
        bg_color = bg_pic.getpixel((0,0))
        bg_color = '{:02x}{:02x}{:02x}'.format(*bg_color)
        combo = requests.get(f"https://randoma11y.com/combos?hex={bg_color}").json()
        print(bg_color)
    combo = combo[0]
    if combo['color_two'] != '#' + bg_color:
        complement = combo['color_two']
    else:
        complement = combo['color_one']
    pprint(combo)
    complement = get_text_color(complement)
    pic2 = glitch_image(pic2, count=10)
    text = get_text()
    write_text(text, complement)
    make_gif()
    try:
        post_to_mastodon('new.gif', text)
        post_to_twitter('new.gif', text)
        # large_image = Image.open('glitch_out0.png')
        # large_image = large_image.resize((1800, 1800))
        # large_image.save(os.path.join('hq', timestamp() + '.png'), 'PNG')
    except:
        pass
    cleanup()


if __name__ == '__main__':
    main()
