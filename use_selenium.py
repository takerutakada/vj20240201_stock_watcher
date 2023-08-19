import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

import gspread
import os

# 時間計測開始
time_sta = time.perf_counter()

# ASINsリストを定義
asins = ["B0B9H67NYT", "B0B9GMPXGN", "B0B9GP8WF8"]

success, failed = 0, 0

trials_count = 0
max_trial_count = 10

def get_data():

    # WebDriverの初期化
    options = webdriver.ChromeOptions()
    # options.add_argument('--headless')
    driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=options)

    data = [['ASIN', '商品名', '2023/08/20']]

    for asin in asins:
        # Amazon商品検索用URLを構築
        url = f"https://www.amazon.co.jp/s?k={asin}"

        # URLにアクセス
        driver.get(url)

        # 商品詳細ページに遷移
        product_link = driver.find_element(By.CSS_SELECTOR, ".s-result-item a")
        product_link.click()
        driver.switch_to.window(driver.window_handles[-1])

        # カートに追加
        try:
            add_to_cart_button = driver.find_element(By.CSS_SELECTOR, "#add-to-cart-button")
            add_to_cart_button.click()
        except:
            print(f"ASIN: {asin} - カートに追加できませんでした。")
            continue

        # カートに移動
        driver.get("https://www.amazon.co.jp/gp/cart/view.html")

        # 数量選択ページに遷移
        time.sleep(2)
        quantity_button = driver.find_element(By.CSS_SELECTOR, "#a-autoid-0-announce")
        quantity_button.click()
        time.sleep(2)

        # 10+を選択
        while 'product' in driver.current_url:
            print(driver.current_url)
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
        driver.get("https://www.amazon.co.jp/gp/cart/view.html")
        quantity_input = driver.find_element(By.NAME, "quantityBox")
        time.sleep(2)
        available_quantity = quantity_input.get_attribute("value")
        print(f"ASIN: {asin} - 購入可能数量: {available_quantity}")
        data.append([asin, '', available_quantity])

        # 削除ボタンをクリックして商品をカートから削除
        driver.get("https://www.amazon.co.jp/gp/cart/view.html")
        delete_button = driver.find_element(By.CSS_SELECTOR, "span.a-size-small.sc-action-delete")
        delete_button.click()
        time.sleep(2)

    # WebDriverを閉じる
    print(data)
    driver.quit()
    return data

def write_sheet(data):

    WORKBOOK_KEY = '1YUidupPf4GmIMECZh1SAv2qIcNZvWFvbSo-olA1UzPI'

    dir_path = os.path.dirname(__file__)
    gc = gspread.oauth(
                    credentials_filename=os.path.join(dir_path, "client_secret.json"),
                    authorized_user_filename=os.path.join(dir_path, "authorized_user.json"),
                    )
    # スプレッドシートに書き込み
    wb = gc.create("test03") # test03のファイルを作成
    print(wb.id)
    wb = gc.open_by_key(wb.id) # test03のファイルを開く(キーから)
    ws = wb.get_worksheet(0) # 最初のシートを開く(idは0始まりの整数)
    print(ws.title)

    # ws = gc.open_by_key(WORKBOOK_KEY).worksheet('Sheet1')
    # ws.clear()

    ws.append_rows(data)

def main_func():
    data = get_data()
    write_sheet(data)

main_func()

# while trials_count <= max_trial_count:
#     try:
#         main_func()
#         success += 1
#     except:
#         failed += 1
#         continue
#     trials_count += 1
#     print(trials_count)

# print(f'success: {success} / failed: {failed}')

# 時間計測終了
time_end = time.perf_counter()
# 経過時間（秒）
tim = time_end- time_sta

print(f'処理が完了しました。処理時間：{tim}')
