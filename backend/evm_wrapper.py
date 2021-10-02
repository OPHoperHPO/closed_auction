from typing import List

import web3
import eth_account
from pathlib import Path
from .crypto import PyPedersen
from solcx import compile_source, install_solc

install_solc(version="latest")


class BaseContractWrapper:
    def __init__(self, rpc_address: str, contract_file: Path, contract_name: str):
        self.web3 = web3.Web3(web3.HTTPProvider(rpc_address))
        self.contract_name = contract_name
        self.abi, self.bytecode = self.compile_contract(contract_file)
        self.contact_address = None
        self.rpc_address = rpc_address
        self.contract_file = contract_file

    def compile_contract(self, sol_file: Path):
        """Compiles solidity contract."""
        if isinstance(sol_file, str):
            with open(sol_file) as f:
                src = f.read()
        elif isinstance(sol_file, Path):
            src = sol_file.read_text()
        else:
            raise NotImplemented("Unknown type of input sol filepath")
        compiled_sol = compile_source(src, optimize=True, allow_paths=[Path("./")])
        contract = compiled_sol[f'<stdin>:{self.contract_name}']
        bytecode = contract['bin']
        abi = contract['abi']
        return abi, bytecode

    def get_contract_by_address(self, contract_address):
        contract = self.web3.eth.contract(address=contract_address,
                                          abi=self.abi)
        return contract


class Pedersen(BaseContractWrapper):
    def __init__(self, rpc_address: str, contract_file: Path):
        super().__init__(rpc_address, contract_file, "Pedersen")

    def deploy(self,
               deploy_account: eth_account.account.LocalAccount,
               gas=4712388,
               gas_price=100000000000,
               q: int = 21888242871839275222246405745257275088696311157297823662689037894645226208583,
               gX: int = 19823850254741169819033785099293761935467223354323761392354670518001715552183,
               gY: int = 15097907474011103550430959168661954736283086276546887690628027914974507414020,
               hX: int = 3184834430741071145030522771540763108892281233703148152311693391954704539228,
               hY: int = 1405615944858121891163559530323310827496899969303520166098610312148921359100,
               ) -> str:
        """Deploys contract to blockchain from specific account"""
        contract = self.web3.eth.contract(abi=self.abi, bytecode=self.bytecode)
        tx_hash = contract.constructor(q,
                                       gX,
                                       gY,
                                       hX,
                                       hY).buildTransaction(
            {
                'gas': gas,
                'gasPrice': gas_price,
                'from': deploy_account.address,
                'nonce': self.web3.eth.get_transaction_count(deploy_account.address, "pending")
            })
        signed_txn = self.web3.eth.account.signTransaction(tx_hash, private_key=deploy_account.privateKey)
        contract_hash = self.web3.eth.sendRawTransaction(signed_txn.rawTransaction)
        contract_tx_info = self.web3.eth.wait_for_transaction_receipt(contract_hash)
        contract_address = contract_tx_info["contractAddress"]
        self.contact_address = contract_address
        return contract_address

    @property
    def q(self) -> int:
        contract = self.get_contract_by_address(self.contact_address)
        return contract.functions.q().call()

    @property
    def gX(self) -> int:
        contract = self.get_contract_by_address(self.contact_address)
        return contract.functions.gX().call()

    @property
    def gY(self) -> int:
        contract = self.get_contract_by_address(self.contact_address)
        return contract.functions.gY().call()

    @property
    def hX(self) -> int:
        contract = self.get_contract_by_address(self.contact_address)
        return contract.functions.hX().call()

    @property
    def hY(self) -> int:
        contract = self.get_contract_by_address(self.contact_address)
        return contract.functions.hY().call()

    def commit(self, b: int, r: int):
        contract = self.get_contract_by_address(self.contact_address)
        return contract.functions.Commit(b, r).call()

    def verify(self, b: int, r: int, cX: int, cY: int):
        contract = self.get_contract_by_address(self.contact_address)
        return contract.functions.Verify(b, r, cX, cY).call()

    def commitDelta(self, cX1: int, cY1: int, cX2: int, cY2: int):
        contract = self.get_contract_by_address(self.contact_address)
        return contract.functions.Verify(cX1, cY1, cX2, cY2).call()

    def ecMul(self, b: int, cX1: int, cY1: int):
        contract = self.get_contract_by_address(self.contact_address)
        return contract.functions.ecMul(b, cX1, cY1).call()

    def ecAdd(self, cX1: int, cY1: int, cX2: int, cY2: int):
        contract = self.get_contract_by_address(self.contact_address)
        return contract.functions.ecMul(cX1, cY1, cX2, cY2).call()


