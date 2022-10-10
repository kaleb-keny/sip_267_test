from utils.brownie_interactions import BrownieInteractions
from brownie import history
from brownie import accounts as bAccount
from utils.utility import parse_config, setup_post_request
import time
import asyncio
import nest_asyncio
nest_asyncio.apply()

conf = parse_config("config/conf.yaml")
self = BrownieInteractions(conf)
#%%
def test_1():
    
    '''
    - Setting a Direct Integration (DI) account to have 40 bp sETH atomic exchange fees and 10 bp sUSD fees, 
        while standard fees being 10 bp sETH and 5 bp on sUSD
        - When the DI account attempts to trade atomically 100 sUSD to sETH
          - ✅ Then it succeeds and the following take place:
              - 50 bp fees are levied on the trade
        - When the a non-DI account attemps the same trade atomically 100 sUSD to sETH
          - ✅ Then it succeeds and the following take place:
              - 15 bp fees are levied on the trade
    '''
    
    #reset state
    self.brownie_revert()
    
    #Add sETH and sUSD integration
    self.set_integration(targetAddress=bAccount[1].address,
                         currencyKey='sETH',
                         atomicExchangeFeeRate=int(40e14))
    self.set_integration(targetAddress=bAccount[1].address,
                         currencyKey='sUSD',
                         atomicExchangeFeeRate=int(10e14))
    
    #set non-di atomic fees
    self.set_atomic_exchange_fee(currencyKey='sETH', fee=int(40e14))
    self.set_atomic_exchange_fee(currencyKey='sUSD', fee=int(10e14))
    
    #get some susd on di account and standard account
    self.eth_to_susd(bAccount[1],int(5e18))
    self.eth_to_susd(bAccount[2],int(5e18))
        
    #swap sUSD to sETH
    diFee    = self.swap_atomically(fromCurrencyKey='sUSD', toCurrencyKey='sETH', fromAmount=int(100e18), account=bAccount[1])
    nonDiFee = self.swap_atomically(fromCurrencyKey='sUSD', toCurrencyKey='sETH', fromAmount=int(100e18), account=bAccount[2])
    
    assert self.is_close(diFee, 50e-4), "atomicFee for DI not achieved"
    assert self.is_close(nonDiFee, 15e-4), "atomicFee for non Di not achieved"
    
def test_2():
    
    '''
    - Setting a Direct Integration (DI) account to have 0 bp sEUR atomic exchange fees and 30 bp sUSD fees, 
        while standard fees being 15 bp sEUR and 5 bp on sUSD
        - When the DI account attempts to trade atomically 100 sUSD to sEUR
          - ✅ Then it succeeds and the following take place:
              - 45 bp fees are levied on the trade, being the DI fees on sUSD and  standard fees on EUR
    '''
    
    #reset state
    self.brownie_init()
    
    #Add sEUR to integration
    self.set_integration(targetAddress=bAccount[1].address,
                         currencyKey='sEUR',
                         atomicExchangeFeeRate=int(0))
    self.set_integration(targetAddress=bAccount[1].address,
                         currencyKey='sUSD',
                         atomicExchangeFeeRate=int(30e14))
    
    #set non-di atomic fees
    self.set_atomic_exchange_fee(currencyKey='sEUR', fee=int(15e14))
    self.set_atomic_exchange_fee(currencyKey='sUSD', fee=int(5e14))
    
    #get some susd on di account and standard account
    self.eth_to_susd(bAccount[1],int(5e18))
    self.eth_to_susd(bAccount[2],int(5e18))
        
    #swap sUSD to sETH
    diFee    = self.swap_atomically(fromCurrencyKey='sUSD', toCurrencyKey='sEUR', fromAmount=int(100e18), account=bAccount[1])
    
    assert self.is_close(diFee, 45e-4), "default fees were not caught"

