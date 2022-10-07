import json
from utils.utility import get_w3

class SnxContracts():

    def __init__(self,conf):
            
        self.conf    = conf
        self.w3   = get_w3(conf)
                                                               
    def get_snx_contract(self,contractNameAddress,contractNameAbi=None):
        if contractNameAbi is None:
            contractNameAbi = contractNameAddress
        with open("config/deployment.json",encoding='utf-8') as f:
            data = json.loads(f.read())
        address = data["targets"][contractNameAddress]["address"]    
        abi = data["sources"][contractNameAbi ]["abi"]
        return self.w3.eth.contract(address=address,abi=abi)