#################################
The Honey Badger of BFT Protocols
#################################

* Andrew Miller -- University of Illinois, Urbana-Champaign
* Yu Xia -- Tsinghua University
* Kyle Croman -- Cornell University
* Elaine Shi -- Cornell University
* Dawn Song -- University of California, Berkeley

********
ABSTRACT
********

The surprising success of cryptocurrencies has led to a surge of interest
in deploying large scale, highly robust, Byzantine fault tolerant
(BFT) protocols for mission-critical applications, such as financial
transactions. Although the conventional wisdom is to build atop a
(weakly) synchronous protocol such as PBFT (or a variation thereof),
such protocols rely critically on network timing assumptions, and
only guarantee liveness when the network behaves as expected. We
argue these protocols are ill-suited for this deployment scenario.

We present an alternative, HoneyBadgerBFT, the first practical
asynchronous BFT protocol, which guarantees liveness without making
any timing assumptions. We base our solution on a novel atomic
broadcast protocol that achieves optimal asymptotic efficiency. We
present an implementation and experimental results to show our
system can achieve throughput of tens of thousands of transactions
per second, and scales to over a hundred nodes on a wide area network.
We even conduct BFT experiments over Tor, without needing
to tune any parameters. Unlike the alternatives, HoneyBadgerBFT
simply does not care about the underlying network.

.. toctree::
    :maxdepth: 1
    
    intro
    background
    async-vs-wsync
    protocol
    implementation
    conclusion
    refs
    appendix
