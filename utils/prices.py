# -*- coding: utf-8 -*-
from web3 import Web3
from utils.utility import get_w3, get_abi

class Prices:
    def __init__(self,conf):
        self.exchangerRatesContract = self.get_snx_contract(contractNameAddress='ExchangeRates',
                                                            contractNameAbi='ExchangeRatesWithDexPricing')
        self.init_univ3_contracts()

    def init_univ3_contracts(self):
        self.uniContractDict = dict()
        w3 = get_w3(self.conf)
        abi = get_abi(self.conf,self.conf["univ3"]["poolAbi"])
        for lpFee in self.conf["univ3"]["poolAddress"].keys():
            self.uniContractDict[lpFee] = {}
            for token in self.conf["univ3"]["poolAddress"][lpFee]:
                address = self.conf["univ3"]["poolAddress"][lpFee][token]        
                self.uniContractDict[lpFee][token] = w3.eth.contract(address=address,abi=abi)    
    
    def get_uni_prices(self,ticker,poolFeeBp,twap):
        #return spot/twap price for a tickerPrices
        if ticker.lower() == 'usd':
            return 1,1
        
        elif not ticker.lower() in ['eth','btc']:
            return -1,-1

        elif ticker.lower() == 'btc':
                
            #wbtc/usdc 5 bp need to do weth/usdc*usdc/wbtc
            #get the eth price
            contract = self.uniContractDict[poolFeeBp]['usd']
            tickCumulatives, _ = contract.functions.observe([0,twap]).call()
            tick = (tickCumulatives[0]-tickCumulatives[1])  / twap
            (sqrtPriceX96,_,_,_,_,_,_)=contract.functions.slot0().call()
            ethSpotPrice = 1e12/(sqrtPriceX96/2**96)**2
            ethTwapPrice = 1e12 / 1.0001**tick

            contract = self.uniContractDict[poolFeeBp]['btc']
            tickCumulatives, _ = contract.functions.observe([0,twap]).call()
            tick = (tickCumulatives[0]-tickCumulatives[1])  / twap
            (sqrtPriceX96,_,_,_,_,_,_)=contract.functions.slot0().call()
            btcEthSpotPrice = (sqrtPriceX96/2**96)**2/1e10
            btcEthTwapPrice = 1.0001**tick/1e10

            spotPrice = ethSpotPrice*btcEthSpotPrice
            twapPrice = ethTwapPrice*btcEthTwapPrice

        else:
            #getting eth price
            contract = self.uniContractDict[poolFeeBp]['usd']
            tickCumulatives, _ = contract.functions.observe([0,twap]).call()
            tick = (tickCumulatives[0]-tickCumulatives[1])  / twap
            (sqrtPriceX96,_,_,_,_,_,_)=contract.functions.slot0().call()
    
            spotPrice = 1e12/(sqrtPriceX96/2**96)**2
            twapPrice = 1e12 / 1.0001**tick
            
            return spotPrice, twapPrice

    def get_atomic_link_price(self,fromCurrencyKey,toCurrencyKey):
        fromHex   = Web3.toHex(text=fromCurrencyKey).ljust(66,"0")
        toHex     = Web3.toHex(text=toCurrencyKey).ljust(66,"0")
        atomicRate, systemRate,systemSourceRate,systemDestinationRate = self.exchangerRatesContract.functions.effectiveAtomicValueAndRates(fromHex,
                                                                                                                                           int(1e18),
                                                                                                                                           toHex).call()
        return atomicRate/1e18 , systemRate/1e18