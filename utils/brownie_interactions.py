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
from web3.providers.base import JSONBaseProvider
base_provider = JSONBaseProvider()

class BrownieInteractions(SnxContracts,Prices):
    
    def __init__(self,conf):

        self.w3 = get_w3(conf)
        SnxContracts.__init__(self,conf)
        Prices.__init__(self,conf)
        self.conf=conf
        self.brownie_init()
        self.setup_contracts()                
            
    def setup_contracts(self):
        
        self.contracts = {}
        
        wethContract = get_contract(self.conf,'0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2')
        self.contracts['weth'] = bContract.from_abi(name='weth',address=wethContract.address,abi=wethContract.abi)
                
        contract = get_contract(self.conf,'0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48')
        self.contracts['usdc'] = bContract.from_abi(name='usdc',address=contract.address,abi=wethContract.abi)
        
        contract = get_contract(self.conf,'0x68b3465833fb72A70ecDF485E0e4C7bD8665Fc45')
        self.contracts['uni'] = bContract.from_abi(name='uni',address=contract.address,abi=contract.abi)
        
        #setup synthetix contract
        proxyContract = self.get_snx_contract(contractNameAddress="ProxyERC20")
        snxContract   = self.get_snx_contract(contractNameAddress="Synthetix")
        self.contracts['snx'] = bContract.from_abi(name='snx', address=proxyContract.address, abi=snxContract.abi)

        #setup susd contract
        contract = self.get_snx_contract(contractNameAddress="ProxyERC20sUSD",contractNameAbi='ProxyERC20')
        self.contracts['susd'] = bContract.from_abi(name='susd', address=contract.address, abi=contract.abi)

        #setup seth contract
        contract = self.get_snx_contract(contractNameAddress="ProxysETH",contractNameAbi='ProxyERC20')
        self.contracts['seth'] = bContract.from_abi(name='seth', address=contract.address, abi=contract.abi)

        #setup sEUR contract
        contract = self.get_snx_contract(contractNameAddress="ProxysEUR",contractNameAbi='ProxyERC20')
        self.contracts['seur'] = bContract.from_abi(name='seur', address=contract.address, abi=contract.abi)
        
        #setup direct integration contract
        contract = self.get_snx_contract('DirectIntegrationManager')
        self.contracts['integration'] = bContract.from_abi(name='di', address=contract.address, abi=contract.abi)
        
        #setup collateral eth contract
        contract = self.get_snx_contract('CollateralEth')
        self.contracts['collateral_eth'] = bContract.from_abi(name='collateral_eth', address=contract.address, abi=contract.abi)
        
        #setup collateral eth contract
        contract = self.get_snx_contract('ExchangeRates')
        self.contracts['exchange_rates'] = bContract.from_abi(name='exchange_rates', address=contract.address, abi=contract.abi)

        #setup collateral eth contract
        contract = self.get_snx_contract('SystemSettings')
        self.contracts['settings'] = bContract.from_abi(name='settings', address=contract.address, abi=contract.abi)
        
        #dex aggregartors
        contract = get_contract(self.conf,'0xf120F029Ac143633d1942e48aE2Dfa2036C5786c')
        self.contracts['dex_agg'] = bContract.from_abi(name='dex_1',address=contract.address,abi=contract.abi)

        contract = get_contract(self.conf,self.conf["contracts"]["dexPriceAggregator"])
        self.contracts['dex_agg_mock'] = bContract.from_abi(name='dex_1',address=contract.address,abi=contract.abi)
        
        #setup mock aggergator
        address  = self.conf["contracts"]["mockAggregator"]
        contract = get_contract(conf=self.conf,address=address)
        self.contracts["mock"] = bContract.from_abi(name='mock', address=contract.address, abi=contract.abi)        

        #Setup CircuitBreaker
        contract = self.get_snx_contract("CircuitBreaker")
        self.contracts['breaker'] = bContract.from_abi(name='breaker', address=contract.address, abi=contract.abi)        

                            
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
    
    def get_integration(self,diAddress,currencyKey):
        headers = ['currencyKey',
                   'dexPriceAggregator',
                   'atomicEquivalentForDexPricing',
                   'atomicExchangeFeeRate',
                   'atomicTwapWindow',
                   'atomicMaxTwapDelta',
                   'atomicMaxVolumePerBlock',
                   'atomicVolatilityConsiderationWindow',
                   'atomicVolatilityTwapSeconds',
                   'atomicVolatilityUpdateThreshold',
                   'exchangeFeeRate',
                   'exchangeMaxDynamicFee',
                   'exchangeDynamicFeeRounds',
                   'exchangeDynamicFeeThreshold',
                   'exchangeDynamicFeeWeightDecay']        
        currencyKeyHex = self.w3.toHex(text=currencyKey).ljust(66,"0")
        output = self.contracts["integration"].getExchangeParameters(diAddress,currencyKeyHex)
        outputDict = {header: parameter for header, parameter in zip(headers,output)}
        outputDict["currencyKey"] = self.w3.toText(outputDict["currencyKey"]).replace("\x00",'')
        return outputDict
                    
    def set_exchange_fee(self,currencyKey,fee):
        currencyKeyHex = self.w3.toHex(text=currencyKey).ljust(66,"0")
        return self.contracts["settings"].setExchangeFeeRateForSynths([currencyKeyHex],[fee],{'from' : bAccount[-1],'max_fee':int(1e9),'priority_fee':int(1e9)})

    def set_atomic_exchange_fee(self,currencyKey,fee):
        currencyKeyHex = self.w3.toHex(text=currencyKey).ljust(66,"0")
        return self.contracts["settings"].setAtomicExchangeFeeRate(currencyKeyHex,fee,{'from' : bAccount[-1],'max_fee':int(1e9),'priority_fee':int(1e9)})

    def set_atomic_max_volume_per_block(self,maxVolumePerBlock):
        return self.contracts["settings"].setAtomicMaxVolumePerBlock(maxVolumePerBlock,{'from' : bAccount[-1],'max_fee':int(1e9),'priority_fee':int(1e9)})

    def set_atomic_volatility_threshold(self,currencyKey,volatilityThreshold):
        currencyKeyHex = self.w3.toHex(text=currencyKey).ljust(66,"0")
        return self.contracts["settings"].setAtomicVolatilityUpdateThreshold(currencyKeyHex ,volatilityThreshold,{'from' : bAccount[-1],'max_fee':int(1e9),'priority_fee':int(1e9)})

    def set_atomic_consideration_window(self,currencyKey,window):
        currencyKeyHex = self.w3.toHex(text=currencyKey).ljust(66,"0")
        return self.contracts["settings"].setAtomicVolatilityConsiderationWindow(currencyKeyHex,window,{'from' : bAccount[-1],'max_fee':int(1e9),'priority_fee':int(1e9)})
    
    def set_dynamic_parameters(self,rounds=None,threshold=None,decay=None,maxFee=None):
        if not rounds is None:
            self.contracts["settings"].setExchangeDynamicFeeRounds(rounds,{'from' : bAccount[-1],'max_fee':int(1e9),'priority_fee':int(1e9)})
        if not threshold is None:
            self.contracts["settings"].setExchangeDynamicFeeThreshold(threshold,{'from' : bAccount[-1],'max_fee':int(1e9),'priority_fee':int(1e9)})
        if not decay is None:
            self.contracts["settings"].setExchangeDynamicFeeWeightDecay(decay,{'from' : bAccount[-1],'max_fee':int(1e9),'priority_fee':int(1e9)})
        if not maxFee is None:
            self.contracts["settings"].setExchangeMaxDynamicFee(maxFee,{'from' : bAccount[-1],'max_fee':int(1e9),'priority_fee':int(1e9)})
       
    def swap_uni(self,account,fromToken,toToken,fromAmount,fee):        
        #create some random account
        randomAccount = Account.create()        
        #send random some eth
        bAccount[0].transfer(randomAccount.address,'1 ether',gas_price='1 gwei')
                
        #send the tokens to the random account
        self.contracts[fromToken].transfer(randomAccount.address,fromAmount,{'from':account,'max_fee':int(1e9),'priority_fee':int(1e9)})
        
        #have the suspense account approve uni to spend from tokens
        contract = self.w3.eth.contract(address = self.contracts[fromToken].address,
                                        abi = self.contracts[fromToken].abi)
        txPrep = contract.functions.approve(self.contracts["uni"].address,int(fromAmount))
        tx = txPrep.buildTransaction({'chainId': 1,
                                      'gas': int(1e6),
                                      'maxFeePerGas': int(1e9),
                                      'maxPriorityFeePerGas': int(1e9),
                                      'type': 2 ,
                                      'nonce': self.w3.eth.getTransactionCount(randomAccount.address)})
        signedTx = self.w3.eth.account.sign_transaction(tx, randomAccount.key)            
        txHash = self.w3.eth.sendRawTransaction(signedTx.rawTransaction)        
        time.sleep(10)
        txReceipt = self.w3.eth.getTransactionReceipt(txHash)
        assert txReceipt["status"] == 1,"approve failed"

        #swap the tokens on uniswap
        contract = self.w3.eth.contract(address = self.contracts["uni"].address,
                                        abi = self.contracts["uni"].abi)
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
        time.sleep(10)
        txReceipt = self.w3.eth.getTransactionReceipt(txHash)
        assert txReceipt["status"] == 1,"swap failed"
        
        #send the tokens to account
        contract = self.w3.eth.contract(address = self.contracts[toToken].address,
                                        abi = self.contracts[toToken].abi)
        
        txPrep = contract.functions.transfer(account.address,contract.functions.balanceOf(randomAccount.address).call())
        tx = txPrep.buildTransaction({'chainId': 1,
                                      'gas': int(1e6),
                                      'maxFeePerGas': int(1e9),
                                      'maxPriorityFeePerGas': int(1e9),
                                      'type': 2 ,
                                      'nonce': self.w3.eth.getTransactionCount(randomAccount.address)})
        signedTx = self.w3.eth.account.sign_transaction(tx, randomAccount.key)            
        txHash = self.w3.eth.sendRawTransaction(signedTx.rawTransaction)     
        time.sleep(10)
        txReceipt = self.w3.eth.getTransactionReceipt(txHash)
        assert txReceipt["status"] == 1,"sending tokens back to account failed"        
        
    def eth_to_weth(self,account,amount):        
        return self.contracts["weth"].deposit({'value':amount,
                                               'from':account,
                                               'max_fee':int(1e9),
                                               'priority_fee':int(1e9)})
    
    def eth_to_susd(self,account,ethAmount):
        atomicRate, linkRate = self.get_atomic_link_price('sETH','sUSD')
        currencyKeyHex = self.w3.toHex(text='sUSD').ljust(66,"0")
        return self.contracts["collateral_eth"].open(\
                                                     int(ethAmount*linkRate/1.31),\
                                                         currencyKeyHex,\
                                                             {'value':ethAmount,
                                                              'from':account,
                                                              'max_fee':int(1e9),
                                                              'priority_fee':int(1e9)})
    
    def swap_atomically(self,fromCurrencyKey,toCurrencyKey,fromAmount,account):
        fromAmountPre = self.balance_of(fromCurrencyKey.lower(), account)
        toAmountPre   = self.balance_of(toCurrencyKey.lower(), account)        
        atomicRate, linkRate  = self.get_atomic_link_price(fromCurrencyKey=fromCurrencyKey, toCurrencyKey=toCurrencyKey)
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
    
    
    def get_atomic_swap_signed_tx(self,fromCurrencyKey,toCurrencyKey,fromAmount,account,incrementNonce=0):
        fromHex   = Web3.toHex(text=fromCurrencyKey).ljust(66,"0")
        toHex     = Web3.toHex(text=toCurrencyKey).ljust(66,"0")
        snxContract   = self.get_snx_contract(contractNameAddress="Synthetix")
        txPrep = snxContract.functions.exchangeAtomically(fromHex,
                                                          fromAmount,
                                                          toHex,
                                                          '0x0000000000000000000000000000000000000000',
                                                          0)
        
        tx = txPrep.buildTransaction({'chainId': 1,
                                      'gas': int(1e6),
                                      'maxFeePerGas': int(1e9),
                                      'maxPriorityFeePerGas': int(1e9),
                                      'type': 2 ,
                                      'nonce': self.w3.eth.getTransactionCount(account.address)+incrementNonce})
        
        tx = self.w3.eth.account.sign_transaction(tx, account.key)            
        
        return base_provider.encode_rpc_request('eth_sendRawTransaction', [tx.rawTransaction.hex()])
        
    
    def swap_classic(self,fromCurrencyKey,toCurrencyKey,fromAmount,account):
        fromAmountPre = self.balance_of(fromCurrencyKey.lower(), account)
        toAmountPre   = self.balance_of(toCurrencyKey.lower(), account)        
        atomicRate, linkRate = self.get_atomic_link_price(fromCurrencyKey=fromCurrencyKey, toCurrencyKey=toCurrencyKey)
        fromHex   = Web3.toHex(text=fromCurrencyKey).ljust(66,"0")
        toHex     = Web3.toHex(text=toCurrencyKey).ljust(66,"0")
        self.contracts["snx"].exchangeWithTracking(fromHex,
                                                   fromAmount,
                                                   toHex,
                                                   '0x0000000000000000000000000000000000000000',
                                                   '0x0000000000000000000000000000000000000000',
                                                   {'from':account,
                                                    'max_fee':int(1e9),
                                                    'priority_fee':int(1e9)})        
        fromAmountPost = self.balance_of(fromCurrencyKey.lower(), account)
        toAmountPost   = self.balance_of(toCurrencyKey.lower(), account)
        return  1 - (toAmountPost-toAmountPre)/((fromAmountPre-fromAmountPost)*linkRate)
    
    def find_nearest_to_atomic(self,atomic,twap,spot,cl):
        rateNames = np.array(['twap','spot','cl'])
        deltas = np.array([abs(atomic/rate-1) for rate in [twap,spot,cl]])
        return rateNames[np.min(deltas) == deltas].item()
    
    def is_close(self,firstNumber,secondNumber,dof=10):
        return abs(firstNumber/secondNumber-1)<1/10**dof

    def set_oracle_to_mock(self,currencyKey):
        currencyKeyHex = self.w3.toHex(text=currencyKey).ljust(66,"0")
        return self.contracts["exchange_rates"].addAggregator(currencyKeyHex,self.contracts["mock"].address,{'from':bAccount[-1],'gas_price':'1 gwei'})

    def set_mock_price(self,newPrice,timestamp):
        return self.contracts["mock"].setLatestAnswer(newPrice,timestamp,{'from':bAccount[0],'gas_price':'1 gwei'})

    def reset_circuit_breaker(self,address):
        return self.contracts["breaker"].resetLastValue([address],[0],{'from':bAccount[-1],'gas_price':'1 gwei'})

    def brownie_revert(self):
        brownie.chain.revert()

    def brownie_init(self):

        self.w3 = get_w3(conf=self.conf)
        self.specialAccounts = []

        if brownie.network.is_connected():
            self.disconnect_brownie()

        #connect
        brownie.network.connect('267-fork')
        
        #setup few random accounts and fund them
        for x in range(4):
            bAccount.add()
            bAccount[0].transfer(bAccount[x+1],"100 ether",gas_price="1 gwei")
            self.specialAccounts.append(Account.create())
         
        for account in self.specialAccounts:
            bAccount[0].transfer(account.address,"100 ether",gas_price="1 gwei")
                            
        #unlock the owner
        contract = self.get_snx_contract(contractNameAddress='Issuer')
        ownerAddress = contract.functions.owner().call()
        bAccount.at(ownerAddress,force=True)
        brownie.chain.snapshot()

        
    def disconnect_brownie(self):
        brownie.network.disconnect()          