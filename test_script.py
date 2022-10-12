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
    self.brownie_init()
    
    #Add sETH and sUSD integration
    self.set_integration(targetAddress=bAccount[1].address,
                         currencyKey='sETH',
                         atomicExchangeFeeRate=int(40e14))
    self.set_integration(targetAddress=bAccount[1].address,
                         currencyKey='sUSD',
                         atomicExchangeFeeRate=int(10e14))
    
    #set non-di atomic fees
    self.set_atomic_exchange_fee(currencyKey='sETH', fee=int(10e14))
    self.set_atomic_exchange_fee(currencyKey='sUSD', fee=int(5e14))
    
    #get some susd on di account and standard account
    self.eth_to_synth(bAccount[1],int(5e18),'sUSD')
    self.eth_to_synth(bAccount[2],int(5e18),'sUSD')
        
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
    self.eth_to_synth(bAccount[1],int(5e18),'sUSD')
    self.eth_to_synth(bAccount[2],int(5e18),'sUSD')
        
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
    self.eth_to_synth(bAccount[4],int(50e18),'sUSD')
    
    #send sUSD to testing accounts
    self.contracts["susd"].transfer(bAccount[1],int(10000e18),{'from':bAccount[4],'gas_price':'1 gwei'})
    
    try:
        self.swap_atomically('sUSD','sETH',int(101e18),bAccount[1])
    except:
        pass
    assert history[-1].status.value == 0, "max cap did not achive desired affect"


def test_4():
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
    self.eth_to_synth(bAccount[4],int(50e18),'sETH')
    

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
    
def test_5():
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
        
    #get some sETH on di account and standard account
    self.eth_to_synth(bAccount[4],int(50e18),'sETH')
    
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
    
def test_6():
    
    '''
    - Setting a Direct Integration (DI) `atomicVolatilityUpdateThreshold` of 10 updates while the standard parameters being 15 updates. The atomicConsiderationWindow being set to 60 seconds.
        - When 10 oracle updates are pushed in the span of few seconds
          - When an DI and an nonDI account attempts to trade 100 sUSD to sETH
            - ✅ Then the non-DI account transaction suceeds
            - ❌ Then the DI account transaction reverts
    '''
    
    #reset state
    self.brownie_revert()
    
    #first save the sETH aggregator address
    aggregatorAddress = self.contracts["exchange_rates"].aggregators(self.w3.toHex(text='sETH').ljust(66,"0"))

    #set atomic volatility threshold on sETH to 3
    self.set_integration(targetAddress=bAccount[1].address,
                         currencyKey='sETH',
                         atomicVolatilityUpdateThreshold=10)
    
    #set non di atomic volatility threshold
    self.set_atomic_volatility_threshold('sETH',15)

    #get some susd on di account and standard account
    self.eth_to_synth(bAccount[1],int(2e18),'sUSD')
    self.eth_to_synth(bAccount[2],int(2e18),'sUSD')
    
    #set consideration window to 30 seconds
    self.set_atomic_consideration_window('sETH',60)
    atomicPrice, linkPrice = self.get_atomic_link_price(fromCurrencyKey='sETH', toCurrencyKey='sUSD')    

    #update to mock
    self.set_oracle_to_mock('sETH')
    
    #update prices 10 times    
    for x in range(10):
        self.set_mock_price(newPrice=int(atomicPrice*1e18), timestamp=int(time.time()+x))
    
    #reset price circuit breaker
    self.reset_circuit_breaker(self.conf["contracts"]["mockAggregator"])
    
    #swap sUSD to sETH
    try:
        self.swap_atomically(fromCurrencyKey='sUSD', toCurrencyKey='sETH', fromAmount=int(1e18), account=bAccount[1])
    except:
        assert history[-1].status==0, "tx did not revert, while it should have"
    finally:
        self.set_oracle_to_chainlink('sETH', aggregatorAddress)
    
    self.swap_atomically(fromCurrencyKey='sUSD', toCurrencyKey='sETH', fromAmount=int(1e18), account=bAccount[2])    

    assert history[-1].status==1, "tx reverted, while it should not have reverted"