def test_3():
    
    '''
    - Setting a Direct Integration (DI) `maxAtomicVolumePerBlock` to 2000$ per block on sUSD and 1000$ on sETH while the standard parameters being 100$ on sUSD
        - When a non DI account attempts to trade 101 sUSD to sETH
          - ❌ Then transaction reverts, due to exceeding max volume per block
    '''
    
    #reset state
    self.brownie_revert()
    
    #add integration params
    self.set_integration(targetAddress=self.specialAccounts[0].address,
                         currencyKey='sETH',
                         atomicMaxVolumePerBlock=int(1000e18))
    self.set_integration(targetAddress=self.specialAccounts[0].address,
                         currencyKey='sUSD',
                         atomicMaxVolumePerBlock=int(2000e18))
    
    self.set_atomic_max_volume_per_block(int(100e18))
            
    #get some susd 
    self.eth_to_susd(bAccount[4],int(50e18))
    
    #send sUSD to testing accounts
    self.contracts["susd"].transfer(bAccount[1],int(10000e18),{'from':bAccount[4],'gas_price':'1 gwei'})
    
    try:
        self.swap_atomically('sUSD','sETH',int(101e18),bAccount[1])
    except:
        pass
    assert history[-1].status.value == 0, "max cap did not achive desired affect"


    
def test_4():
    '''
    - Setting a Direct Integration (DI) `maxAtomicVolumePerBlock` to 2000$ per block on sUSD and 1000$ on sETH while the standard parameters being 100$
        - When an DI account attempts to trade 1900 sUSD to sETH and simulatenously in the same block a non-DI account trades 100 sUSD to sETH
          - ✅ Then both transactions succeed
    '''
    
    #reset state
    self.brownie_init()

    #add integration params
    self.set_integration(targetAddress=self.specialAccounts[0].address,
                         currencyKey='sETH',
                         atomicMaxVolumePerBlock=int(1000e18))
    self.set_integration(targetAddress=self.specialAccounts[0].address,
                         currencyKey='sUSD',
                         atomicMaxVolumePerBlock=int(2000e18))
    
    self.set_atomic_max_volume_per_block(int(100e18))
            
    #get some susd 
    self.eth_to_susd(bAccount[4],int(50e18))
    
    #send sUSD to testing accounts
    self.contracts["susd"].transfer(self.specialAccounts[0].address,int(10000e18),{'from':bAccount[4],'gas_price':'1 gwei'})
    self.contracts["susd"].transfer(self.specialAccounts[1].address,int(10000e18),{'from':bAccount[4],'gas_price':'1 gwei'})
    
    #get the test signed transactions
    #note that specialAccount[0] is DI
    txList = []
    txList.append(self.get_atomic_swap_signed_tx(fromCurrencyKey='sUSD', toCurrencyKey='sETH', fromAmount=int(1900e18), account=self.specialAccounts[0]))
    txList.append(self.get_atomic_swap_signed_tx(fromCurrencyKey='sUSD', toCurrencyKey='sETH', fromAmount=int(100e18), account=self.specialAccounts[1]))
        
    #disable automine
    self.w3.provider.make_request("evm_setAutomine",[False])
    self.w3.provider.make_request("evm_setIntervalMining", [5000]);
    
    #send transactions asynchrounously
    loop = asyncio.get_event_loop()
    future = asyncio.ensure_future(setup_post_request(txList,self.conf))
    loop.run_until_complete(future)
    outputList = future.result()
    
    #enable automine
    self.w3.provider.make_request("evm_setIntervalMining", [5]);
    self.w3.provider.make_request("evm_setAutomine",[True])
    
    #wait for tx mining
    time.sleep(30)

    txReceipt1 = self.w3.eth.getTransactionReceipt(outputList[0]["result"])
    txReceipt2 = self.w3.eth.getTransactionReceipt(outputList[1]["result"])
    
    assert txReceipt1["blockNumber"] == txReceipt2["blockNumber"], "txs were not included in the same block"
    assert txReceipt1.status==1 and txReceipt2.status==1, "one of the transactions failed while they should not have"


