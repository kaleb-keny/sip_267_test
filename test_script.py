from utils.brownie_interactions import BrownieInteractions
from brownie import accounts as bAccount
from utils.utility import parse_config
conf = parse_config("config/conf.yaml")
self = BrownieInteractions(conf)

#%%
def test_1():
    
    '''
    - Setting a Direct Integration (DI) account to have 40 bp sETH atomic exchange fees and 10 bp sUSD fees, while standard fees being 10 bp sETH and 5 bp on sUSD
        - When the DI account attempts to trade atomically 100 sUSD to sETH
          - ✅ Then it succeeds and the following take place:
              - 50 bp fees are levied on the trade
        - When the a non-DI account attemps the same trade atomically 100 sUSD to sETH
          - ✅ Then it succeeds and the following take place:
              - 15 bp fees are levied on the trade
    '''
    
    #reset state
    self.reset_state()
    
    #Add sETH and sUSD integration
    self.set_integration(targetAddress=bAccount[0].address,
                         currencyKey='sETH',
                         atomicExchangeFeeRate=int(40e14))
    self.set_integration(targetAddress=bAccount[0].address,
                         currencyKey='sUSD',
                         atomicExchangeFeeRate=int(10e14))
        
    #get some susd
    self.eth_to_susd(bAccount[0],int(5e18))
    
    #approve spending of sUSD
    self.approve(approver=bAccount[0], 
                 approvee=self.contracts["snx"], 
                 amount=int(1e30), 
                 contractName='susd')
    
    #swap sUSD to sETH
    fee = self.swap_atomically(fromCurrencyKey='sUSD', toCurrencyKey='sETH', fromAmount=int(100e18), account=bAccount[0])
    
    
    