def test_7():
    
    '''
    - Setting the base exchange fee on a DI account to 50 bp on sETH and 10 bp on sUSD, while the standard fees are 20 bp and 5 bp
      - Setting the DI and standard `setExchangeDynamicFeeRounds` to 0
          - When the DI account trades with the standard exchange functionality 100 sUSD to sETH
              - ✅ Then the tx suceeds and 60 bp fees are levied
          - When a non-DI account trades with the standard exchange functionality 100 sUSD to sETH
              - ✅ Then the tx suceeds and 25 bp fees are levied
    '''
    
    #reset state
    self.brownie_revert()
    
    #set atomic volatility classic fees
    self.set_integration(targetAddress=bAccount[1].address,
                         currencyKey='sETH',
                         exchangeFeeRate=int(50e14))
    self.set_integration(targetAddress=bAccount[1].address,
                         currencyKey='sUSD',
                         exchangeFeeRate=int(10e14))
    
    #set rounds to zero
    self.set_dynamic_parameters(rounds=0)
    
    #set non di atomic volatility threshold
    self.set_exchange_fee('sETH',int(20e14))
    self.set_exchange_fee('sUSD',int(5e14))

    #get some susd on di account and standard account
    self.eth_to_synth(bAccount[1],int(2e18),'sUSD')
    self.eth_to_synth(bAccount[2],int(2e18),'sUSD')
        
    #swap sUSD to sETH
    diFee    = self.swap_classic(fromCurrencyKey='sUSD', toCurrencyKey='sETH', fromAmount=int(1e18), account=bAccount[1])
    nonDiFee = self.swap_classic(fromCurrencyKey='sUSD', toCurrencyKey='sETH', fromAmount=int(1e18), account=bAccount[2])

    assert self.is_close(diFee, 60e-4), "classic fee for DI not achieved"
    assert self.is_close(nonDiFee, 25e-4), "classic for non Di not achieved"
    
def test_8():
    
    '''
    - Setting the base exchange fee 0 bp on sETH and 0 bp on sUSD
      - Setting the DI dynamic fee parameters as follows
          a) `setExchangeDynamicFeeWeightDecay` to 0.8
          b) `setExchangeDynamicFeeThreshold` to 0.1%
          c) `setExchangeDynamicFeeRounds` to 4
          d) `setExchangeMaxDynamicFee` to 10%
          e) update the ETH price print to 1200$ / 1220$ / 1250$ / 1240$ / 1230$
      - While the standard non DI `setExchangeDynamicFeeRounds` is 0.
          - When the DI account trades with the standard exchange functionality 100 sUSD to sETH
              - ✅ Then the tx suceeds and 4.16% fees are levied
          - When the non-Di accounts trades with the standard exchange function 100 sUSD to sETH
              - ✅ Then the tx suceeds and no fees are levied
    '''
    
    #reset state
    self.brownie_revert()
    
    #first save the sETH aggregator address
    aggregatorAddress = self.contracts["exchange_rates"].aggregators(self.w3.toHex(text='sETH').ljust(66,"0"))

    #set atomic volatility classic fees
    self.set_integration(targetAddress=bAccount[1].address,
                         currencyKey='sETH',
                         exchangeFeeRate=0,
                         exchangeDynamicFeeWeightDecay=int(0.8*1e18),
                         exchangeDynamicFeeThreshold=int(1e15),
                         exchangeDynamicFeeRounds=5,
                         exchangeMaxDynamicFee=int(1e17))
    
    #set rounds to zero
    self.set_dynamic_parameters(rounds=0)

    #set non di atomic volatility threshold
    self.set_exchange_fee('sETH',int(0))
    self.set_exchange_fee('sUSD',int(0))
    self.set_dynamic_parameters(rounds=0)

    #get some susd on di account and standard account
    self.eth_to_synth(bAccount[1],int(2e18),'sUSD')
    self.eth_to_synth(bAccount[2],int(2e18),'sUSD')
                
    #update to mock
    self.set_oracle_to_mock('sETH')
   
    #update prices 10 times    
    self.set_mock_price(newPrice=int(1200*1e18), timestamp=int(time.time()))
    self.set_mock_price(newPrice=int(1220*1e18), timestamp=int(time.time()))
    self.set_mock_price(newPrice=int(1250*1e18), timestamp=int(time.time()+1))
    self.set_mock_price(newPrice=int(1240*1e18), timestamp=int(time.time()+2))
    self.set_mock_price(newPrice=int(1230*1e18), timestamp=int(time.time()+3))
   
    #reset price circuit breaker
    self.reset_circuit_breaker(self.conf["contracts"]["mockAggregator"])

    #swap sUSD to sETH
    self.swap_classic(fromCurrencyKey='sUSD', toCurrencyKey='sETH', fromAmount=int(1e18), account=bAccount[1])
    self.swap_classic(fromCurrencyKey='sUSD', toCurrencyKey='sETH', fromAmount=int(1e18), account=bAccount[2])
    
    #get link price
    atomicPrice,linkPrice = self.get_atomic_link_price(fromCurrencyKey='sETH', toCurrencyKey='sUSD')
    
    diFee    = 1 - self.balance_of('seth', account=bAccount[1]) * linkPrice / 1e18
    nonDiFee = 1 - self.balance_of('seth', account=bAccount[2]) * linkPrice / 1e18

    self.set_oracle_to_chainlink('sETH', aggregatorAddress)

    assert self.is_close(diFee, 3.578355/1e2,5), "dynamic fee did not reach exepcted value"
    assert self.is_close(nonDiFee+0.0000000001, 0.0000000001,4), "dynamic fee was not nullified in standard exchanges"

