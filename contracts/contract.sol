pragma solidity >=0.7.0 <0.9.0;
// SPDX-License-Identifier: MIT

contract Pedersen {
    //uint public q =  21888242871839275222246405745257275088548364400416034343698204186575808495617;
    int public q = 21888242871839275222246405745257275088696311157297823662689037894645226208583;
    int public gX = 19823850254741169819033785099293761935467223354323761392354670518001715552183;
    int public gY = 15097907474011103550430959168661954736283086276546887690628027914974507414020;
    int public hX = 3184834430741071145030522771540763108892281233703148152311693391954704539228;
    int public hY = 1405615944858121891163559530323310827496899969303520166098610312148921359100;

    constructor(int _q, int _gX, int _gY, int _hX, int _hY ) { // Добавлено изменение значений простых чисел
        q = _q;
        gX = _gX;
        gY = _gY;
        hX = _hX;
        hY = _hY;
    }

    function Commit(int b, int r) public returns (int cX, int cY) {
        (int cX1, int cY1) = ecMul(b, gX, gY);
        (int cX2, int cY2) = ecMul(r, hX, hY);
        return(ecAdd(cX1, cY1, cX2, cY2));
    }
    function Verify(int b, int r, int cX, int cY) public returns (bool) {
        (int cX2, int cY2) = Commit(b,r);
        return cX == cX2 && cY == cY2;
    }
    function CommitDelta(int cX1, int cY1, int cX2, int cY2) public returns (int cX, int cY) {
        (cX, cY) = ecAdd(cX1, cY1, cX2, q-cY2);
    }
    function ecMul(int b, int cX1, int cY1) private returns (int cX2, int cY2) {
        bool success = false;
        bytes memory input = new bytes(96);
        bytes memory output = new bytes(64);
        assembly {
            mstore(add(input, 32), cX1)
            mstore(add(input, 64), cY1)
            mstore(add(input, 96), b)
            success := call(gas(), 7, 0, add(input, 32), 96, add(output, 32), 64)
            cX2 := mload(add(output, 32))
            cY2 := mload(add(output, 64))
        }
        require(success);
    }
    function ecAdd(int cX1, int cY1, int cX2, int cY2) public returns (int cX3, int cY3) {
        bool success = false;
        bytes memory input = new bytes(128);
        bytes memory output = new bytes(64);
        assembly {
            mstore(add(input, 32), cX1)
            mstore(add(input, 64), cY1)
            mstore(add(input, 96), cX2)
            mstore(add(input, 128), cY2)
            success := call(gas(), 6, 0, add(input, 32), 128, add(output, 32), 64)
            cX3 := mload(add(output, 32))
            cY3 := mload(add(output, 64))
        }
        require(success);
    }
}

contract AuctionsBox{
    address public admin;
    address[] public opened_auctions;
    constructor () {
        admin = msg.sender;
    }

    function getAll() external view returns(address[] memory)  {
        return(opened_auctions);
    }

    function addAuction(address addr) public {
        BlindAuction auction_addr = BlindAuction(addr);
        require(msg.sender == admin || msg.sender == auction_addr.auctioneerAddress());
        opened_auctions.push(addr);
    }


    function closeAuction(uint idx) public {
        require(msg.sender == admin || msg.sender == BlindAuction(opened_auctions[idx]).auctioneerAddress());
        delete opened_auctions[idx];
    }

}


