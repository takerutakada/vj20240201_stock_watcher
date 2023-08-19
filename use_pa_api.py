from amazon.paapi import AmazonAPI
import configparser

ini_file = configparser.ConfigParser()
ini_file.read('./config.ini', 'UTF-8')

ACCESS_KEY = ini_file.get('API', 'ACCESS_KEY')
SECRET_KEY = ini_file.get('API', 'SECRET_KEY')
ASSOCIATE_ID =  ini_file.get('API', 'ASSOCIATE_ID')
COUNTRY =  ini_file.get('API', 'COUNTRY')

amazon_api = AmazonAPI(ACCESS_KEY, SECRET_KEY, ASSOCIATE_ID, COUNTRY)

products = amazon_api.get_items(item_ids=['B01N5IB20Q','B01F9G43WU'])

print(products['data']['B01N5IB20Q'])
