"""
amazon からの返答

お世話になっております。
APIサポートでございます。

Catalog Items APIを呼び出しているとのことですが、お客様がお持ちの以下のロールではCatalog Items APIを呼びだすことが出来ません。

・Amazonから発送
・購入者にフィードバックを依頼
・財務会計
・在庫と注文の追跡
・ブランド分析

Catalog Items APIのご使用にはProduct Listing(商品の出品) のロールが必要となります。
https://developer-docs.amazon.com/sp-api/docs/product-listing-role

テストコールを行う場合には、Sellers API をお試しください。
https://developer-docs.amazon.com/sp-api/docs/sellers-api-v1-reference#get-sellersv1marketplaceparticipations

詳細につきましては以下のドキュメントの5. テストコール⼿順をご参照ください。
https://spapi-apac-doc.s3.ap-northeast-1.amazonaws.com/SP-API%E8%A8%AD%E5%AE%9A%E3%83%9E%E3%83%8B%E3%83%A5%E3%82%A2%E3%83%AB_%E6%97%A5%E6%9C%AC%E8%AA%9E_20230316.pdf

引き続きよろしくお願いいたします。

宜しくお願いいたします。

"""

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
