import configparser
import time
import datetime
import gspread
import os
import sys
from oauth2client.service_account import ServiceAccountCredentials
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

# 設定ファイル保管場所
SETTING_DIR = "settings"
SETTING_DIR_PATH = f"{os.path.dirname(os.path.abspath(sys.argv[0]))}/{SETTING_DIR}"
# モード（TEST / PROD）
MODE = "TEST"
# MODE = "PROD"
# 最大リトライ回数
MAX_RETRIES = 1

if "GITHUB_ACTIONS" in os.environ:
    JSON = "service_account.json"
    if MODE == "TEST":
        # スプレッドシート（「https://docs.google.com/spreadsheets/d/」以降の文字列）
        WORKBOOK_KEY = os.environ.get("WORKBOOK_KEY_TEST")
    elif MODE == "PROD":
        # スプレッドシート（「https://docs.google.com/spreadsheets/d/」以降の文字列）
        WORKBOOK_KEY = os.environ.get("WORKBOOK_KEY")
else:
    # config.ini の読み込み
    ini_file = configparser.ConfigParser()
    ini_file.read(f"{SETTING_DIR_PATH}/config.ini", "utf-8-sig")
    # service_account.json
    JSON = ini_file.get(MODE, "JSON")
    # スプレッドシート（「https://docs.google.com/spreadsheets/d/」以降の文字列）
    WORKBOOK_KEY = ini_file.get(MODE, "WORKBOOK_KEY")


def google_auth():
    """
    Authorize google account
    """

    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive",
    ]
    credentials = ServiceAccountCredentials.from_json_keyfile_name(
        f"{SETTING_DIR_PATH}/{JSON}", scope
    )

    auth = gspread.authorize(credentials)
    return auth


def get_asins_and_urls(auth):
    """
    在庫数を取得する ASIN・URL のリストを取得（URL で取得対象のセラーを絞っている）

    Parameters
    ----------
    auth : gspread.authorize()

    Returns
    ----------
    asins : list
        取得した ASIN のリスト
    urls : list
        取得した URL のリスト
    """

    sheet = auth.open_by_key(WORKBOOK_KEY).worksheet("Monitor")
    asins = sheet.col_values(1)[1:]
    urls = sheet.col_values(3)[1:]
    return asins, urls


def init_driver():
    options = webdriver.ChromeOptions()
    prefs = {
        "profile.default_content_setting_values.notifications": 2,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
    }
    options.add_experimental_option("prefs", prefs)
    options.add_experimental_option("excludeSwitches", ["enable-logging"])
    options.add_argument("--headless")
    options.add_argument("--disk-cache=false")
    driver = webdriver.Chrome(options=options)
    driver.implicitly_wait(10)
    driver.set_window_position(0, 0)  # ブラウザの位置を左上に固定
    driver.maximize_window()

    return driver