class BlindAuction(BaseContractWrapper):
    def __init__(self, rpc_address: str, contract_file: Path):
        super().__init__(rpc_address, contract_file, "BlindAuction")

    def deploy(self,
               maxBid: int,
               bidBlockNumber: int,
               revealBlockNumber: int,
               winnerPaymentBlockNumber: int,
               maxBiddersCount: int,
               fairnessFees: int,
               pedersenAddress: str,
               k: int,
               testing: bool,
               eth_pay_value: int,
               deploy_account: eth_account.account.LocalAccount,
               gas=4712388,
               gas_price=100000000000) -> str:
        """Deploys contract to blockchain from specific account"""
        contract = self.web3.eth.contract(abi=self.abi, bytecode=self.bytecode)
        tx_hash = contract.constructor(maxBid,
                                       bidBlockNumber,
                                       revealBlockNumber,
                                       winnerPaymentBlockNumber,
                                       maxBiddersCount,
                                       fairnessFees,
                                       pedersenAddress,
                                       k,
                                       testing).buildTransaction(
            {
                'gas': gas,
                'gasPrice': gas_price,
                'from': deploy_account.address,
                'nonce': self.web3.eth.get_transaction_count(deploy_account.address, "pending"),
                "value": eth_pay_value
            })
        signed_txn = self.web3.eth.account.signTransaction(tx_hash, private_key=deploy_account.privateKey)
        contract_hash = self.web3.eth.sendRawTransaction(signed_txn.rawTransaction)
        contract_tx_info = self.web3.eth.wait_for_transaction_receipt(contract_hash)
        contract_address = contract_tx_info["contractAddress"]
        self.contact_address = contract_address
        return contract_address

    @property
    def number_zkp(self):
        contract = self.get_contract_by_address(self.contact_address)
        return contract.functions.number_zkp().call()

    @property
    def max_bid(self):
        contract = self.get_contract_by_address(self.contact_address)
        return contract.functions.maxBid().call()

    @property
    def states(self):
        contract = self.get_contract_by_address(self.contact_address)
        state = contract.functions.states().call()
        states = ["Init", "Challenge", "ChallengeDelta", "Verify", "VerifyDelta", "ValidWinner"]
        return states[state]

    @property
    def is_withdraw_lock(self):
        contract = self.get_contract_by_address(self.contact_address)
        return contract.functions.withdrawLock().call()

    @property
    def auctioneer_address(self):
        contract = self.get_contract_by_address(self.contact_address)
        return contract.functions.auctioneerAddress().call()

    @property
    def bid_block_number(self):
        contract = self.get_contract_by_address(self.contact_address)
        return contract.functions.bidBlockNumber().call()

    @property
    def reveal_block_number(self):
        contract = self.get_contract_by_address(self.contact_address)
        return contract.functions.revealBlockNumber().call()

    @property
    def winner_payment_block_number(self):
        contract = self.get_contract_by_address(self.contact_address)
        return contract.functions.winnerPaymentBlockNumber().call()

    @property
    def max_bidders_count(self):
        contract = self.get_contract_by_address(self.contact_address)
        return contract.functions.maxBiddersCount().call()

    @property
    def fairness_fees(self):
        contract = self.get_contract_by_address(self.contact_address)
        return contract.functions.fairnessFees().call()

    @property
    def winner(self):
        contract = self.get_contract_by_address(self.contact_address)
        return contract.functions.winner().call()

    @property
    def pedersen(self) -> PyPedersen:
        contract = self.get_contract_by_address(self.contact_address)
        ped = Pedersen(self.rpc_address, self.contract_file)
        ped.contact_address = contract.functions.getPedersenAddr().call()
        return PyPedersen(ped.q, ped.gX, ped.gY, ped.hX, ped.hY)

    @property
    def highest_bid(self):
        contract = self.get_contract_by_address(self.contact_address)
        return contract.functions.highestBid().call()

    def bid(self, cX: int, cY: int, bid_amount_wei: int,
            account: eth_account.account.LocalAccount,
            gas=4712388,
            gas_price=100000000000):
        contract = self.get_contract_by_address(self.contact_address)
        transaction = contract.functions.Bid(
            cX, cY
        ).buildTransaction({
            'gas': gas,
            'gasPrice': gas_price,
            'from': account.address,
            'nonce': self.web3.eth.get_transaction_count(account.address),
            "value": bid_amount_wei
        })
        signed_txn = self.web3.eth.account.signTransaction(transaction,
                                                           private_key=account.privateKey)
        return self.web3.eth.wait_for_transaction_receipt(self.web3.eth.sendRawTransaction(signed_txn.rawTransaction))

    def reveal(self, cipher: bytes,
               account: eth_account.account.LocalAccount,
               gas=4712388,
               gas_price=100000000000):
        contract = self.get_contract_by_address(self.contact_address)
        transaction = contract.functions.Reveal(
            cipher
        ).buildTransaction({
            'gas': gas,
            'gasPrice': gas_price,
            'from': account.address,
            'nonce': self.web3.eth.get_transaction_count(account.address),
        })
        signed_txn = self.web3.eth.account.signTransaction(transaction,
                                                           private_key=account.privateKey)
        return self.web3.eth.wait_for_transaction_receipt(self.web3.eth.sendRawTransaction(signed_txn.rawTransaction))

    def zkp_commit(self, y: str,
                   commits: List[int],
                   account: eth_account.account.LocalAccount,
                   gas=4712388,
                   gas_price=100000000000):
        contract = self.get_contract_by_address(self.contact_address)
        transaction = contract.functions.ZKPCommit(
            y, commits
        ).buildTransaction({
            'gas': gas,
            'gasPrice': gas_price,
            'from': account.address,
            'nonce': self.web3.eth.get_transaction_count(account.address),
        })
        signed_txn = self.web3.eth.account.signTransaction(transaction,
                                                           private_key=account.privateKey)
        return self.web3.eth.wait_for_transaction_receipt(self.web3.eth.sendRawTransaction(signed_txn.rawTransaction))

    def zkp_verify(self,
                   response: List[int],
                   account: eth_account.account.LocalAccount,
                   gas=4712388,
                   gas_price=100000000000):
        contract = self.get_contract_by_address(self.contact_address)
        transaction = contract.functions.ZKPVerify(
            response
        ).buildTransaction({
            'gas': gas,
            'gasPrice': gas_price,
            'from': account.address,
            'nonce': self.web3.eth.get_transaction_count(account.address),
        })
        signed_txn = self.web3.eth.account.signTransaction(transaction,
                                                           private_key=account.privateKey)
        return self.web3.eth.wait_for_transaction_receipt(self.web3.eth.sendRawTransaction(signed_txn.rawTransaction))

    def verify_all(self,
                   account: eth_account.account.LocalAccount,
                   gas=4712388,
                   gas_price=100000000000):
        contract = self.get_contract_by_address(self.contact_address)
        transaction = contract.functions.VerifyAll(
        ).buildTransaction({
            'gas': gas,
            'gasPrice': gas_price,
            'from': account.address,
            'nonce': self.web3.eth.get_transaction_count(account.address),
        })
        signed_txn = self.web3.eth.account.signTransaction(transaction,
                                                           private_key=account.privateKey)
        return self.web3.eth.wait_for_transaction_receipt(self.web3.eth.sendRawTransaction(signed_txn.rawTransaction))

    def claim_winner(self,
                     winner: str,
                     bid: int,
                     r: int,
                     account: eth_account.account.LocalAccount,
                     gas=4712388,
                     gas_price=100000000000):
        contract = self.get_contract_by_address(self.contact_address)
        transaction = contract.functions.ClaimWinner(
            winner, bid, r
        ).buildTransaction({
            'gas': gas,
            'gasPrice': gas_price,
            'from': account.address,
            'nonce': self.web3.eth.get_transaction_count(account.address),
        })
        signed_txn = self.web3.eth.account.signTransaction(transaction,
                                                           private_key=account.privateKey)
        return self.web3.eth.wait_for_transaction_receipt(self.web3.eth.sendRawTransaction(signed_txn.rawTransaction))

    def withdraw(self, account: eth_account.account.LocalAccount,
                 gas=4712388,
                 gas_price=100000000000):
        contract = self.get_contract_by_address(self.contact_address)
        transaction = contract.functions.Withdraw(
        ).buildTransaction({
            'gas': gas,
            'gasPrice': gas_price,
            'from': account.address,
            'nonce': self.web3.eth.get_transaction_count(account.address),
            'value': 1
        })
        signed_txn = self.web3.eth.account.signTransaction(transaction,
                                                           private_key=account.privateKey)
        return self.web3.eth.wait_for_transaction_receipt(self.web3.eth.sendRawTransaction(signed_txn.rawTransaction))

    def winner_pay(self, account: eth_account.account.LocalAccount,
                   gas=4712388,
                   gas_price=100000000000):
        contract = self.get_contract_by_address(self.contact_address)
        transaction = contract.functions.WinnerPay(
        ).buildTransaction({
            'gas': gas,
            'gasPrice': gas_price,
            'from': account.address,
            'nonce': self.web3.eth.get_transaction_count(account.address),
            'value': 1
        })
        signed_txn = self.web3.eth.account.signTransaction(transaction,
                                                           private_key=account.privateKey)
        return self.web3.eth.wait_for_transaction_receipt(self.web3.eth.sendRawTransaction(signed_txn.rawTransaction))

    def destroy(self, account: eth_account.account.LocalAccount,
                gas=4712388,
                gas_price=100000000000):
        contract = self.get_contract_by_address(self.contact_address)
        transaction = contract.functions.Destroy(
        ).buildTransaction({
            'gas': gas,
            'gasPrice': gas_price,
            'from': account.address,
            'nonce': self.web3.eth.get_transaction_count(account.address),
        })
        signed_txn = self.web3.eth.account.signTransaction(transaction,
                                                           private_key=account.privateKey)
        return self.web3.eth.wait_for_transaction_receipt(self.web3.eth.sendRawTransaction(signed_txn.rawTransaction))