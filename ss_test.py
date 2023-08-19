import gspread
import os

dir_path = os.path.dirname(__file__)
gc = gspread.oauth(
                   credentials_filename=os.path.join(dir_path, "client_secret.json"),
                   authorized_user_filename=os.path.join(dir_path, "authorized_user.json"),
                   )
# スプレッドシート生成
wb = gc.create("test") # testのファイルを作成
print(wb.id) # キーを後々の参照用に出力しておく

# スプレッドシートに書き込み
wb = gc.open_by_key(wb.id) # testのファイルを開く(キーから)
ws = wb.get_worksheet(0) # 最初のシートを開く(idは0始まりの整数)

data = [
        ['ASIN', '商品名', '2023/08/20', '2023/08/21'],
        [1, 2, '2023/01/01', '寒い'],
        [3, 20, '2023/02/01', 'ふつう'],
        [31, 14, '2023/03/21', '暑い'],
        [16, 32, '2023/04/22', 'だるい'],
        [13, 100, '2023/05/03', '微熱がある'],
        ]

# 複数行一括書き込み
ws.append_rows(data)

