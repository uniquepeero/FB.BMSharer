from config import api_url, proxies
import utils
import requests
import logging
from bs4 import BeautifulSoup
import re
from seleniumwire import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import *
from random import random
from time import sleep

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)
fh = logging.FileHandler('logs/app.log', encoding="utf-8")
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)
log.addHandler(fh)

FB_URL = 'https://www.facebook.com/'


class Sharer:
    def __init__(self, email, password):
        self._email = email
        self._password = password

        self.links = list()
        self._token = None
        self._fp_id = None

        self._session = requests.Session()
        self._session.proxies.update(proxies)
        self._user_agent = utils.get_user_agent()
        headers = {
            'user-agent': self._user_agent
        }
        self._session.headers.update(headers)
        self._driver = self._firefox_config()
        self._driver.implicitly_wait(30)

    def _firefox_config(self):
        options = {
            # 'proxy': proxies
        }
        fp = webdriver.FirefoxProfile()
        fp.set_preference("general.useragent.override", self._user_agent)  # choice useragent
        fp.set_preference("media.peerconnection.enabled", False)  # disable webrtc
        fp.set_preference("plugin.state.flash", 0)  # disable flash
        fp.set_preference("general.useragent.locale", "en")
        fp.update_preferences()  # save settings

        return webdriver.Firefox(firefox_profile=fp, seleniumwire_options=options, executable_path='geckodriver.exe')

    def _create_fp(self):
        self._driver.get('https://ipinfo.io/json')
        # Login page
        self._driver.get(FB_URL)
        login = self._driver.find_element_by_xpath('//*[@id="email"]')
        password = self._driver.find_element_by_xpath('//*[@id="pass"]')
        for letter in self._email:
            login.send_keys(letter)
            sleep(random())
        for letter in self._password:
            password.send_keys(letter)
            sleep(random())
        # Login btn
        # self._driver.find_element_by_xpath('//*[@id="u_0_4"]').click()
        self._driver.find_element_by_tag_name('body').send_keys(Keys.ENTER)
        try:
            create_btn = self._driver.find_element_by_xpath('//*[@id="creation_hub_entrypoint"]')
        except NoSuchElementException:
            if 'checkpoint' in self._driver.current_url:
                log.info('Account on checkpoint')
            self._driver.close()
            return

        if create_btn:
            self._driver.get("https://www.facebook.com/pages/create/")
        else:
            log.warning('Cannot find create page button')
            utils.save_page(self._driver.page_source, f'{self._email}_pre_create')
            self._driver.close()
            return None

        action = ActionChains(self._driver)
        action.move_by_offset(55, 105)
        action.click()
        action.perform()

        # Get started btn
        btn = '/html/body/div[1]/div[3]/div[1]/div/div[2]/div/div[2]/table/tbody/tr/td[1]/div/div[1]/div[2]/button/div/div'
        self._driver.find_element_by_xpath(btn).click()

        page_name = self._driver.find_element_by_xpath('//*[@id="BUSINESS_SUPERCATEGORYPageNameInput"]')
        for letter in utils.get_random_string():
            page_name.send_keys(letter)
            sleep(random())
        category = self._driver.find_element_by_xpath('//*[@id="js_6"]/input')
        for letter in 'home decor':
            category.send_keys(letter)
            sleep(random())
        category.send_keys(Keys.ENTER)

        # Continue btn
        self._driver.find_element_by_xpath('//*[@id="content"]/div/div[2]/div/div[2]/table/tbody/tr/td[1]/div/div[2]/div[5]/button/div/div').click()
        # Picture skip btn
        self._driver.find_element_by_xpath('//*[@id="content"]/div/div[2]/div[2]/a').click()
        # Cover pic skip btn
        self._driver.find_element_by_xpath('//*[@id="content"]/div/div[2]/div[2]/a').click()

        self._fp_id = re.findall(r'\d+', self._driver.current_url)[0]
        log.info(f'FP created: {self._fp_id}')

        self._driver.get(f'{FB_URL}adsmanager/manage/campaigns')
        self._token = utils.get_token(self._driver.page_source, f'{self._email}_notoken')

        self._driver.close()

    def _check_user(self):
        log.info(f'Checking {self._email}:{self._password}')
        valid = False
        try:
            main_page = self._session.get(FB_URL, allow_redirects=False)
            if main_page.status_code == 200:

                #DEBUG
                utils.save_page(main_page.text, f'{self._email}_1')

                soup = BeautifulSoup(main_page.text, features="html.parser")
                try:
                    action_url = soup.find('form', id='login_form')['action']
                    inputs = soup.find('form', id='login_form').findAll('input', {'type': ['hidden', 'submit']})
                except TypeError:
                    log.error('Something went wrong')
                    return
                post_data = {input_tag.get('name'): input_tag.get('value') for input_tag in inputs}
                post_data['email'] = self._email
                post_data['pass'] = self._password

                scripts = soup.findAll('script')
                scripts_string = '/n/'.join([script.text for script in scripts])
                js_datr_search = re.search(r'\["_js_datr","([^"]*)"', scripts_string, re.DOTALL)
                datr_search = re.search(r'\["datr","([^"]*)"', scripts_string, re.DOTALL)
                if js_datr_search:
                    datr = js_datr_search.group(1)
                    cookies = {'_js_datr': datr}
                elif datr_search:
                    datr = datr_search.group(1)
                    cookies = {'datr': datr}
                else:
                    log.warning('Cookies not found')
                    cookies = self._session.cookies

                # if cookies is not None:
                try:
                    login_page = self._session.post(action_url, data=post_data, cookies=cookies)

                    #DEBUG
                    utils.save_page(login_page.text, f'{self._email}_2')

                    if re.search('Home', login_page.text):
                        log.info(f'Valid: {self._email}:{self._password}')
                        log.info(login_page.cookies.get_dict())
                        valid = self._session.cookies
                    elif re.search('checkpoint', login_page.text):
                        log.debug('Checkpoint')
                    elif re.search('Your Account Has Been Disabled', login_page.text):
                        log.debug('Account disabled')
                    elif re.search('Your account is temporarily locked', login_page.text):
                        log.debug('Account locked')
                    elif re.search('Sorry, something went wrong', login_page.text):
                        log.debug('Facebook error')
                    elif re.search('Sorry, your account is temporarily unavailable', login_page.text):
                        log.debug('Logged in. but this account is temporarily unavailable')
                    elif re.search(r'Incorrect email\/password combination', login_page.text):
                        log.debug('Incorrect email/password combination')
                    elif re.search('since this location is very unusual for you', login_page.text):
                        log.debug('Logged in. but it need verification for your location through email')
                    elif re.search('Sorry, your account is temporarily unavailable', login_page.text):
                        log.debug('Logged in. but this account is temporarily unavailable')
                    else:
                        log.debug('Unknown error. Check it manually')
                except requests.exceptions.RequestException as e:
                    log.error(f'{action_url} - {e}')

            else:
                log.error(f'{FB_URL} - {main_page.status_code} - {main_page.text}')
        except requests.exceptions.RequestException as e:
            log.error(f'{FB_URL} - {e}')

        if valid:
            try:
                token_page = self._session.get(f'{FB_URL}adsmanager/manage/campaigns')
                if token_page.status_code == 200:

                    #DEBUG
                    utils.save_page(token_page.text, f'{self._email}_3')

                    soup = BeautifulSoup(token_page.text, features="html.parser")
                    scripts = soup.find_all('script')
                    tokens = []
                    for script in scripts:
                        tokens.extend(re.findall(r'\[\"EA[A-Za-z0-9]{20,}', script.text))

                    if tokens:
                        log.info(f'Tokens found: {tokens}')
                        self._token = tokens[-1][2:]
                    else:
                        log.error('Token not found')

            except requests.exceptions.RequestException as e:
                log.warning(f'Token page: {e}')

    def create_share(self):
        log.info(f'Checking {self._email}:{self._password}')
        self._create_fp()

        if self._token is not None:
            for i in range(20):
                # fp_name = utils.get_random_string()
                #
                # payload = {
                #     'access_token': self._token,
                #     'name': fp_name,
                #     'category': "2606"
                # }
                # try:
                #     response = self._session.post(f'{api_url}me/accounts', data=payload)
                #     if response.status_code == 200:
                #         response = response.json()
                #         log.debug(response)
                #
                #         if response['error']:
                #             log.error(f'FP ID not found: {response}')
                #             break
                #
                #         fp_id = response['id']
                #     else:
                #         log.error(f'Create fan page error code: {response.status_code} - {response.text}')
                #         break
                # except requests.exceptions.RequestException as e:
                #     log.warning(f'Create fan page request: {e}')

                if self._fp_id is not None:
                    bm_name = utils.get_random_string()
                    bm_id = None

                    payload = {
                        'access_token': self._token,
                        'name': bm_name,
                        'vertical': "ADVERTISING",
                        'primary_page': self._fp_id,
                        'timezone_id': 116
                    }
                    try:
                        response = self._session.post(f'{api_url}me/businesses', data=payload)
                        if response.status_code == 200:
                            response = response.json()
                            log.debug(response)
                            if 'id' in response.keys():
                                bm_id = response['id']
                            else:
                                log.error(f'FP ID not found: {response}')
                        else:
                            log.error(f'Create BM error code: {response.status_code} - {response.text}')
                            break
                    except requests.exceptions.RequestException as e:
                        log.warning(f'Create BM request: {e}')

                    if bm_id is not None:
                        email = utils.get_random_email()

                        payload = {
                            'access_token': self._token,
                            'email': email,
                            'role': 'ADMIN'
                        }
                        invited = False
                        try:
                            response = self._session.post(f'{api_url}{bm_id}/business_users', data=payload)
                            if response.status_code == 200:
                                response = response.json()
                                log.debug(response)
                                # if response[error] is None:
                                invited = True
                            else:
                                log.error(f'Invite error: {response.status_code} - {response.text}')
                                break
                        except requests.exceptions.RequestException as e:
                            log.warning(f'Invite request: {e}')

                        if invited:
                            params = {
                                'access_token': self._token,
                                'fields': 'id,role,email,invite_link,status'
                            }
                            try:
                                response = self._session.get(f'{bm_id}/pending_users', params=params)
                                if response.status_code == 200:
                                    response = response.json()
                                    log.debug(response)
                                    link = response['data'][0]['invite_link']
                                    self.links.append(link)
                                    log.info(f'New link appended: {link}')
                                else:
                                    log.error(f'Get invite link: {response.status_code} - {response.text}')
                                    break
                            except requests.exceptions.RequestException as e:
                                log.warning(f'Get invite link: {e}')

            log.info(self.links)
