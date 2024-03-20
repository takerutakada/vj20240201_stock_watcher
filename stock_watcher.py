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

# 実行環境
# ACTION_ENV = "Local"
ACTION_ENV = "GitHub Actions"
# 設定ファイル保管場所
SETTING_DIR = "settings"
SETTING_DIR_PATH = f"{os.path.dirname(os.path.abspath(sys.argv[0]))}/{SETTING_DIR}"
# モード（TEST / PROD）
MODE = "TEST"
# 最大リトライ回数
MAX_RETRIES = 1

if ACTION_ENV == "Local":
    # config.ini の読み込み
    ini_file = configparser.ConfigParser()
    ini_file.read(f"{SETTING_DIR_PATH}/config.ini", "utf-8-sig")
    # service_account.json
    JSON = ini_file.get(MODE, "JSON")
    # スプレッドシート（「https://docs.google.com/spreadsheets/d/」以降の文字列）
    WORKBOOK_KEY = ini_file.get(MODE, "WORKBOOK_KEY")
elif ACTION_ENV == "GitHub Actions":
    JSON = "service_account.json"
    if MODE == "TEST":
        # スプレッドシート（「https://docs.google.com/spreadsheets/d/」以降の文字列）
        WORKBOOK_KEY = os.environ.get("WORKBOOK_KEY_TEST")
    elif MODE == "PROD":
        # スプレッドシート（「https://docs.google.com/spreadsheets/d/」以降の文字列）
        WORKBOOK_KEY = os.environ.get("WORKBOOK_KEY")


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


def get_asins_and_targets(auth):
    """
    Get asin2target from spreadsheet

    Parameters
    ----------
    auth : gspread.authorize()
        authorization for operating spreadsheet

    Returns
    ----------
    asins : list
        List of asin
    targets : list
        List of target
    """

    sheet = auth.open_by_key(WORKBOOK_KEY).worksheet("シート1")
    asins = sheet.col_values(1)[1:]
    targets = sheet.col_values(3)[1:]
    return asins, targets


def init_driver():
    """
    Initialize WebDriver
    """

    options = webdriver.ChromeOptions()
    prefs = {
        "profile.default_content_setting_values.notifications": 2,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
    }
    options.add_experimental_option("prefs", prefs)
    options.add_experimental_option("excludeSwitches", ["enable-logging"])
    # options.add_argument("--headless")
    options.add_argument("--disk-cache=false")
    driver = webdriver.Chrome(options=options)
    driver.implicitly_wait(10)
    driver.set_window_position(0, 0)  # ブラウザの位置を左上に固定
    driver.maximize_window()

    return driver


def get_status(driver, asin, target):
    """
    get status of items

    Parameters
    ----------
    driver : WebDriver
        Initialized WebDriver
    asin : str
        ASIN code
    target : str
        Seller name

    Returns
    ----------
    status : str or int
        status of items
    """

    retry_count = 0
    while True:
        try:
            print(f"ASIN: {asin} / target: {target}")
            # bot 対策回避のため、一度重要度の低いページを経由する
            tmp_url = "https://www.amazon.co.jp/gp/help/customer/display.html?nodeId=201909000"
            driver.get(tmp_url)
            upload_images_to_slack(driver, f"{asin}_{target}_1.png")
            url = f"https://www.amazon.co.jp/dp/{asin}"
            driver.get(url)
            upload_images_to_slack(driver, f"{asin}_{target}_1.png")
            # 住所を変更
            update_address_btn = driver.find_element(
                By.XPATH,
                "/html/body/div[2]/header/div/div[4]/div[1]/div/div/div[3]/span[2]/span/input",
            )
            update_address_btn.click()
            postcode_0_input = driver.find_element(By.XPATH, "//*[@id='GLUXZipUpdateInput_0']")
            postcode_0_input.send_keys("100")
            postcode_1_input = driver.find_element(By.XPATH, "//*[@id='GLUXZipUpdateInput_1']")
            postcode_1_input.send_keys("0001")
            time.sleep(5)
            save_btn = driver.find_element(By.XPATH, "//*[@id='GLUXZipUpdate']/span/input")
            save_btn.click()
            time.sleep(5)
            complete_btn = driver.find_element(
                By.XPATH, "/html/body/div[9]/div/div/div[2]/span/span/input"
            )
            complete_btn.click()
            time.sleep(5)
            # 販売元が表示されているか判定
            seller_name_elements = driver.find_elements(By.ID, "sellerProfileTriggerId")
            # 販売元が表示されている
            if seller_name_elements and seller_name_elements[0].text == target:
                # カートに追加
                add_to_cart_button = driver.find_element(
                    By.XPATH, "//*[@id='add-to-cart-button']"
                )
                add_to_cart_button.click()
                status = "get_by_stock_count"
            else:
                out_of_stocks = driver.find_elements(By.ID, "outOfStock")
                olp_link_widgets = driver.find_elements(
                    By.XPATH, "//*[@id='olpLinkWidget_feature_div']/div[2]"
                )
                buybox_see_all_buying_choices = driver.find_elements(
                    By.XPATH, "//*[@id='buybox-see-all-buying-choices']/span/a"
                )
                if out_of_stocks:
                    print("- 在庫切れです")
                    status = 0
                elif buybox_see_all_buying_choices or olp_link_widgets:
                    if buybox_see_all_buying_choices:
                        buybox_see_all_buying_choices[0].click()
                    elif olp_link_widgets:
                        olp_link_widgets[0].click()
                    seller_name_elements = driver.find_elements(
                        By.XPATH, "//*[@id='aod-offer-soldBy']/div/div/div[2]/a"
                    )
                    for seller_name_element in seller_name_elements:
                        if seller_name_element.text == target:
                            add_to_cart_url = seller_name_element.get_attribute("href")
                            driver.get(add_to_cart_url)
                            # 「カートに入れる」ボタンをクリック（ElementClickInterceptedException を突破できないので力技）
                            action = webdriver.ActionChains(driver)
                            keys_to_send = [
                                Keys.TAB,
                                Keys.ENTER,
                                Keys.TAB,
                                Keys.TAB,
                                Keys.TAB,
                                Keys.TAB,
                                Keys.TAB,
                                Keys.TAB,
                                Keys.ENTER,
                            ]
                            for key in keys_to_send:
                                action.send_keys(key).perform()
                            time.sleep(10)
                            status = "get_by_stock_count"
                            break
                    else:
                        print(f"- {target} は出品していません")
                        status = 0
                else:
                    print("情報を取得できません")
                    raise Exception
            # 先頭タブを除きすべてのタブを閉じる
            for handle in driver.window_handles[1:]:
                driver.switch_to.window(handle)
                driver.close()
            driver.switch_to.window(driver.window_handles[0])
            return status
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
                status = "error"
                return status


