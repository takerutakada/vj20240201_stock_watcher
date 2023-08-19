
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from bs4 import BeautifulSoup

import pyautogui
import time

# import configparser

# ini_file = configparser.ConfigParser()
# ini_file.read('./config.ini', 'UTF-8')

# 時間計測開始
time_sta = time.perf_counter()

# モード（Google画像検索か拡張機能を利用するか選択）
# MODE = ini_file.get('Mode', 'MODE')
MODE = 'GWS'
EXTENSION_PATH = 'Aliexpress_Search_by_image.crx'

# WebDriverの初期化
options = webdriver.ChromeOptions()
options.add_extension(EXTENSION_PATH)
driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=options)


driver.set_window_position(0,0) # ブラウザの位置を左上に固定
driver.set_window_size(600,740) # ブラウザのウィンドウサイズを固定

# ヤフーショッピングのURLを開く
url = "https://store.shopping.yahoo.co.jp/jajamaruhonpo/search.html?X=4&n=100#CentSrchFilter1"
driver.get(url)

# try:
# 商品情報を含む要素を取得
print('商品情報を含む要素を取得')
product_elements = driver.find_elements(By.CSS_SELECTOR, "img.elImageContent")


    for product_element in product_elements[:10]:
        # 画像を右クリックし、Google画像検索を実行
        print('画像を右クリックし、Google画像検索を実行')
        product_image_url = product_element.get_attribute("src")
        print(product_image_url)
        driver.execute_script(f"window.open('https://www.google.com/searchbyimage?image_url');")

        # 新しいタブに切り替え
        print('新しいタブに切り替え')
        driver.switch_to.window(driver.window_handles[-1])

        # 画像 URL を入力
        lens_btn = driver.find_element(By.CSS_SELECTOR, "div.nDcEnd")
        lens_btn.send_keys(Keys.ENTER)
        input_URL = driver.find_element(By.CSS_SELECTOR, "input.cB9M7")
        input_URL.send_keys(product_image_url)
        search_btn = driver.find_element(By.CSS_SELECTOR, "div.Qwbd3")
        search_btn.send_keys(Keys.ENTER)

        # Google画像検索の結果ページを解析
        print('Google画像検索の結果ページを解析')
        search_results = driver.find_elements(By.CLASS_NAME, "G19kAf.ENn9pd")

        # "aliexpress"を含むURLを出力
        print('"aliexpress"を含むURLを出力')
        time.sleep(10)
        for search_result in search_results:
            search_result_url = search_result.find_element(By.TAG_NAME, "a").get_attribute("href")
            # search_result_url = search_result.get_attribute("data-action-url")
            if "aliexpress" in search_result_url:
                print(search_result_url)

        # タブを閉じて元のページに戻る
        print('タブを閉じて元のページに戻る')
        driver.close()
        driver.switch_to.window(driver.window_handles[0])



# 時間計測終了
time_end = time.perf_counter()
# 経過時間（秒）
tim = time_end- time_sta

print(tim)