contract BlindAuction {
    enum VerificationStates {Init, Challenge,ChallengeDelta, Verify, VerifyDelta, ValidWinner}
    struct Bidder {
        int commitX;
        int commitY;
        bytes cipher;
        bool validProofs;
        bool paidBack;
        bool existing;
    }
    Pedersen pedersen;
    bool withdrawLock;
    VerificationStates public states;
    address private challengedBidder;
    uint private challengeBlockNumber;
    bool private testing; //for fast testing without checking block intervals
    uint8 private K = 10; //number of multiple rounds per ZKP
    int public Q = 21888242871839275222246405745257275088696311157297823662689037894645226208583;
    int public V = 5472060717959818805561601436314318772174077789324455915672259473661306552145;
    int[] commits;
    mapping(address => Bidder) public bidders;
    address[] public indexs;
    uint mask =1;
    //Auction Parameters
    address public auctioneerAddress;
    uint    public bidBlockNumber;
    uint    public revealBlockNumber;
    uint    public winnerPaymentBlockNumber;
    uint    public maxBiddersCount;
    uint    public fairnessFees;
    uint    public maxBid;
    //these values are set when the auctioneer determines the winner
    address public winner;
    uint public highestBid;

    // Рандомное число для ZKP
    uint8 public number_zkp = 221;


    // Как это работает:
    // 1. Создается аукцион, в параметрах которого задается:
    //     1.1 Комиссия за участие (_fairnessFees)
    //     1.2 Номер блока до окончания периода ставок
    //     1.3 Создается instance схемы Педерсена
    //     1.4 Максимальное число участников (maxBiddersCount)
    //     1.5 Задается число раундов ZKP (переменная K)
    //     1.6 Параметр тестирования (testing)

    // 2. Желающий сделать ставку вычисляет следующиее значения:
    //     2.1 Берет свою стаку x (в wei) и рандомной число r в Поле q
    //     Вычисляет значение: С = x*G + r*H --> значения cX (commitX) и cY (commitY) в структуре бидера
    //     передаются в смарт-контракт посредством функции Bid, тем самым ставка фиксируется

    // 3. Доказывающий фиксирует ставку путем функции ZKPCommit:

    //     Commit
    //     Для 1 раунда:

    //     Генерирует w1 c [0,B]
    //     Высчитывает w2 = w1 - B,
    //
    //     Вычисляет   W1 = w1*G + r1*H, r1 - рандомное в поле q
    //                 W2 = w2*G + r2*H, r2 - рандомное в поле q

    //     И передает в функцию ZKPCommit:
    //          [коорд x точки W1, коорд y точки W1, коорд x точки W2, коорд y точки W2, ......]
    //
    //     Вся информация пушится в массив commits вида [коорд x точки W1, коорд y точки W1, коорд x точки W2, коорд y точки W2, ......] для каждого док-ва

    // 4. ZKP
    // Из прошлой функции доказывающий узнает в каком блоке была замайнена транзакция
    // Высчитвает оттуда значение uint(block.blockhash(номер_блока_когда_была_замайнена_транзакция))

    // Берет оттуда 10 LSB (для нашего случая) и в зависимости от бита вычисляет и передает функции ZKPVerify

    //     (структура response)
    //     4.1 if b = 0, то передает [w1, r1, w2, r2]
    //     if b = 1, то передает [m, n, z], где  m = x+wz, n = r+rz и само число z для выбора какую нужно компоненту



    //Constructor = Setting all Parameters and auctioneerAddress as well
    constructor(uint _maxBid, uint _bidBlockNumber, uint _revealBlockNumber,
    uint _winnerPaymentBlockNumber, uint _maxBiddersCount,
    uint _fairnessFees,
    address pedersenAddress, uint8 k, bool _testing) payable {
        require(msg.value >= _fairnessFees);
        require(_maxBid>=_fairnessFees);
        maxBid = _maxBid;
        auctioneerAddress = msg.sender;
        bidBlockNumber = block.number + _bidBlockNumber;
        revealBlockNumber = bidBlockNumber + _revealBlockNumber;
        winnerPaymentBlockNumber = revealBlockNumber + _winnerPaymentBlockNumber;
        maxBiddersCount = _maxBiddersCount;
        fairnessFees = _fairnessFees;
        pedersen = Pedersen(pedersenAddress);
        K= k;
        testing = _testing;
    }

    function getPedersenAddr() public returns(address) {
        return(address(pedersen));
    }
    function Bid(int cX, int cY) public payable {
        require(block.number < bidBlockNumber || testing);   //during bidding Interval
        require(indexs.length < maxBiddersCount); //available slot
        require(msg.value >= fairnessFees);  //paying fees
        require(bidders[msg.sender].existing == false);
        bidders[msg.sender] = Bidder(cX, cY,"", false, false,true);
        indexs.push(msg.sender);
    }
    function Reveal(bytes memory cipher) public {
        require(block.number < revealBlockNumber && block.number > bidBlockNumber || testing);
        require(bidders[msg.sender].existing ==true); //existing bidder
        bidders[msg.sender].cipher = cipher;
    }

    function ZKPCommit(address y, int[] memory _commits) public challengeByAuctioneer {
        require(states == VerificationStates.Challenge || testing);
        require(_commits.length == K *4);
        require(bidders[y].existing == true); // existing bidder
        challengedBidder = y;
        challengeBlockNumber = block.number;
        for(uint i=0; i< _commits.length; i++)
            if(commits.length == i) {
                commits.push(_commits[i]);
            } else {
                commits[i] = _commits[i];
            }
        states = VerificationStates.Verify;
    }

    function get_bit(uint8 _number, uint8 _k) pure internal returns(uint8) {
        return (_number >> _k) & 1;
    }

    function ZKPVerify(int[] memory response) public challengeByAuctioneer {
        require(states == VerificationStates.Verify || states == VerificationStates.VerifyDelta);
        uint8 count = 0;
        //uint hash = uint(block.blockhash(challengeBlockNumber));
        // mask = 1;
        uint i = 0;
        uint j = 0;
        int cX;
        int cY;
        uint8 b;
        // Для рассчета бит
        uint8 bits_count = 0;
        while(i<response.length && j<commits.length) {
            b = 0;

            // b = 0
            if(b == 0) {
                // структура response = [w1, r1, w2, r2]
                // структура commits = [коорд x точки W1, коорд y точки W1, коорд x точки W2, коорд y точки W2]
                require((response[i] + response[i+2])%Q==V, "(response[i] + response[i+2])%Q==V");
                require(pedersen.Verify(response[i], response[i+1], commits[j], commits[j+1]), "Failed Verification stage for w1,r1 and commited W1 dot");
                require(pedersen.Verify(response[i+2], response[i+3], commits[j+2], commits[j+3]), "Failed Verification stage for w2,r2 and commited W2 dot");
                i+=4;
            } else {
                // b = 1

                // структура response = [m, n, z]
                if(response[i+2] ==1) //z=1

                // ecAdd(uint cX1, uint cY1, uint cX2, uint cY2)
                    (cX, cY) = pedersen.ecAdd(bidders[challengedBidder].commitX, bidders[challengedBidder].commitY, commits[j], commits[j+1]);
                else
                    (cX, cY) = pedersen.ecAdd(bidders[challengedBidder].commitX, bidders[challengedBidder].commitY, commits[j+2], commits[j+3]);
                // Рассчитали новые координаты cX и cY и переходим к верификации
                require(pedersen.Verify(response[i], response[i+1], cX, cY));
                i+=3;
            }
            j+=4;
            //mask = mask <<1;
            count++;
            bits_count++;
        }
        require(count==K);

        // count =0;
        // i =0;
        // j=0;
        // while(i<deltaResponses.length && j<deltaCommits.length) {

        //     if(hash&mask == 0) {
        //         require((deltaResponses[i] + deltaResponses[i+2])%Q==V);
        //         require(pedersen.Verify(deltaResponses[i], deltaResponses[i+1], deltaCommits[j], deltaCommits[j+1]));
        //         require(pedersen.Verify(deltaResponses[i+2], deltaResponses[i+3], deltaCommits[j+2], deltaCommits[j+3]));
        //         i+=4;
        //     } else {
        //     (cX, cY) = pedersen.CommitDelta(bidders[winner].commitX, bidders[winner].commitY, bidders[challengedBidder].commitX, bidders[challengedBidder].commitY);
        //     if(deltaResponses[i+2]==1)
        //         (cX, cY) = pedersen.ecAdd(cX,cY, deltaCommits[j], deltaCommits[j+1]);
        //     else
        //         (cX, cY) = pedersen.ecAdd(cX,cY, deltaCommits[j+2], deltaCommits[j+3]);
        //     require(pedersen.Verify(deltaResponses[i],deltaResponses[i+1],cX,cY));
        //     i+=3;
        //     }
        //     j+=4;
        //     mask = mask <<1;
        //     count++;
        // }
        // require(count==K);

        bidders[challengedBidder].validProofs = true;

        // states = VerificationStates.Challenge;
    }
    function VerifyAll() public challengeByAuctioneer {
        for (uint i = 0; i<indexs.length; i++)
                if(indexs[i] != winner)
                    if(!bidders[indexs[i]].validProofs) {
                        winner = address(0);
                        revert();
                    }

        states = VerificationStates.ValidWinner;
    }


    function ClaimWinner(address _winner, uint _bid, uint _r) public challengeByAuctioneer {
        require(states == VerificationStates.Init);
        require(bidders[_winner].existing == true); //existing bidder
        require(_bid < uint(V)); //valid bid
        require(pedersen.Verify(int(_bid), int(_r), bidders[_winner].commitX, bidders[_winner].commitY)); //valid open of winner's commit
        winner = _winner;
        highestBid = _bid;
        states = VerificationStates.Challenge;
    }


    function Withdraw() public payable {
        require(states == VerificationStates.ValidWinner || block.number>winnerPaymentBlockNumber);
        require(msg.sender != winner);
        require(bidders[msg.sender].paidBack == false && bidders[msg.sender].existing == true);
        require(withdrawLock == false);
        withdrawLock = true;
        payable(msg.sender).transfer(fairnessFees);
        bidders[msg.sender].paidBack = true;
        withdrawLock = false;
    }
    function WinnerPay() public payable {
        require(states == VerificationStates.ValidWinner);
        require(msg.sender == winner);
        require(msg.value >= highestBid - fairnessFees);
    }
    function Destroy() public {
        selfdestruct(payable(auctioneerAddress));
    }
    modifier challengeByAuctioneer() {
        require(msg.sender == auctioneerAddress); //by auctioneer only
        require(block.number > revealBlockNumber && block.number < winnerPaymentBlockNumber || testing); //after reveal and before winner payment
        _;
    }
}