def test_5():
    '''
    - Setting a Direct Integration (DI) `maxAtomicVolumePerBlock` to 2000$ per block on sUSD and 1000$ on sETH while the standard parameters being 100$
        - When an DI account attempts to trade 2001 sUSD to sETH and simulatenously in the same block a non-DI account trades 100 sUSD to sETH
          - ❌ Then the DI account transaction reverts
          - ✅ Then the non-DI account transaction suceeds
    '''
    
    #reset state
    self.brownie_init()

    #add integration params
    self.set_integration(targetAddress=self.specialAccounts[0].address,
                         currencyKey='sETH',
                         atomicMaxVolumePerBlock=int(1000e18))
    self.set_integration(targetAddress=self.specialAccounts[0].address,
                         currencyKey='sUSD',
                         atomicMaxVolumePerBlock=int(2000e18))
    
    self.set_atomic_max_volume_per_block(int(100e18))
            
    #get some susd 
    self.eth_to_susd(bAccount[4],int(50e18))
    
    #send sUSD to testing accounts
    self.contracts["susd"].transfer(self.specialAccounts[0].address,int(10000e18),{'from':bAccount[4],'gas_price':'1 gwei'})
    self.contracts["susd"].transfer(self.specialAccounts[1].address,int(10000e18),{'from':bAccount[4],'gas_price':'1 gwei'})
    
    #get the test signed transactions
    #note that specialAccount[0] is DI
    txList = []
    txList.append(self.get_atomic_swap_signed_tx(fromCurrencyKey='sUSD', toCurrencyKey='sETH', fromAmount=int(2001e18), account=self.specialAccounts[0]))
    txList.append(self.get_atomic_swap_signed_tx(fromCurrencyKey='sUSD', toCurrencyKey='sETH', fromAmount=int(100e18), account=self.specialAccounts[1]))
        
    #disable automine
    self.w3.provider.make_request("evm_setAutomine",[False])
    self.w3.provider.make_request("evm_setIntervalMining", [5000]);
    
    #send transactions asynchrounously
    loop = asyncio.get_event_loop()
    future = asyncio.ensure_future(setup_post_request(txList,self.conf))
    loop.run_until_complete(future)
    outputList = future.result()
    
    #enable automine
    self.w3.provider.make_request("evm_setIntervalMining", [5]);
    self.w3.provider.make_request("evm_setAutomine",[True])
    
    #wait for tx mining
    time.sleep(30)

    txReceipt1 = self.w3.eth.getTransactionReceipt(outputList[0]["result"])
    txReceipt2 = self.w3.eth.getTransactionReceipt(outputList[1]["result"])
    
    assert txReceipt1["blockNumber"] == txReceipt2["blockNumber"], "txs were not included in the same block"
    assert txReceipt1.status==0 and txReceipt2.status==1, "transaction status incorrect"

def test_6():
    '''
    - Setting a Direct Integration (DI) `maxAtomicVolumePerBlock` to 2000$ per block on sUSD and 1000$ on sETH while the standard parameters being 100$
        - When an DI account attempts to trade 2000 sUSD to sETH and simulatenously in the same block a DI account trades 1000 sETH to sUSD
          - ✅ Then the DI sUSD to sETH trades suceeds
          - ❌ Then the DI sETH to sUSD trade reverts
    '''
    
    #reset state
    self.brownie_init()

    #add integration params
    self.set_integration(targetAddress=self.specialAccounts[0].address,
                         currencyKey='sETH',
                         atomicMaxVolumePerBlock=int(1000e18))
    self.set_integration(targetAddress=self.specialAccounts[0].address,
                         currencyKey='sUSD',
                         atomicMaxVolumePerBlock=int(2000e18))
    
    self.set_atomic_max_volume_per_block(int(100e18))
            
    #get some susd 
    self.eth_to_susd(bAccount[4],int(50e18))
    
    #send sUSD to testing accounts
    self.contracts["susd"].transfer(self.specialAccounts[0].address,int(10000e18),{'from':bAccount[4],'gas_price':'1 gwei'})
    
    #get the test signed transactions
    #note that specialAccount[0] is DI
    atomicPrice,linkPrice = self.get_atomic_link_price(fromCurrencyKey='sETH', toCurrencyKey='sUSD')
    txList = []
    txList.append(self.get_atomic_swap_signed_tx(fromCurrencyKey='sUSD', toCurrencyKey='sETH', fromAmount=int(2000e18), account=self.specialAccounts[0]))
    txList.append(self.get_atomic_swap_signed_tx(fromCurrencyKey='sETH', toCurrencyKey='sUSD', fromAmount=int(100e18/atomicPrice), account=self.specialAccounts[0],incrementNonce=1))
        
    #disable automine
    self.w3.provider.make_request("evm_setAutomine",[False])
    self.w3.provider.make_request("evm_setIntervalMining", [5000]);
    
    #send transactions asynchrounously
    loop = asyncio.get_event_loop()
    future = asyncio.ensure_future(setup_post_request(txList,self.conf))
    loop.run_until_complete(future)
    outputList = future.result()
    
    #enable automine
    self.w3.provider.make_request("evm_setIntervalMining", [5]);
    self.w3.provider.make_request("evm_setAutomine",[True])
    
    #wait for tx mining
    time.sleep(30)

    txReceipt1 = self.w3.eth.getTransactionReceipt(outputList[0]["result"])
    txReceipt2 = self.w3.eth.getTransactionReceipt(outputList[1]["result"])
    
    assert txReceipt1["blockNumber"] == txReceipt2["blockNumber"], "txs were not included in the same block"
    assert txReceipt1.status==1 and txReceipt2.status==0, "transaction status incorrect"