def get_stock_count(driver, asin, target):
    """
    Get stock count from amazon

    Parameters
    ----------
    driver : WebDriver
        Initialized WebDriver
    asin : str
        ASIN code
    target : str
        Seller name

    Returns
    ----------
    stock_count : str or int
        stock count
    """

    retry_count = 0
    while True:
        try:
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
            return stock_count
        except Exception as e:
            if retry_count < MAX_RETRIES:
                retry_count += 1
                print(
                    f"- get_stock_count: 失敗しました。リトライします。（リトライ回数：{retry_count}回目）"
                )
                driver.quit()
                driver = init_driver()
                get_status(driver, asin, target)
            else:
                print(
                    "- get_stock_count: リトライ上限に達しました。次の商品に移ります。"
                )
                print(f"エラー内容: {e}")
                stock_count = "error"
                return stock_count


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

    sheet = auth.open_by_key(WORKBOOK_KEY).worksheet("シート1")
    # 現在の日付を取得
    current_date = datetime.datetime.now().strftime("%Y/%m/%d")
    # 4列目に空列を挿入
    sheet.insert_cols([[]], col=4)
    # 4列目に各商品に対応する在庫数を入力
    quantities = [[current_date]]
    for stock_count in stock_counts:
        quantities.append([stock_count])
    sheet.append_rows(quantities, table_range="D1", value_input_option="USER_ENTERED")

def upload_images_to_slack(driver, file_name):
    import requests
    from glob import glob
    SLACK_TOKEN = ini_file.get(MODE, "SLACK_TOKEN")
    SLACK_CHANNEL = ini_file.get(MODE, "SLACK_CHANNEL")
    # get width and height of the page
    w = driver.execute_script("return document.body.scrollWidth;")
    h = driver.execute_script("return document.body.scrollHeight;")
    # set window size
    driver.set_window_size(w, h)
    driver.save_screenshot(file_name)
    file_path = glob(file_name)[0]

    files = {"file": open(file_path, "rb")}
    param = {
        "token": SLACK_TOKEN,
        "channels": SLACK_CHANNEL,
        "filename": "filename",
        "initial_comment": "initial comment",
        "title": "title",
    }
    requests.post(url="https://slack.com/api/files.upload", data=param, files=files)


if __name__ == "__main__":
    start_time = datetime.datetime.now()
    print(f"処理を開始します - {start_time.strftime('%H:%M')}")
    # WebDriver の初期化
    auth = google_auth()
    # ASIN / 出品者を取得
    print("ASIN / 出品者を取得します")
    asins, targets = get_asins_and_targets(auth)
    # Amazon から在庫数を取得
    print("Amazon から在庫数を取得します")
    stock_counts = []
    for asin, target in zip(asins, targets):
        driver = init_driver()
        status = get_status(driver, asin, target)
        if status == "get_by_stock_count":
            stock_counts.append(get_stock_count(driver, asin, target))
        else:
            stock_counts.append(status)
        driver.quit()
    # スプレッドシートへ在庫数を入力
    print("スプレッドシートへ在庫数を入力します")
    post_to_spreadsheet(auth, stock_counts)
    end_time = datetime.datetime.now()
    print(f"処理が完了しました - {end_time.strftime('%H:%M')}")
