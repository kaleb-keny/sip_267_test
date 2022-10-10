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
