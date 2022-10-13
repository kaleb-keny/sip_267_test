# SIP 267 Testing
 Run the tests specified within [SIP-267](https://sips.synthetix.io/sips/sip-267/) with the help of both [brownie](https://eth-brownie.readthedocs.io/en/stable/) and [cannon](https://usecannon.com/) frameworks.

## To Setup

### Create a folder for the Synthetix Contracts
```
mkdir synthetix
cd synthetix
git clone git@github.com:Synthetixio/synthetix.git 
```

### Update env file & Install Package

With `vim .env` update the env file":

```
ETHERSCAN_KEY=XXXXXXXXXXXXXXXXXXXXXXXXX
OVM_ETHERSCAN_KEY=XXXXXXXXXXXXXXXXXXXXXXXXX
PROVIDER_URL=https://eth-mainnet.g.alchemy.com/v2/XXXXXXXXXXXXXXXXXXXXXXXXX
PROVIDER_URL_MAINNET=https://eth-mainnet.g.alchemy.com/v2/XXXXXXXXXXXXXXXXXXXXXXXXX
PROVIDER_URL_KOVAN=https://kovan.infura.io/v3/XXXXXXXXXXXXXXXXXXXXXXXXX
```

Then install the necessary packages

```
npm install
node publish build --clean-build
```
 
### Use Cannon to deploy 267 contracts on a forked mainnet
```
git checkout direct-integration-sip-267
node publish prepare-deploy --network mainnet --use-sips
npx hardhat cannon:build --file cannonfile.release.toml --network mainnet --dry-run network=mainnet --impersonate 0xEb3107117FEAd7de89Cd14D463D340A2E6917769 --fund-signers --port 8545
```

### CREATE FOLDER For the SIP 267 Testing Tools
```
mkdir breaker
cd sip_267_test
git clone git@github.com:kaleb-keny/sip_267_test.git
```

### Run Tests

#### CREATE VIRTUAL ENVIRONMENT
```python3.7 -m venv sip267 ```

#### ACTIVATE VIRTUAL ENVIRONMENT
```source sip267/bin/activate```

#### Create Brownie Test Network
```
brownie networks add Development 267-fork host=http://127.0.0.1 cmd=hardhat-cli chain_id=1  port=8545
```

#### Install Requirements
```pip install -r env/requirements.txt```

#### Run the tests
```pytest test_script.py```