def test_7():
    '''
    - Setting a Direct Integration (DI) `maxAtomicVolumePerBlock` to 2000$ per block on sUSD and 1000$ on sETH while the standard parameters being 100$
        - When an DI account attempts to trade 750 sUSD to sETH and simulatenously in the same block a DI account trades 249$ worth of sETH to sUSD
          - ✅ Then both transactions succeed
    '''
    
    #reset state
    self.brownie_init()

    #add integration params
    self.set_integration(targetAddress=self.specialAccounts[0].address,
                         currencyKey='sETH',
                         atomicMaxVolumePerBlock=int(1000e18))
    self.set_integration(targetAddress=self.specialAccounts[0].address,
                         currencyKey='sUSD',
                         atomicMaxVolumePerBlock=int(2000e18))
    
    self.set_atomic_max_volume_per_block(int(100e18))
            
    #get some susd 
    self.eth_to_susd(bAccount[4],int(50e18))
    
    #send sUSD to testing accounts
    self.contracts["susd"].transfer(self.specialAccounts[0].address,int(10000e18),{'from':bAccount[4],'gas_price':'1 gwei'})
    
    #get the test signed transactions
    #note that specialAccount[0] is DI
    atomicPrice,linkPrice = self.get_atomic_link_price(fromCurrencyKey='sETH', toCurrencyKey='sUSD')
    txList = []
    txList.append(self.get_atomic_swap_signed_tx(fromCurrencyKey='sUSD', toCurrencyKey='sETH', fromAmount=int(750e18), account=self.specialAccounts[0]))
    txList.append(self.get_atomic_swap_signed_tx(fromCurrencyKey='sETH', toCurrencyKey='sUSD', fromAmount=int(249e18/atomicPrice), account=self.specialAccounts[0],incrementNonce=1))
        
    #disable automine
    self.w3.provider.make_request("evm_setAutomine",[False])
    self.w3.provider.make_request("evm_setIntervalMining", [5000]);
    
    #send transactions asynchrounously
    loop = asyncio.get_event_loop()
    future = asyncio.ensure_future(setup_post_request(txList,self.conf))
    loop.run_until_complete(future)
    outputList = future.result()
    
    #enable automine
    self.w3.provider.make_request("evm_setIntervalMining", [5]);
    self.w3.provider.make_request("evm_setAutomine",[True])
    
    #wait for tx mining
    time.sleep(30)

    txReceipt1 = self.w3.eth.getTransactionReceipt(outputList[0]["result"])
    txReceipt2 = self.w3.eth.getTransactionReceipt(outputList[1]["result"])
    
    assert txReceipt1["blockNumber"] == txReceipt2["blockNumber"], "txs were not included in the same block"
    assert txReceipt1.status==1 and txReceipt2.status==1, "transaction status incorrect"    

