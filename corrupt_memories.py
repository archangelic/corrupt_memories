#!/usr/bin/env python3
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


class POSifiedText(markovify.Text):
    def word_split(self, sentence):
        words = re.split(self.word_split_pattern, sentence)
        words = [w for w in words if len(w) > 0]
        words = ["::".join(tag) for tag in nltk.pos_tag(words)]
        return words

    def word_join(self, words):
        sentence = " ".join(word.split("::")[0] for word in words)
        return sentence


def get_image():
    tags = [
        'computer',
        'cyberpunk',
        'cyber',
        'hacker',
        'circuit board',
        'wiring',
        'electronics'
    ]
    p = flickr.photos.search(
        per_page=500,
        page=random.choice(range(1, 11)),
        extras='url_l',
        safesearch=2,
        tags=random.choice(tags),
        tag_mode='all'
    )
    photo = random.choice(p['photos']['photo'])
    purl = photo['url_l']
    pprint(photo)
    r = requests.get(purl)
    with open('fimage.jpg', 'wb') as f:
        f.write(r.content)
    pic = Image.open('fimage.jpg')
    return pic


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


def write_text(pic, text, comp):
    pic.save('new.png', 'PNG')
    w, h = pic.size
    w = str(int(w - (w / 10)))
    h = str(int(h - (h / 10)))
    font = random.choice(os.listdir('fonts'))
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
    cmd = 'convert -background none -gravity {} -font fonts/{} '.format(gravity, font)
    cmd += '-fill "rgb({},{},{})" -size {}x{} '.format(comp[0], comp[1], comp[2], w, h)
    cmd += 'caption:"{}" new.png +swap -gravity center -composite new.png'.format(text)
    print(cmd)
    call(cmd, shell=True)
    pic = Image.open('new.png')
    return pic


def get_text():
    with open('cyber.json') as f:
        cyber = json.load(f)
    text_model = POSifiedText.from_json(cyber)
    text = text_model.make_short_sentence(80)
    text = ''.join([i if ord(i) < 128 else '' for i in text])
    return text


def glitch_image(pic):
    angle = random.choice([i for i in range(360)])
    intensity = random.choice([i for i in range(-2, 3)])
    pic.save('glitch.png', 'PNG')
    cmd = './prismsort.py glitch.png -a {} -i {}'.format(angle, intensity)
    print(cmd)
    call(cmd, shell=True)
    pic = Image.open('glitch_out0.png')
    return pic


def post_to_mastodon(pic_path, text):
    pic = mastodon.media_post(pic_path)
    mastodon.status_post(text, media_ids=[pic])


def main():
    pic = get_image().convert('L').convert('RGB')
    pic.filter(ImageFilter.SHARPEN)
    pastel, complement = get_colors()
    pic = add_pastel(pic, pastel)
    pic = select_section(pic)
    pic = glitch_image(pic)
    text = get_text()
    pic = write_text(pic, text, complement)
    pic.save('new.png', 'PNG')
    post_to_mastodon('new.png', text)


if __name__ == '__main__':
    main()