def test_9():
    
    '''
      - Setting the standard dynamic fee parameters as follows
          a) `setExchangeDynamicFeeWeightDecay` to 0.5
          b) `setExchangeDynamicFeeThreshold` to 0.2%
          c) `setExchangeDynamicFeeRounds` to 4
          d) `setExchangeMaxDynamicFee` to 10%
          e) update the ETH price print to 1200$ / 1220$ / 1250$ / 1240$ / 1230$
      - While the  DI `setExchangeDynamicFeeRounds` is 1.
          - When the non-DI account trades with the standard exchange functionality 100 sUSD to sETH
              - ✅ Then the tx suceeds and 1.65% fees are levied
         - When the Di accounts trades with the standard exchange function 100 sUSD to sETH
              - ✅ Then the tx suceeds and no fees are levied
    '''
    
    #reset state
    self.brownie_revert()
    
    #first save the sETH aggregator address
    aggregatorAddress = self.contracts["exchange_rates"].aggregators(self.w3.toHex(text='sETH').ljust(66,"0"))
    
    #set atomic volatility classic fees
    self.set_integration(targetAddress=bAccount[1].address,
                         currencyKey='sETH',
                         exchangeDynamicFeeRounds=1)
    
    #set standard dyn.........Famic fees
    self.set_dynamic_parameters(threshold=int(2e15),decay=int(0.5*1e18),rounds=5,maxFee=int(5e16))

    #set non di atomic volatility threshold
    self.set_exchange_fee('sETH',int(0))
    self.set_exchange_fee('sUSD',int(0))

    #get some susd on di account and standard account
    self.eth_to_synth(bAccount[1],int(2e18),'sUSD')
    self.eth_to_synth(bAccount[2],int(2e18),'sUSD')
                
    #update to mock
    self.set_oracle_to_mock('sETH')
   
    #update prices 10 times    
    self.set_mock_price(newPrice=int(1200*1e18), timestamp=int(time.time()))
    self.set_mock_price(newPrice=int(1220*1e18), timestamp=int(time.time()))
    self.set_mock_price(newPrice=int(1250*1e18), timestamp=int(time.time()+1))
    self.set_mock_price(newPrice=int(1240*1e18), timestamp=int(time.time()+2))
    self.set_mock_price(newPrice=int(1230*1e18), timestamp=int(time.time()+3))
   
    #reset price circuit breaker
    self.reset_circuit_breaker(self.conf["contracts"]["mockAggregator"])

    #swap sUSD to sETH
    self.swap_classic(fromCurrencyKey='sUSD', toCurrencyKey='sETH', fromAmount=int(1e18), account=bAccount[1])
    self.swap_classic(fromCurrencyKey='sUSD', toCurrencyKey='sETH', fromAmount=int(1e18), account=bAccount[2])
    
    #get link price
    atomicPrice,linkPrice = self.get_atomic_link_price(fromCurrencyKey='sETH', toCurrencyKey='sUSD')
    
    diFee    = 1 - self.balance_of('seth', account=bAccount[1]) * linkPrice / 1e18
    nonDiFee = 1 - self.balance_of('seth', account=bAccount[2]) * linkPrice / 1e18
    
    self.set_oracle_to_chainlink('sETH', aggregatorAddress)

    assert self.is_close(nonDiFee, 1.654539045/1e2,5), "dynamic fee did not reach exepcted value"
    assert self.is_close(diFee+0.0000000001, 0.0000000001,4), "dynamic fee was not nullified in standard exchanges"
    
