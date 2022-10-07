import time
import requests
import yaml
import web3 as w3

def parse_config(path):
    with open(path, 'r') as stream:
        return  yaml.load(stream, Loader=yaml.FullLoader)

def get_w3(conf):
    rpc = conf["node"]
    web3 = w3.Web3(w3.HTTPProvider(rpc))
    return web3

def get_abi(conf,address):
    headers      = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'}
    url = conf["etherscan"].format(address)
    while True:
        try:
            result = requests.get(url,headers=headers).json()
            if result["status"] != '0':
                return result["result"]
            else:
                print("error seen with abi fetch, trying again")
                time.spleep(3)
                continue
        except:
            print("error seen with abi fetch, trying again")
            time.sleep(3)

def get_contract(conf,address):
    abi = get_abi(conf,address)
    w3 = get_w3(conf)
    return w3.eth.contract(address=address,abi=abi)