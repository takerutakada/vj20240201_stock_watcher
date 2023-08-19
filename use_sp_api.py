import configparser
from sp_api.api import Products
from sp_api.api import Catalog
from sp_api.base.marketplaces import Marketplaces


ini_file = configparser.ConfigParser()
ini_file.read('./config.ini', 'UTF-8')

credentials = dict(
    refresh_token = ini_file.get('SP-API', 'SP_API_REFRESH_TOKEN'),  # From Seller central under Authorise -> Refresh Token
    lwa_app_id = ini_file.get('SP-API', 'LWA_APP_ID'),  # From Seller Central, named CLIENT IDENTIFIER on website.
    lwa_client_secret = ini_file.get('SP-API', 'LWA_CLIENT_SECRET'), # From Seller Central, named CLIENT SECRET on website.
    aws_access_key = ini_file.get('SP-API', 'SP_API_ACCESS_KEY'), # From AWS IAM Setup
    aws_secret_key = ini_file.get('SP-API', 'SP_API_SECRET_KEY'), # From AWS IAM Setup
    role_arn = ini_file.get('SP-API', 'SP_API_ROLE_ARN'),  #arn:aws:iam::1234567890:role/SellingPartnerAPIRole
)

def productCompetitive_asin(ASIN_LIST):
    # 商品検索用オブジェクト
    products = Products(marketplace=Marketplaces.JP,   # 対象のマーケットプレイスを指定
                  credentials=credentials)             # API情報を指定

    # 結果取得
    result = products.get_competitive_pricing_for_asins(ASIN_LIST)
    return result()


# 引数（ASINのリスト）
ASIN_LIST = ['B07SK4W1VJ','B097B2HQ5R']
ASIN_LIST = 'B07SK4W1VJ'
# 関数実行
productCompetitive_asin(ASIN_LIST)

# def search_product(ASIN):
#     # 商品検索用オブジェクト
#     obj = Catalog(marketplace=Marketplaces.JP,   # 対象のマーケットプレイスを指定
#                   credentials=credentials)       # API情報を指定

#     # ASINコードを指定し商品情報取得
#     result = obj.get_item(ASIN)
#     return result()

# # 検索条件（ASINコード）
# ASIN = "B07WXL5YPW"

# # 関数実行
# search_product(ASIN)