def test_10():
    '''
    - Setting a Direct Integration (DI) `maxAtomicVolumePerBlock` to 2000$ per block on sUSD and 1000$ on sETH while the standard parameters being 100$
        - When an DI account attempts to trade 50 sUSD to sETH and subsequently in the same block a non-DI account trades 50 sUSD to sETH
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
    self.eth_to_synth(bAccount[4],int(50e18),'sUSD')
    
    #send sUSD to testing accounts
    self.contracts["susd"].transfer(self.specialAccounts[0].address,int(10000e18),{'from':bAccount[4],'gas_price':'1 gwei'})
    self.contracts["susd"].transfer(self.specialAccounts[1].address,int(10000e18),{'from':bAccount[4],'gas_price':'1 gwei'})
    
    #get the test signed transactions
    #note that specialAccount[0] is DI
    txList = []
    txList.append(self.get_atomic_swap_signed_tx(fromCurrencyKey='sUSD', toCurrencyKey='sETH', fromAmount=int(50e18), account=self.specialAccounts[0]))
    txList.append(self.get_atomic_swap_signed_tx(fromCurrencyKey='sUSD', toCurrencyKey='sETH', fromAmount=int(50e18), account=self.specialAccounts[1]))
        
    #disable automine
    self.w3.provider.make_request("evm_setAutomine",[False])
    self.w3.provider.make_request("evm_setIntervalMining", [5000])
    
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


def test_11():
    '''
    - Setting a Direct Integration (DI) `maxAtomicVolumePerBlock` to 2000$ per block on sUSD and 1000$ on sETH while the standard parameters being 100$
        - When an DI account attempts to trade 2000 sUSD to sETH and subsequently in the same block a non-DI account trades 100 sUSD to sETH
          - ✅ Then the DI account transaction suceeds
          - ❌ Then the non-DI account transaction reverts
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
    self.eth_to_synth(bAccount[4],int(50e18),'sUSD')
    
    #send sUSD to testing accounts
    self.contracts["susd"].transfer(self.specialAccounts[0].address,int(10000e18),{'from':bAccount[4],'gas_price':'1 gwei'})
    self.contracts["susd"].transfer(self.specialAccounts[1].address,int(10000e18),{'from':bAccount[4],'gas_price':'1 gwei'})
    
    #get the test signed transactions
    #note that specialAccount[0] is DI
    txList = []
    txList.append(self.get_atomic_swap_signed_tx(fromCurrencyKey='sUSD', toCurrencyKey='sETH', fromAmount=int(2000e18), account=self.specialAccounts[0]))
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
    assert txReceipt1.status==1 and txReceipt2.status==0, "transaction status incorrect"

def test_12():
    '''
    - Setting a Direct Integration (DI) `maxAtomicVolumePerBlock` to 2000$ per block on sUSD and 1000$ on sETH while the standard parameters being 100$
        - When an DI account attempts to trade 2000 sUSD to sETH and subsequently in the same block a DI account trades 1 sETH to sUSD
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
    self.eth_to_synth(bAccount[4],int(50e18),'sUSD')
    
    #send sUSD to testing accounts
    self.contracts["susd"].transfer(self.specialAccounts[0].address,int(10000e18),{'from':bAccount[4],'gas_price':'1 gwei'})
    
    #get the test signed transactions
    #note that specialAccount[0] is DI
    txList = []
    txList.append(self.get_atomic_swap_signed_tx(fromCurrencyKey='sUSD', toCurrencyKey='sETH', fromAmount=int(2000e18), account=self.specialAccounts[0]))
    txList.append(self.get_atomic_swap_signed_tx(fromCurrencyKey='sETH', toCurrencyKey='sUSD', fromAmount=int(1e18), account=self.specialAccounts[0],incrementNonce=1))
        
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