def test_8():
    '''
    - Setting the DI account to route through 30 bp uni pools while the non-DI accounts routes through 5 bp pools
        - When the DI account trades atomically
            - ✅ Then the tx suceeds and the trade is routed through 30 bp uni pool
        - When a non-DI account trades atomically
            - ✅ Then the tx suceeds and the trade is routed through the 5 bp uni pool
    '''
    
    #reset state
    self.brownie_revert()
    
    #Add sETH and sUSD integration
    self.set_integration(targetAddress=bAccount[1].address,
                         currencyKey='sETH',
                         dexPriceAggregator=self.conf["contracts"]["dexPriceAggregator"])
    self.set_integration(targetAddress=bAccount[1].address,
                         currencyKey='sUSD',
                         dexPriceAggregator=self.conf["contracts"]["dexPriceAggregator"])
        
    #get some susd on di account and standard account
    self.eth_to_susd(bAccount[4],int(50e18))
    
    #swap sUSD to sETH
    self.swap_atomically(fromCurrencyKey='sUSD', toCurrencyKey='sETH', fromAmount=self.balance_of('susd', bAccount[4]), account=bAccount[4])

    #send sETH to testing accounts
    self.contracts["seth"].transfer(bAccount[1].address,int(15e18),{'from':bAccount[4],'gas_price':'1 gwei'})
    self.contracts["seth"].transfer(bAccount[2].address,int(15e18),{'from':bAccount[4],'gas_price':'1 gwei'})
                
    #set dex price standard dex price aggregator to 5 bp pools
    #on USDC/wETH
    self.contracts["dex_agg"].setPoolForRoute(self.contracts["usdc"].address,
                                              self.contracts["weth"].address,
                                              '0x88e6A0c2dDD26FEEb64F039a2c41296FcB3f5640',
                                              {'from':bAccount[-1],'max_fee':int(1e9),'priority_fee':int(1e9)})

    self.contracts["dex_agg_mock"].setPoolForRoute(self.contracts["usdc"].address,
                                                   self.contracts["weth"].address,
                                                   '0x8ad599c3A0ff1De082011EFDDc58f1908eb6e6D8',
                                                   {'from':bAccount[-1],'max_fee':int(1e9),'priority_fee':int(1e9)})
        
    #push the 5 bp pool ETH/USD price down a bit (to distinguish 30 pool from 5 pool prices)
    #first swap ETH to wETH
    self.eth_to_weth(account=bAccount[0], amount=int(500e18))

    #swap weth to usdc on the 5 bp pool / market manipulation
    self.swap_uni(account=bAccount[0], 
                  fromToken='weth', 
                  toToken='usdc', 
                  fromAmount=int(500e18), 
                  fee=500)

    #fetch prices
    spot5, twap5 = self.get_uni_prices(ticker='eth', poolFeeBp=5, twap=60*30)
    spot30, twap30 = self.get_uni_prices(ticker='eth', poolFeeBp=30, twap=60*30)
    
    assert not self.is_close(spot5, spot30,3), "manipulation failed"
        
    #swap sUSD to sETH
    _        = self.swap_atomically(fromCurrencyKey='sETH', toCurrencyKey='sUSD', fromAmount=int(10e18), account=bAccount[1])
    nonDiFee = self.swap_atomically(fromCurrencyKey='sETH', toCurrencyKey='sUSD', fromAmount=int(10e18), account=bAccount[2])
    
    #get the fee adjusted fill price on the fee, note that nonDiFee, is used, as test
    #does not manipulate fees    
    diPrice = self.balance_of('susd', account=bAccount[1])/10e18/(1-nonDiFee)
    nonDiPrice = self.balance_of('susd', account=bAccount[2])/10e18/(1-nonDiFee)
    
    #get the chainlink price
    _, linkPrice = self.get_atomic_link_price(fromCurrencyKey='sETH', toCurrencyKey='sUSD')
    
    assert self.is_close(nonDiPrice, spot5,3), "manipulated spot 5 price was not used"
    assert not self.is_close(diPrice, spot5,3), "manipulated spot 5 price was used"
    assert self.is_close(diPrice, min(spot30,linkPrice,twap30),3), "spot 30 or link price was not used"
    
