from pathlib import Path
import random

from backend.evm_wrapper import BlindAuction, Pedersen

rpc = "http://127.0.0.1:8545"

perdesen = Pedersen(rpc_address=rpc,
                    contract_file=Path("contracts/contract.sol"))
auction = BlindAuction(rpc_address=rpc,
                       contract_file=Path("contracts/contract.sol"))

auctioneer_account = perdesen.web3.eth.account.privateKeyToAccount(
    "0x4f3edf983ac636a65a842ce7c78d9aa706d3b113bce9c46f30d7d21715b23b1d")

private_keys = open("keys").read().split("\n")
users_accounts = list(map(perdesen.web3.eth.account.privateKeyToAccount, private_keys))

auction_params = {
    "maxBid": perdesen.web3.toWei(10, "ether"),
    "bidBlockNumber": 0,
    "revealBlockNumber": 0,
    "winnerPaymentBlockNumber": 0,
    "maxBiddersCount": 5,  # Максимальное число участников
    "fairnessFees": 1,  # Комиссия за участие (_fairnessFees)
    "pedersenAddress": "",  # Адрес контракта Pedersen в блокчейне
    "k": 1,  # Количество раундов доказательства
    "testing": True,  # Обход проверки блоков, включает тестовый режим
    "eth_pay_value": 1,  # Сколько заплатить при инициализации аукциона
    "gas": 4712388,
    "gas_price": 100000000000,
}

# Deploy contracts from auctioneer
perdesen.deploy(deploy_account=auctioneer_account)
auction_params["pedersenAddress"] = perdesen.contact_address
auction.deploy(**auction_params, deploy_account=auctioneer_account)


def get_bs(number, w1, w2, r1, r2, r, x):
    return [x + w1, r + r1, 1]


# create bids from users
def create_bid(r, x, value=1000):
    result = []
    for account in users_accounts:
        cX, cY = perdesen.get_dot(x, r)
        auction.bid(cX, cY, value, account)
        w1 = random.randint(0, auction.max_bid / 2)
        w2 = w1 - auction.max_bid
        r1 = random.randint(0, auction.max_bid / 2)
        r2 = random.randint(0, auction.max_bid / 2)
        W1x, W1y = perdesen.get_dot(w1, r1)
        W2x, W2y = perdesen.get_dot(w2, r2)
        result.append([account.address, w1, w2, r1, r2, r, x, W1x, W1y, W2x, W2y])
        value += 2500
    return result


def get_winner(results):
    for res in results:
        acc_addr, w1, w2, r1, r2, r, x, W1x, W1y, W2x, W2y = res
        auction.zkp_commit(acc_addr, [W1x, W1y, W2x, W2y], auctioneer_account)
        auction.zkp_verify(get_bs(  # TODO Something went wrong here
            auction.number_zkp, w1, w2, r1, r2, r, x
        ), auctioneer_account)
    auction.verify_all(auctioneer_account)
    print(f"Winner is {auction.winner}")


get_winner(create_bid(2, 100, 2000))
