import logging
import os
import re
import sys
import time

import pandas as pd
import requests
import undetected_chromedriver as uc
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from selenium.common.exceptions import (NoSuchElementException,
                                        JavascriptException)
from selenium.webdriver.common.by import By
from twocaptcha import TwoCaptcha
from webdriver_manager.chrome import ChromeDriverManager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s, %(levelname)s, %(name)s, %(message)s',
    handlers=[logging.FileHandler('logs.log', mode='w', encoding='utf-8'),
              logging.StreamHandler()]
)

API_KEY_CAPTCHA: str = 'ваш ключ'
CAT_NAME: str = 'Металлопрокат'
STATIC_URL: str = 'https://multicity.23met.ru/price/'


class GetPrice23met:
    """Сбор данных с сайта 23met.ru"""

    @staticmethod
    def get_all_services() -> dict:
        """Получить slug и название всех видов товара."""
        data_links: dict = {}
        headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,'
                      'image/avif,image/webp,image/apng,*/*;q=0.8,'
                      'application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-GB;q=0.8,en;q=0.7,en-US;q=0.6',
            'Connection': 'keep-alive',
            'User-Agent': UserAgent(
                browsers=['opera', 'firefox', 'chrome']).random,

        }
        response = requests.get(STATIC_URL,
                                headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        for link_category in soup.find('ul', {'class': 'tabs'}).find_all('li'):
            if link_category.find('a'):
                data_links[link_category.find('a').text] = \
                    link_category.find('a')['href'].replace('/price/', '')
        return data_links

    def get_sub_services(self) -> dict:
        """Получить slug и название всех подкатегорий."""
        data_sub_categories: dict = {}
        for name_category, slug_category in self.get_all_services().items():
            logging.info(f'{name_category} -> {slug_category}')
            headers = {
                'Accept': '*/*',
                'Connection': 'keep-alive',
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'User-Agent': UserAgent(
                    browsers=['opera', 'firefox', 'chrome']).random,

            }
            data = {
                'ajax': 'sizes',
                'n': slug_category,
            }
            response = requests.post(STATIC_URL,
                                     data=data,
                                     headers=headers)
            soup = BeautifulSoup(response.text, 'html.parser')
            sub_cat: dict = {}
            for link_sub_category in soup.find_all('a'):
                sub_cat[link_sub_category.text] = link_sub_category['href']
            data_sub_categories[name_category] = sub_cat

        return data_sub_categories

    def google_captcha(self, site_url: str, driver) -> None:
        DELAY_BUTTON: int = 3
        """Проверка наличия Капчи на странице, запускает разгадывание."""
        try:
            find_captcha_key = str(driver.find_element(
                By.XPATH,
                "//script[contains(text(),'sitekey')]").get_attribute(
                'innerHTML')
            )
            try:
                key_captcha = re.search(
                    r'sitekey.+', find_captcha_key).group().replace(
                    "sitekey' : '", "").replace("'", "")
                sys.path.append(os.path.dirname(
                    os.path.dirname(os.path.realpath(__file__))))
                try:
                    result = TwoCaptcha(API_KEY_CAPTCHA).recaptcha(
                        sitekey=f'{key_captcha}',
                        url=f'{site_url}')
                except Exception as error:
                    logging.critical(
                        f'Проблема  с получением  данных от API -  {error}'
                    )
                else:
                    done_key = str(result['code'])
                    driver.execute_script("document.getElementById("
                                          "'g-recaptcha-response')."
                                          "style.display='block';")
                    time.sleep(DELAY_BUTTON)
                    driver.find_element(By.XPATH, '//textarea[contains(@id,'
                                                  '"g-recaptcha-response")]'
                                        ).send_keys(done_key)
                    time.sleep(DELAY_BUTTON)
                    driver.find_element(By.XPATH,
                                        '//input[contains(@value,'
                                        '"Отправить")]').click()
                    time.sleep(DELAY_BUTTON)
            except NoSuchElementException:
                logging.critical(f'Ошибка обработки  капчи. '
                                 f'Страница - {site_url}')
        except (NoSuchElementException, JavascriptException):
            logging.info(f'Капча отсутствует, страница  -  {site_url}')

    def get_page_data(self, data_links: dict) -> dict:
        """Поиск данных на отдельной странице."""
        data_result: dict = {}
        chrome_manager = ChromeDriverManager()
        chrome_driver_path = chrome_manager.install()
        version_main = int(
            chrome_manager.driver.get_browser_version_from_os().split('.')[0])
        driver = uc.Chrome(driver_executable_path=chrome_driver_path,
                           version_main=version_main, headless=True)
        try:
            for name_cat, sub_cat_data in data_links.items():
                _sub_cat: dict = {}
                for sub_cat_name, slug_sub_cat in sub_cat_data.items():
                    logging.info(f'Открываю ссылку - '
                                 f'https://multicity.23met.ru{slug_sub_cat}')
                    driver.get(f'https://multicity.23met.ru{slug_sub_cat}')
                    if not BeautifulSoup(
                            driver.page_source, 'html.parser'
                    ).find('script', text=re.compile('sitekey')):

                        driver.add_cookie(
                            {"name": "mc_e_cn",
                             "value": "msk%2Cspb%2Carhangelsk%2Castrahan%2Cbarnayl"
                                      "%2Cbelgorod%2Cbratsk%2Cbryansk%2Cvnovgorod%"
                                      "2Cvladivostok%2Cvladikavkaz%2Cvladimir%"
                                      "2Cvolgograd%2Cvologda%2Cvoronezh%2Cekb%"
                                      "2Civanovo%2Cizhevsk%2Cyoshkarola%2Cirkytsk%"
                                      "2Ckazan%2Ckalyga%2Ckemerovo%2Ckirov%"
                                      "2Ckrasnodar%2Ckrasnoyarsk%2Ckyrsk%"
                                      "2Clipetsk%2Cmagnitogorsk%2Cmahachkala%"
                                      "2Cminvody%2Cnabchelny%2Cnalchik%2Cnn%"
                                      "2Ctagil%2Cnovokyzneck%2Cnsk%"
                                      "2Cnovocherkassk%2Comsk%2Corel%2Corenbyrg%"
                                      "2Cpenza%2Cperm%2Cpyatigorsk%2Crostov%"
                                      "2Cryazan%2Csamara%2Csaransk%2Csaratov%"
                                      "2Csevastopol%2Csimferopol%2Csmolensk%"
                                      "2Csochi%2Cstavropol%2Csyrgyt%2Coskol%"
                                      "2Csyzran%2Ctaganrog%2Ctambov%2Ctver%"
                                      "2Ctolyatti%2Ctula%2Ctumen%2Cylianovsk%"
                                      "2Cylanyde%2Cufa%2Chabarovsk%2Ccheboksary%"
                                      "2Cchelyabinsk%2Ccherepovec%2Cchita%"
                                      "2Cusahalinsk%2Cyakytsk%2Cyaroslavl"}
                        )
                        driver.refresh()
                        soup = BeautifulSoup(driver.page_source, 'html.parser')
                        _name, _steel_grade, _length, _price, _provider = [], [], [], [], []
                        for table_tr in soup.find('tbody').find_all('tr'):
                            min_length_table = 7
                            if len(table_tr.find_all('td')) >= min_length_table:
                                _name.append(table_tr.find_all('td')[0].text)
                                _steel_grade.append(
                                    table_tr.find_all('td')[1].text)
                                _length.append(table_tr.find_all('td')[2].text)
                                _price.append(table_tr.find_all('td')[3].text)
                                _provider.append(table_tr.find_all('td')[5].text)
                        _sub_cat[sub_cat_name] = [{'names': _name},
                                                  {'steel_grade': _steel_grade},
                                                  {'lengths': _length},
                                                  {'prices': _price},
                                                  {'providers': _provider}]
                    else:
                        self.google_captcha(
                            f'https://multicity.23met.ru{slug_sub_cat}', driver
                        )
                data_result[name_cat] = _sub_cat
        finally:
            driver.close()
            logging.info('Сбор данных  закончен.')
        return data_result

    def data_to_xlsx(self, data_xlsx: dict):
        """Сохранение данных в XLSX файл."""

        main_sections: list = []
        subsections: list = []
        sizes: list = []
        names: list = []
        steel_grades: list = []
        longs: list = []
        prices: list = []
        providers: list = []

        for general_cat, sub_cat in data_xlsx.items():
            for sub_cat_name, data_sub_cat in sub_cat.items():
                for name, steel_grade, length, price, provider in zip(
                        data_sub_cat[0].get('names'),
                        data_sub_cat[1].get('steel_grade'),
                        data_sub_cat[2].get('lengths'),
                        data_sub_cat[3].get('prices'),
                        data_sub_cat[4].get('providers'),
                ):
                    main_sections.append(CAT_NAME)
                    subsections.append(general_cat)
                    sizes.append(sub_cat_name)
                    names.append(name)
                    steel_grades.append(steel_grade)
                    longs.append(length)
                    prices.append(price)
                    providers.append(provider)

        data_frame_result = pd.DataFrame({
            'Основной раздел': main_sections,
            'Подраздел': subsections,
            'Размер': sizes,
            'Наименование': names,
            'Марка стали': steel_grades,
            'Длина': longs,
            'Цена': prices,
            'Поставщик': providers,

        })

        data_frame_result.to_excel('23met_result.xlsx', index=False)
        logging.info('Данные успешно записаны.')


if __name__ == "__main__":
    logging.info('Запускаю парсинг данных')
    parsing = GetPrice23met()
    try:
        links: dict = parsing.get_sub_services()
        logging.info(f'Собрал {len(links)} категории.')
        logging.info('Запускаю  парсинг данных')
        results_parsing: dict = parsing.get_page_data(links)
        logging.info('Парсинг закончен, сохраняю')
        parsing.data_to_xlsx(results_parsing)
        logging.info('Закрываю программу.')
    except AttributeError:
        logging.critical('Ошибка получения данных. '
                         'Возможно, сайт блокирует ваше соединение.')
