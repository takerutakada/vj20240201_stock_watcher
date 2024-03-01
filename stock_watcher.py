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
    options.add_argument("--headless")
    driver = webdriver.Chrome(options=options)
    driver.implicitly_wait(10)
    # driver.set_window_position(0, 0)  # ブラウザの位置を左上に固定
    # driver.maximize_window()

    return driver


def add_to_cart(driver, asin, target):
    """
    add item to cart

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

    def track_target():

        out_of_stock = driver.find_elements(By.ID, "outOfStock")
        olp_link_widget = driver.find_elements(
            By.XPATH, "//*[@id='olpLinkWidget_feature_div']/div[2]"
        )
        buybox_see_all_buying_choices = driver.find_elements(By.XPATH, "//*[@id='buybox-see-all-buying-choices']/span/a")
        # 商品が在庫切れ
        if len(out_of_stock):
            print("- 在庫切れです")
            stock_count = 0
        elif len(buybox_see_all_buying_choices):
            buybox_see_all_buying_choices[0].click()
            seller_name_elements = driver.find_elements(
                By.XPATH, "//*[@id='aod-offer-soldBy']/div/div/div[2]/a"
            )
            print("パターン1")
            for seller_name_element in seller_name_elements:
                print(seller_name_element.text)
            for seller_name_element in seller_name_elements:
                # 出品者の中に target が存在する
                if seller_name_element.text == target:
                    add_to_cart_url = seller_name_element.get_attribute("href")
                    driver.get(add_to_cart_url)
                    # 「カートに入れる」ボタンをクリック（ElementClickInterceptedException を突破できないので力技）
                    action = webdriver.ActionChains(driver)
                    keys_to_send = [Keys.TAB, Keys.ENTER, Keys.TAB, Keys.TAB, Keys.TAB, Keys.TAB, Keys.TAB, Keys.TAB, Keys.ENTER]
                    for key in keys_to_send:
                        action.send_keys(key).perform()
                    time.sleep(10)
                    stock_count = "get_by_stock_count"
                    break
            else:
                print(f"- {target} は出品していません")
                stock_count = 0
        # 複数の出品者が存在する
        elif len(olp_link_widget):
            olp_link_widget[0].click()
            seller_name_elements = driver.find_elements(
                By.XPATH, "//*[@id='aod-offer-soldBy']/div/div/div[2]/a"
            )
            print("パターン2")
            for seller_name_element in seller_name_elements:
                print(seller_name_element.text)
            for seller_name_element in seller_name_elements:
                # 出品者の中に target が存在する
                if seller_name_element.text == target:
                    add_to_cart_url = seller_name_element.get_attribute("href")
                    driver.get(add_to_cart_url)
                    # 「カートに入れる」ボタンをクリック（ElementClickInterceptedException を突破できないので力技）
                    action = webdriver.ActionChains(driver)
                    keys_to_send = [Keys.TAB, Keys.ENTER, Keys.TAB, Keys.TAB, Keys.TAB, Keys.TAB, Keys.TAB, Keys.ENTER]
                    for key in keys_to_send:
                        action.send_keys(key).perform()
                    time.sleep(10)
                    stock_count = "get_by_stock_count"
                    break
            else:
                print(f"- {target} は出品していません")
                stock_count = 0

        return stock_count

    def close_tabs():
        # 先頭タブを除きすべてのタブを閉じる
        for handle in driver.window_handles[1:]:
            driver.switch_to.window(handle)
            driver.close()
        driver.switch_to.window(driver.window_handles[0])

    retry_count = 0
    max_retries = 2
    is_success = False
    while not is_success:
        try:
            print(f"ASIN: {asin} / target: {target}")
            url = f"https://www.amazon.co.jp/dp/{asin}"
            # URLにアクセス
            driver.get(url)

            # 販売元が表示されているか判定
            seller_name_elements = driver.find_elements(By.ID, "sellerProfileTriggerId")
            # 販売元が表示されている
            if len(seller_name_elements):
                print("販売元が表示されている")
                seller_name = seller_name_elements[0].text
                if seller_name == target:
                    print("販売元＝ターゲット")
                    # カートに追加
                    add_to_cart_button = driver.find_element(
                        By.XPATH, "//*[@id='add-to-cart-button']"
                    )
                    add_to_cart_button.click()
                    stock_count = "get_by_stock_count"
                else:
                    print("販売元がターゲットでない")
                    stock_count = track_target()
                    close_tabs()

            else:
                print("販売元が表示されていない")
                stock_count = track_target()
                close_tabs()
            return stock_count

        except Exception:
            if retry_count > max_retries:
                print(
                    f"{asin} のデータ取得のリトライ上限に達しました。次の商品に移ります。"
                )
                stock_count = "error"
                close_tabs()
                break
            else:
                retry_count += 1
                print(
                    f"{asin} のデータ取得に失敗しました。リトライします。（リトライ回数：{retry_count}回目）"
                )


def get_stock_count(driver):
    """
    Get stock count from amazon

    Parameters
    ----------
    driver : WebDriver
        Initialized WebDriver

    Returns
    ----------
    stock_count : str or int
        stock count
    """

    retry_count = 0
    max_retries = 2
    is_success = False
    while not is_success:
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
            is_success = True

        except Exception:
            if retry_count > max_retries:
                print("- データ取得のリトライ上限に達しました。次の商品に移ります。")
                stock_count = "error"
                break
            else:
                retry_count += 1
                print(
                    f"- データ取得に失敗しました。リトライします。（リトライ回数：{retry_count}回目）"
                )
        finally:
            # 先頭タブを除きすべてのタブを閉じる
            for handle in driver.window_handles[1:]:
                driver.switch_to.window(handle)
                driver.close()
            driver.switch_to.window(driver.window_handles[0])
    # WebDriverを閉じる
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
    sheet.append_rows(quantities, table_range="D1", value_input_option='USER_ENTERED')


if __name__ == "__main__":

    start_time = datetime.datetime.now()
    print(f"処理を開始します - {start_time.strftime('%H:%M')}")
    # WebDriver の初期化
    auth = google_auth()
    # ASIN / 出品者を取得
    print("ASIN / 出品者を取得します")
    asins, targets = get_asins_and_targets(auth)
    # Amazon から在庫数を取得します
    print("Amazon から在庫数を取得します")
    stock_counts = []
    driver = init_driver()
    # asins = ["B07M6KPJ9K", "B07M6KPJ9K"]
    # targets = ["SATISストア", "MIBAストア（インボイス登録済）"]
    for asin, target in zip(asins, targets):
        stock_count = add_to_cart(driver, asin, target)
        if stock_count == "get_by_stock_count":
            stock_counts.append(get_stock_count(driver))
        else:
            stock_counts.append(stock_count)
    driver.quit()
    # スプレッドシートへ在庫数を入力
    print("スプレッドシートへ在庫数を入力します")
    post_to_spreadsheet(auth, stock_counts)

    end_time = datetime.datetime.now()
    print(f"処理が完了しました - {end_time.strftime('%H:%M')}")