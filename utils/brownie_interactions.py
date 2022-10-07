from web3 import Web3
import brownie
from brownie import Contract as bContract
from brownie import accounts as bAccount
from utils.utility import get_w3, get_contract
from eth_account import Account
import numpy as np
from utils.snx_contract import SnxContracts
from utils.prices import Prices
import time

class BrownieInteractions(SnxContracts,Prices):
    
    def __init__(self,conf):

        self.w3 = get_w3(conf)
        SnxContracts.__init__(self,conf)
        Prices.__init__(self,conf)
        self.conf=conf
        self.connect_brownie()
        self.setup_contracts()                
            
    def setup_contracts(self):
        
        self.contracts = {}
        
        contract = get_contract(self.conf,'0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2')
        self.contracts['weth'] = bContract.from_abi(name='weth',address=contract.address,abi=contract.abi)
        
        contract = get_contract(self.conf,'0x68b3465833fb72A70ecDF485E0e4C7bD8665Fc45')
        self.contracts['uni'] = bContract.from_abi(name='uni',address=contract.address,abi=contract.abi)
        
        #setup synthetix contract
        proxyContract = self.get_snx_contract(contractNameAddress="ProxyERC20")
        snxContract   = self.get_snx_contract(contractNameAddress="Synthetix")
        self.contracts['snx'] = bContract.from_abi(name='snx', address=proxyContract.address, abi=snxContract.abi)

        #setup susd contract
        contract = self.get_snx_contract(contractNameAddress="ProxyERC20sUSD",contractNameAbi='ProxyERC20')
        self.contracts['susd'] = bContract.from_abi(name='snx', address=contract.address, abi=contract.abi)

        #setup seth contract
        contract = self.get_snx_contract(contractNameAddress="ProxysETH",contractNameAbi='ProxyERC20')
        self.contracts['seth'] = bContract.from_abi(name='snx', address=contract.address, abi=contract.abi)
        
        #setup direct integration contract
        contract = self.get_snx_contract('DirectIntegrationManager')
        self.contracts['integration'] = bContract.from_abi(name='di', address=contract.address, abi=contract.abi)
        
        #setup collateral eth contract
        contract = self.get_snx_contract('CollateralEth')
        self.contracts['collateral_eth'] = bContract.from_abi(name='di', address=contract.address, abi=contract.abi)
        
        #setup collateral eth contract
        contract = self.get_snx_contract('ExchangeRates')
        self.contracts['exchange_rates'] = bContract.from_abi(name='di', address=contract.address, abi=contract.abi)
        
            
    def approve(self,approver,approvee,amount,contractName):
        return self.contracts[contractName].approve(approvee,amount,{"from":approver,'max_fee':int(1e9),'priority_fee':int(1e9)})
    
    def balance_of(self,contractName,account):
        contract = self.contracts[contractName]
        return contract.balanceOf(account.address)
    
    def set_integration(self,
                        targetAddress,
                        currencyKey,
                        dexPriceAggregator='0x0000000000000000000000000000000000000000',
                        atomicEquivalentForDexPricing='0x0000000000000000000000000000000000000000',
                        atomicExchangeFeeRate=0,
                        atomicTwapWindow=0,
                        atomicMaxTwapDelta=0,
                        atomicMaxVolumePerBlock=0,
                        atomicVolatilityConsiderationWindow=0,
                        atomicVolatilityTwapSeconds=0,
                        atomicVolatilityUpdateThreshold=0,
                        exchangeFeeRate=0,
                        exchangeMaxDynamicFee=0,
                        exchangeDynamicFeeRounds=0,
                        exchangeDynamicFeeThreshold=0,
                        exchangeDynamicFeeWeightDecay=0):
        currencyKeyHex = self.w3.toHex(text=currencyKey)
        currencyKeyHex = self.w3.toHex(text=currencyKey).ljust(66,"0")
        return self.contracts["integration"].setExchangeParameters(targetAddress,
                                                                   [currencyKeyHex],
                                                                   [currencyKeyHex,
                                                                    dexPriceAggregator,
                                                                    atomicEquivalentForDexPricing,
                                                                    atomicExchangeFeeRate,
                                                                    atomicTwapWindow,
                                                                    atomicMaxTwapDelta,
                                                                    atomicMaxVolumePerBlock,
                                                                    atomicVolatilityConsiderationWindow,
                                                                    atomicVolatilityTwapSeconds,
                                                                    atomicVolatilityUpdateThreshold,
                                                                    exchangeFeeRate,
                                                                    exchangeMaxDynamicFee,
                                                                    exchangeDynamicFeeRounds,
                                                                    exchangeDynamicFeeThreshold,
                                                                    exchangeDynamicFeeWeightDecay],
                                                                   {'from' : bAccount[-1],
                                                                    'max_fee':int(1e9),
                                                                    'priority_fee':int(1e9)})
        
    def swap_uni(self,account,fromToken,toToken,fromAmount,fee):        
        #create some random account
        randomAccount = Account.create()        
        #send random some eth
        bAccount[0].transfer(randomAccount.address,'1 ether',gas_price='1 gwei')
                
        #send the tokens to the random account
        self.contracts[fromToken].transfer(randomAccount.address,fromAmount,{'from':account,'max_fee':int(1e9),'priority_fee':int(1e9)})
        
        #have the suspense account approve uni to spend from tokens
        contract = get_contract(self.conf,self.contracts[fromToken].address)
        txPrep = contract.functions.approve(self.contracts["uni"].address,int(fromAmount))
        tx = txPrep.buildTransaction({'chainId': 1,
                                      'gas': int(1e6),
                                      'maxFeePerGas': int(1e9),
                                      'maxPriorityFeePerGas': int(1e9),
                                      'type': 2 ,
                                      'nonce': self.w3.eth.getTransactionCount(randomAccount.address)})
        signedTx = self.w3.eth.account.sign_transaction(tx, randomAccount.key)            
        txHash = self.w3.eth.sendRawTransaction(signedTx.rawTransaction)        
        txReceipt = self.w3.eth.getTransactionReceipt(txHash)
        assert txReceipt["status"] == 1,"approve failed"

        #swap the tokens on uniswap
        contract = get_contract(self.conf,self.contracts["uni"].address)
        txPrep = contract.functions.exactInputSingle({'tokenIn':self.contracts[fromToken].address,
                                                      'tokenOut':self.contracts[toToken].address,
                                                      'fee':fee,
                                                      'recipient':randomAccount.address,
                                                      'deadline':int(time.time()+500),
                                                      'amountIn':int(fromAmount),
                                                      'amountOutMinimum':0,
                                                      'sqrtPriceLimitX96':0})
        tx = txPrep.buildTransaction({'chainId': 1,
                                      'gas': int(1e6),
                                      'maxFeePerGas': int(1e9),
                                      'maxPriorityFeePerGas': int(1e9),
                                      'type': 2 ,
                                      'nonce': self.w3.eth.getTransactionCount(randomAccount.address)})
        signedTx = self.w3.eth.account.sign_transaction(tx, randomAccount.key)            
        txHash = self.w3.eth.sendRawTransaction(signedTx.rawTransaction)        
        txReceipt = self.w3.eth.getTransactionReceipt(txHash)
        assert txReceipt["status"] == 1,"swap failed"
        
        #send the tokens to account
        contract = get_contract(self.conf,self.contracts[toToken].address)
        
        txPrep = contract.functions.transfer(account.address,contract.functions.balanceOf(randomAccount.address).call())
        tx = txPrep.buildTransaction({'chainId': 1,
                                      'gas': int(1e6),
                                      'maxFeePerGas': int(1e9),
                                      'maxPriorityFeePerGas': int(1e9),
                                      'type': 2 ,
                                      'nonce': self.w3.eth.getTransactionCount(randomAccount.address)})
        signedTx = self.w3.eth.account.sign_transaction(tx, randomAccount.key)            
        txHash = self.w3.eth.sendRawTransaction(signedTx.rawTransaction)        
        txReceipt = self.w3.eth.getTransactionReceipt(txHash)
        assert txReceipt["status"] == 1,"sending tokens back to account failed"        
        return self.w3.eth.sendRawTransaction(signedTx.rawTransaction)        
        
    def eth_to_weth(self,account,amount):        
        return self.contracts["weth"].deposit({'value':amount,
                                               'from':account,
                                               'max_fee':int(1e9),
                                               'priority_fee':int(1e9)})
    
    def eth_to_susd(self,account,ethAmount):
        ethPrice = self.get_link_price('sETH')
        currencyKeyHex = self.w3.toHex(text='sUSD').ljust(66,"0")
        return self.contracts["collateral_eth"].open(\
                                                     int(ethAmount*ethPrice/1.31),\
                                                         currencyKeyHex,\
                                                             {'value':ethAmount,
                                                              'from':account,
                                                              'max_fee':int(1e9),
                                                              'priority_fee':int(1e9)})
    
    def swap_atomically(self,fromCurrencyKey,toCurrencyKey,fromAmount,account):
        fromAmountPre = self.balance_of(fromCurrencyKey.lower(), account)
        toAmountPre   = self.balance_of(toCurrencyKey.lower(), account)        
        atomicRate, chainlinkRate  = self.get_atomic_link_price(fromCurrencyKey=fromCurrencyKey, toCurrencyKey=toCurrencyKey)
        fromHex   = Web3.toHex(text=fromCurrencyKey).ljust(66,"0")
        toHex     = Web3.toHex(text=toCurrencyKey).ljust(66,"0")
        self.contracts["snx"].exchangeAtomically(fromHex,
                                                 fromAmount,
                                                 toHex,
                                                 '0x0000000000000000000000000000000000000000',
                                                 0,
                                                 {'from':account,
                                                  'max_fee':int(1e9),
                                                  'priority_fee':int(1e9)})        
        fromAmountPost = self.balance_of(fromCurrencyKey.lower(), account)
        toAmountPost   = self.balance_of(toCurrencyKey.lower(), account)
        
        return  1 - (toAmountPost-toAmountPre)/((fromAmountPre-fromAmountPost)*atomicRate)
            
    def find_nearest_to_atomic(self,atomic,twap,spot,cl):
        rateNames = np.array(['twap','spot','cl'])
        deltas = np.array([abs(atomic/rate-1) for rate in [twap,spot,cl]])
        return rateNames[np.min(deltas) == deltas].item()
    
    def initialize_balances(self):
        #in case of pending transactions
        self.cancel_tx()

        #approve the weth/usdc to be spent on the router
        self.approve(contract=self.wethContract,amount=1e12*1e18, contractAddress=self.uniRouter.address)
        self.approve(contract=self.usdcContract,amount=1e12*1e18, contractAddress=self.uniRouter.address)

        usdcBalance = self.get_balance(self.usdcContract)
        if usdcBalance > 0:
            self.swap_uni(fromTokenAddress=self.usdcContract.address, 
                          toTokenAddress=self.wethContract.address, 
                          fromAmount=usdcBalance,
                          fee=3000)
        wethBalance = self.get_balance(self.wethContract)        
        if wethBalance > 0:
            self.weth_to_eth(wethBalance)

    def reset_state(self):
        brownie.chain.reset()

    def connect_brownie(self):

        self.w3 = get_w3(conf=self.conf)

        if brownie.network.is_connected():
            self.disconnect_brownie()

        #connect
        brownie.network.connect('267-fork')
        
        #unlock the pk
        suspenseAddress = Account.from_key(self.conf["pk"]).address
        bAccount.at(suspenseAddress ,force=True)
        
        #unlock the owner
        contract = self.get_snx_contract(contractNameAddress='Issuer')
        ownerAddress = contract.functions.owner().call()
        bAccount.at(ownerAddress,force=True)

                        
    def disconnect_brownie(self):
        brownie.network.disconnect()
                
#%%
if __name__=='__main__':
    self=TestingKit(conf)