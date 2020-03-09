import logging
from random import choice, choices
from string import ascii_lowercase
from bs4 import BeautifulSoup
import re


log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)
fh = logging.FileHandler('logs/app.log', encoding="utf-8")
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)
log.addHandler(fh)


def get_random_email():
    return ''.join(choices(ascii_lowercase, k=10)) + '@gmail.com'


def get_user_agent():
    with open('user_agents.txt', 'r') as file:
        user_agents = file.readlines()
        return choice(user_agents).replace('\n', '')


def get_random_string():
    with open('words.txt', 'r') as file:
        words = file.readlines()
        random_words = choices(words, k=2)
        return ' '.join(random_words).replace('\n', '')


def users():
    with open('accs.txt', 'r') as file:
        users_list = file.read().splitlines()

    for user in users_list:
        splitted = user.split(':')
        yield splitted[0], splitted[1].replace('\n', '')


def users_list():
    with open('accs.txt', 'r') as file:
        users_list = file.read().splitlines()
    l = []
    for user in users_list:
        splitted = user.split(':')
        l.append((splitted[0], splitted[1].replace('\n', '')))
    return l


def save_page(page, name):
    with open(f'html_accs/{name}.html', 'w', encoding='utf-8') as file:
        file.write(page)


def get_token(page_source, name):
    soup = BeautifulSoup(page_source, features="html.parser")
    scripts = soup.find_all('script')
    tokens = []
    for script in scripts:
        tokens.extend(re.findall(r'\[\"EA[A-Za-z0-9]{20,}', script.text))

    if tokens:
        return tokens[0]
    else:
        log.warning(f'Token not found')
        save_page(page_source, name)
        return None