def get_stock_count(driver, asin, url):
    """
    在庫数を取得する

    Parameters
    ----------
    driver : WebDriver
        chrome ドライバ
    asin : str
        ASIN コード
    url : str
        アクセスする URL

    Returns
    ----------
    stock_count : int or str
        在庫数
    """

    retry_count = 0
    while True:
        try:
            print(f"ASIN: {asin}")
            # bot 対策回避のため、一度重要度の低いページを経由する
            tmp_url = "https://www.amazon.co.jp/gp/help/customer/display.html?nodeId=201909000"
            driver.get(tmp_url)
            driver.get(url)
            # 住所を変更
            update_address_btn = driver.find_element(
                By.XPATH,
                "//*[@id='glow-ingress-line2']",
            )
            update_address_btn.click()
            postcode_0_input = driver.find_element(
                By.XPATH, "//*[@id='GLUXZipUpdateInput_0']"
            )
            postcode_0_input.send_keys("100")
            postcode_1_input = driver.find_element(
                By.XPATH, "//*[@id='GLUXZipUpdateInput_1']"
            )
            postcode_1_input.send_keys("0001")
            time.sleep(5)
            save_btn = driver.find_element(
                By.XPATH, "//*[@id='GLUXZipUpdate']/span/input"
            )
            save_btn.click()
            if "GITHUB_ACTIONS" in os.environ:
                action = webdriver.ActionChains(driver)
                action.send_keys(Keys.ENTER).perform()
                tmp_url = "https://www.amazon.co.jp/gp/help/customer/display.html?nodeId=201909000"
                driver.get(tmp_url)
                driver.get(url)
            time.sleep(5)
            # カートに入れる
            add_to_cart_buttons = driver.find_elements(
                By.XPATH, "//*[@id='add-to-cart-button']"
            )
            if not add_to_cart_buttons:
                add_to_cart_buttons = driver.find_elements(
                    By.XPATH, "//*[@id='add-to-cart-button-ubb']"
                )
                if not add_to_cart_buttons:
                    print("- 在庫切れです")
                    driver.quit()
                    return 0
            add_to_cart_buttons[0].click()
            # カートに移動
            driver.get("https://www.amazon.co.jp/gp/cart/view.html")
            # 数量選択ページに遷移
            quantity_button = driver.find_element(
                By.CSS_SELECTOR, "#a-autoid-0-announce"
            )
            quantity_button.click()
            # 10+を選択
            while "product" in driver.current_url:
                print("キャンペーン広告をクリックしました。ブラウザバックします")
                driver.back()
            ten_plus_option = driver.find_element(
                By.XPATH, "//a[contains(text(),'10+')]"
            )
            ten_plus_option.click()
            # 数量入力
            quantity_input = driver.find_element(By.NAME, "quantityBox")
            quantity_input.send_keys(Keys.CONTROL + "a")
            quantity_input.send_keys("999")
            quantity_input.send_keys(Keys.RETURN)
            time.sleep(10)
            # 購入可能数量を取得して出力
            driver.get("https://www.amazon.co.jp/gp/cart/view.html")
            quantity_input = driver.find_element(By.NAME, "quantityBox")
            available_quantity = quantity_input.get_attribute("value")
            print(f"- 在庫数: {available_quantity}")
            stock_count = available_quantity
            driver.quit()
            return stock_count
        except Exception as e:
            driver.quit()
            driver = init_driver()
            if retry_count < MAX_RETRIES:
                retry_count += 1
                print(
                    f"- add_to_cart: 失敗しました。リトライします。（リトライ回数：{retry_count}回目）"
                )
            else:
                print("- add_to_cart: リトライ上限に達しました。次の商品に移ります。")
                print(f"エラー内容: {e}")
                return "error"


def post_to_spreadsheet(auth, stock_counts):
    """
    Posting data to spreadsheet

    Parameters
    ----------
    auth : gspread.authorize()
        authorization for operating spreadsheet
    stock_counts : List
        List of stock_count
    """

    sheet = auth.open_by_key(WORKBOOK_KEY).worksheet("Monitor")
    # 現在の日付を取得
    current_date = datetime.datetime.now().strftime("%Y/%m/%d")
    # 5列目に空列を挿入
    sheet.insert_cols([[]], col=5)
    # 5列目に各商品に対応する在庫数を入力
    quantities = [[current_date]]
    for stock_count in stock_counts:
        quantities.append([stock_count])
    sheet.append_rows(quantities, table_range="E1", value_input_option="USER_ENTERED")


if __name__ == "__main__":
    start_time = datetime.datetime.now()
    print(f"処理を開始します - {start_time.strftime('%H:%M')}")
    # WebDriver の初期化
    auth = google_auth()
    # スプレッドシートから ASIN / URLを取得
    print("スプレッドシートから ASIN / URL を取得します")
    asins, urls = get_asins_and_urls(auth)
    # Amazon から在庫数を取得
    print("Amazon から在庫数を取得します")
    stock_counts = []
    for asin, url in zip(asins, urls):
        driver = init_driver()
        stock_counts.append(get_stock_count(driver, asin, url))
    # スプレッドシートへ在庫数を入力
    print("スプレッドシートへ在庫数を入力します")
    post_to_spreadsheet(auth, stock_counts)
    end_time = datetime.datetime.now()
    print(f"処理が完了しました - {end_time.strftime('%H:%M')}")
