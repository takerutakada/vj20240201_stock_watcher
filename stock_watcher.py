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
    if MODE == "TEST":
        # service_account.json
        JSON = os.environ.get("JSON_TEST")
        # スプレッドシート（「https://docs.google.com/spreadsheets/d/」以降の文字列）
        WORKBOOK_KEY = os.environ.get("WORKBOOK_KEY_TEST")
    elif MODE == "PROD":
        # service_account.json
        JSON = os.environ.get("JSON")
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


def get_asin2target(auth):
    """
    Get asin2target from spreadsheet

    Parameters
    ----------
    auth : gspread.authorize()
        authorization for operating spreadsheet

    Return
    ----------
    asin2target : dict
        dict(Key: asins / Value: target)
    """

    sheet = auth.open_by_key(WORKBOOK_KEY).worksheet("シート1")
    asins = sheet.col_values(1)[1:]
    targets = sheet.col_values(3)[1:]
    asin2target = dict(zip(asins, targets))
    return asin2target


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

    retry_count = 0
    max_retries = 2
    is_success = False
    while not is_success:
        try:
            print(f"ASIN: {asin} / target: {target}")
            # Amazon商品検索用URLを構築（&rh=p_...以降でスポンサー広告商品を除外）
            url = f"https://www.amazon.co.jp/s?k={asin}&rh=p_36%3A1000-%2Cp_8%3A0-&__mk_ja_JP=カタカナ&tag=krutw-22&ref=nb_sb_noss_1"
            # URLにアクセス
            driver.get(url)
            # 先頭に「結果」という文字列の要素がない場合は商品が存在しないので、処理をスキップ
            txt_result = driver.find_elements(
                By.XPATH,
                "//*[@id='search']/div[1]/div[1]/div/span[1]/div[1]/div[1]/div/span/div/div/span",
            )
            if not len(txt_result):
                print("- 該当の商品が見つかりませんでした")
                stock_count = "-"
                break
            # 商品詳細ページに遷移
            product_link = driver.find_element(By.CSS_SELECTOR, ".s-result-item a")
            product_link.click()
            driver.switch_to.window(driver.window_handles[-1])
            out_of_stock = driver.find_elements(By.ID, "outOfStock")
            olp_link_widget = driver.find_elements(
                By.XPATH, "//*[@id='olpLinkWidget_feature_div']/div[2]"
            )
            # 商品が在庫切れ
            if len(out_of_stock):
                print("- 在庫切れです")
                stock_count = 0
            # 複数の出品者が存在する
            elif len(olp_link_widget):
                olp_link_widget[0].click()
                seller_name_elements = driver.find_elements(
                    By.XPATH, "//*[@id='aod-offer-soldBy']/div/div/div[2]/a"
                )
                for seller_name_element in seller_name_elements:
                    # 出品者の中に target が存在する
                    if seller_name_element.text == target:
                        add_to_cart_url = seller_name_element.get_attribute("href")
                        driver.get(add_to_cart_url)
                        # 「カートに入れる」ボタンをクリック（ElementClickInterceptedException を突破できないので力技）
                        action = webdriver.ActionChains(driver)
                        action.send_keys(Keys.TAB).perform()
                        action.send_keys(Keys.ENTER).perform()
                        action.send_keys(Keys.ENTER).perform()
                        action.send_keys(Keys.TAB).perform()
                        action.send_keys(Keys.TAB).perform()
                        action.send_keys(Keys.TAB).perform()
                        action.send_keys(Keys.TAB).perform()
                        action.send_keys(Keys.TAB).perform()
                        action.send_keys(Keys.ENTER).perform()
                        time.sleep(5)
                        stock_count = "get_by_stock_count"
                        break
                else:
                    print(f"- {target} は出品していません")
                    stock_count = 0
            else:
                seller_name = driver.find_element(By.ID, "sellerProfileTriggerId").text
                if seller_name == target:
                    # カートに追加
                    add_to_cart_button = driver.find_element(
                        By.XPATH, "//*[@id='add-to-cart-button']"
                    )
                    add_to_cart_button.click()
                    stock_count = "get_by_stock_count"
                else:
                    print(f"- {target} は出品していません")
                    stock_count = 0

        except Exception:
            if retry_count > max_retries:
                print(
                    f"{asin} のデータ取得のリトライ上限に達しました。次の商品に移ります。"
                )
                stock_count = "error"
                break
            else:
                retry_count += 1
                print(
                    f"{asin} のデータ取得に失敗しました。リトライします。（リトライ回数：{retry_count}回目）"
                )
        finally:
            # 先頭タブを除きすべてのタブを閉じる
            for handle in driver.window_handles[1:]:
                driver.switch_to.window(handle)
                driver.close()
            driver.switch_to.window(driver.window_handles[0])
            return stock_count


def get_stock_count(driver, asin):
    """
    Get stock count from amazon

    Parameters
    ----------
    driver : WebDriver
        Initialized WebDriver
    asin : str
        ASIN code

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
            time.sleep(3)
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


def post_to_spreadsheet(auth, data):
    """
    Posting data to spreadsheet

    Parameters
    ----------
    auth : gspread.authorize()
        authorization for operating spreadsheet
    data : dict
        data got from amazon
    """

    sheet = auth.open_by_key(WORKBOOK_KEY).worksheet("シート1")
    # 既存のデータを取得
    existing_data = sheet.get_values()
    # 現在の日付を取得
    current_date = datetime.datetime.now().strftime("%Y/%m/%d")
    # 列名を取得
    header_row = sheet.row_values(1)
    num_existing_columns = len(header_row)
    # 新しい列を追加
    new_column_index = num_existing_columns + 1
    sheet.update_cell(1, new_column_index, current_date)
    # 各データに対して処理
    for asin, quantity in data.items():
        row_exists = False
        for row in existing_data:
            if row[0] == asin:
                row_exists = True
                row_index = existing_data.index(row) + 1
                sheet.update_cell(row_index, new_column_index, quantity)
                break
        if not row_exists:
            new_row = [asin, ""] + [""] * (new_column_index - 2) + [quantity]
            sheet.append_row(new_row)


if __name__ == "__main__":

    start_time = datetime.datetime.now()
    print(f"処理を開始します - {start_time.strftime('%H:%M')}")
    # WebDriver の初期化
    auth = google_auth()
    # ASIN / 出品者を取得
    print("ASIN / 出品者を取得します")
    asin2target = get_asin2target(auth)
    # Amazon から在庫数を取得します
    print("Amazon から在庫数を取得します")
    stock_count_dic = {}
    driver = init_driver()
    for asin, target in asin2target.items():
        stock_count = add_to_cart(driver, asin, target)
        if stock_count == "get_by_stock_count":
            stock_count_dic[asin] = get_stock_count(driver, asin)
        else:
            stock_count_dic[asin] = stock_count
    driver.quit()
    # スプレッドシートへ在庫数を入力
    print("スプレッドシートへ在庫数を入力します")
    post_to_spreadsheet(auth, stock_count_dic)

    end_time = datetime.datetime.now()
    print(f"処理が完了しました - {end_time.strftime('%H:%M')}")
