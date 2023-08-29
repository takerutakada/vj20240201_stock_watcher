import configparser
import time
import datetime
import gspread
import os
import sys
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

# 設定ファイル
SETTING_DIR = 'settings'

# if getattr(sys, 'frozen', False):
# # 実行ファイルからの実行時
#     dir_path = sys._MEIPASS
# else:
# # スクリプトからの実行時
# dir_path = f'{os.path.dirname(__file__)}/{SETTING_DIR}'
dir_path = f'{os.path.dirname(os.path.abspath(sys.argv[0]))}/{SETTING_DIR}'
print(dir_path)

ini_file = configparser.ConfigParser()
ini_file.read(f'{dir_path}/config.ini', 'UTF-8')
WORKBOOK_KEY = ini_file.get('SPREAD-SHEETS', 'WORKBOOK_KEY')
# WORKBOOK_KEY = '1bW-mhl-2NasK8uqPWI85Ur2Vm6qpjUNoifxf5GkdQMI'
# WORKBOOK_KEY = sys.argv[1]

def operate_sheet(mode, data = ''):

    gc = gspread.oauth(
        credentials_filename = f'{dir_path}/client_secret.json',
        authorized_user_filename = f'{dir_path}/authorized_user.json',
        )

    # スプレッドシートを開く
    worksheet = gc.open_by_key(WORKBOOK_KEY).worksheet('Sheet1')

    if mode == 'r':
        return worksheet.col_values(1)[1:]

    elif mode == 'w':

        # 既存のデータを取得
        existing_data = worksheet.get_values()

        # 現在の日付を取得
        current_date = datetime.datetime.now().strftime("%Y/%m/%d")

        # 列名を取得
        header_row = worksheet.row_values(1)
        num_existing_columns = len(header_row)

        # 新しい列を追加
        new_column_index = num_existing_columns + 1
        worksheet.update_cell(1, new_column_index, current_date)

        # 各データに対して処理
        for asin, quantity in data.items():
            row_exists = False
            for row in existing_data:
                if row[0] == asin:
                    row_exists = True
                    row_index = existing_data.index(row) + 1
                    worksheet.update_cell(row_index, new_column_index, quantity)
                    break

            if not row_exists:
                new_row = [asin, ""] + [""] * (new_column_index - 2) + [quantity]
                worksheet.append_row(new_row)

        print('スプレッドシートへの入力が完了しました。')

def get_data(asins):

    # WebDriverの初期化
    options = webdriver.ChromeOptions()
    # options.add_argument('--headless')
    driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=options)

    driver.set_window_position(0,0) # ブラウザの位置を左上に固定
    driver.set_window_size(860,1200) # ブラウザのウィンドウサイズを固定

    data = {}

    for asin in asins:
        retry_count = 0
        max_retries = 3
        is_success = False
        while not is_success:
            try:
                # Amazon商品検索用URLを構築
                url = f"https://www.amazon.co.jp/s?k={asin}"

                # URLにアクセス
                driver.get(url)

                # 商品詳細ページに遷移
                product_link = driver.find_element(By.CSS_SELECTOR, ".s-result-item a")
                product_link.click()
                driver.switch_to.window(driver.window_handles[-1])

                # カートに追加
                add_to_cart_button = driver.find_element(By.CSS_SELECTOR, "#add-to-cart-button")
                add_to_cart_button.click()

                # カートに移動
                driver.get("https://www.amazon.co.jp/gp/cart/view.html")

                # 数量選択ページに遷移
                time.sleep(2)
                quantity_button = driver.find_element(By.CSS_SELECTOR, "#a-autoid-0-announce")
                quantity_button.click()
                time.sleep(2)

                # 10+を選択
                while 'product' in driver.current_url:
                    print('キャンペーン広告をクリックしました。ブラウザバックします')
                    driver.back()
                    time.sleep(2)
                ten_plus_option = driver.find_element(By.XPATH, "//a[contains(text(),'10+')]")
                ten_plus_option.click()

                # 数量入力
                quantity_input = driver.find_element(By.NAME, "quantityBox")
                quantity_input.send_keys(Keys.CONTROL + "a")
                quantity_input.send_keys("999")
                quantity_input.send_keys(Keys.RETURN)

                # 購入可能数量を取得して出力
                time.sleep(2)
                driver.get("https://www.amazon.co.jp/gp/cart/view.html")
                quantity_input = driver.find_element(By.NAME, "quantityBox")
                available_quantity = quantity_input.get_attribute("value")
                print(f"ASIN: {asin} - 購入可能数量: {available_quantity}")

                # 削除ボタンをクリックして商品をカートから削除
                driver.get("https://www.amazon.co.jp/gp/cart/view.html")
                delete_button = driver.find_element(By.CSS_SELECTOR, "span.a-size-small.sc-action-delete")
                delete_button.click()
                time.sleep(2)

                data[asin] = available_quantity
                is_success = True

            except:
                if retry_count > max_retries:
                    print(f'{asin} のデータ取得のリトライ上限に達しました。次の商品に移ります。')
                else:
                    retry_count += 1
                    print(f'{asin} のデータ取得に失敗しました。リトライします。（リトライ回数：{retry_count}回目）')
                    continue

    # WebDriverを閉じる
    driver.quit()
    print('データの取得が完了しました。')
    return data

def main_func():

    # 時間計測開始
    time_sta = time.perf_counter()
    # 実行
    asins = operate_sheet('r')
    data = get_data(asins)
    operate_sheet('w', data)
    # 時間計測終了
    time_end = time.perf_counter()
    # 経過時間（秒）
    tim = time_end- time_sta
    print(f'処理時間：{round(tim, 2)}秒')

if __name__ == '__main__':

    main_func()

