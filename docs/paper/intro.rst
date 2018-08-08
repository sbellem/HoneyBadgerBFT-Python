.. _intro:

************
INTRODUCTION
************

.. contents::
    :local:

Distributed fault tolerant protocols are promising solutions for
mission-critical infrastructure, such as financial transaction databases.
Traditionally, they have been deployed at relatively small
scale, and typically in a single administrative domain where adversarial
attacks might not be a primary concern. As a representative example, a
deployment of Google’s fault tolerant lock service, Chubby
:cite:`Burrows:2006:CLS:1298455.1298487`, consists of five nodes, and
tolerates up to two crash faults.

In recent years, a new embodiment of distributed systems called
"cryptocurrencies" or "blockchains" have emerged, beginning with
Bitcoin’s phenomenal success :cite:`Nakamoto:2008`. Such cryptocurrency
systems represent a surprising and effective breakthrough
:cite:`Bonneau:2015:SRP:2867539.2867708`, and open a new chapter in our
understanding of distributed systems.

Cryptocurrency systems challenge our traditional belief about the
deployment environment for fault tolerance protocols. Unlike the
classic "5 Chubby nodes within Google" environment, cryptocurrencies
have revealed and stimulated a new demand for consensus protocols over
a wide area network, among a large number of nodes that are mutually
distrustful, and moreover, network connections can be much more
unpredictable than the classical LAN setting, or even adversarial. This
new setting poses interesting new challenges, and calls upon us to rethink
the design of fault tolerant protocols.

**Robustness is a first-class citizen.** Cryptocurrencies demonstrate the
demand for and viability of an unusual operating point that prioritizes
robustness above all else, even at the expense of performance. In fact,
Bitcoin provides terrible performance by distributed systems standards: a
transaction takes on average 10 minutes to be committed, and the system as a
whole achieves throughput on the order of 10 transactions per second. However,
in comparison with traditional fault tolerant deployment scenarios,
cryptocurrencies thrive in a highly adversarial environment, where
well-motivated and malicious attacks are expected (if not commonplace). For
this reason, many of Bitcoin’s enthusiastic supporters refer to it as the
"Honey Badger of Money" :cite:`McMillan`. We note that the demand for
robustness is often closely related to the demand for *decentralization* --
since decentralization would typically require the participation of a large
number of diverse participants in a wide-area network.

**Favor throughput over latency.** Most existing works on scalable fault
tolerance protocols
:cite:`Aublin:2013:RRB:2549695.2549742,Singh:2008:BPU:1387589.1387603` focus
on optimizing scalability in
a LAN environment controlled by a single administrative domain. Since
bandwidth provisioning is ample, these works often focus on reducing
(cryptographic) computations and minimizing response time while under
contention (i.e., requests competing for the same object). In contrast,
blockchains have stirred interest in a class of financial applications where
response time and contention are not the most critical factors, e.g., payment
and settlement networks :cite:`Visa:2015`. In fact, some financial
applications intentionally introduce delays in committing transactions to
allow for possible rollback/chargeback operations.

Although these applications are not latency critical, banks and financial
institutions have expressed interest in a *high-throughput* alternative of
the blockchain technology, to be able to sustain high volumes of requests.
For example, the Visa processes 2,000 tx/sec on average, with a peak of
59,000 tx/sec :cite:`Visa:2015`.

Our Contributions
=================
**Timing assumptions considered harmful.** Most existing Byzantine fault
tolerant (BFT) systems, even those called "robust," assume some variation of
weak synchrony, where, roughly speaking, messages are guaranteed to be
delivered after a certain bound :math:`\delta`, but :math:`\delta` may be
time-varying or unknown to the protocol designer. We argue that protocols
based on timing assumptions are unsuitable for decentralized, cryptocurrency
settings, where network links can be unreliable, network speeds change
rapidly, and network delays may even be adversarially induced.

First, the liveness properties of weakly synchronous protocols can fail
completely when the expected timing assumptions are violated (e.g., due to a
malicious network adversary). To demonstrate this, we explicitly construct an
adversarial "intermittently synchronous" network that violates the
assumptions, such that existing weakly synchronous protocols such as PBFT
:cite:`Castro:1999:PBF:296806.296824` would grind to a halt
(:ref:`Section 3 <async-vs-wsync>`).

Second, even when the weak synchrony assumptions are satisfied in practice,
weakly synchronous protocols degrade significantly in throughput when the
underlying network is unpredictable. Ideally, we would like a protocol whose
throughput closely tracks the network’s performance even under rapidly
changing network conditions. Unfortunately, weakly asynchronous protocols
require timeout parameters that are finicky to tune, especially in
cryptocurrency application settings; and when the chosen timeout values are
either too long or too short, throughput can be hampered. As a concrete
example, we show that even when the weak synchrony assumptions are satisfied,
such protocols are slow to recover from transient network partitions
(:ref:`Section 3 <async-vs-wsync>`).

**Practical asynchronous BFT.** We propose HoneyBadgerBFT, the first BFT
*atomic broadcast* protocol to provide *optimal asymptotic efficiency* in
the asynchronous setting. We therefore directly refute the prevailing wisdom
that such protocols are [#t0]_ necessarily impractical.

We make significant efficiency improvements on the best prior-known
asynchronous atomic broadcast protocol, due to Cachin et al.
:cite:`Cachin:2001:SEA:646766.704283`, which requires each node to transmit
:math:`\mathcal{O}(N^2)` bits for each committed transaction, substantially
limiting its throughput for all but the smallest networks. This inefficiency
has two root causes. The first cause is redundant work among the parties.
However, a naïve attempt to eliminate the redundancy compromises the fairness
property, and allows for targeted censorship attacks. We invent a novel
solution to overcome this problem by using threshold public-key encryption to
prevent these attacks. The second cause is the use of a suboptimal
instantiation of the Asynchronous Common Subset (ACS) subcomponent. We show
how to efficiently instantiate ACS by combining existing but overlooked
techniques: efficient reliable broadcast using erasure codes
:cite:`1541196`, and a reduction from ACS to reliable broadcast from the
multi-party computation literature :cite:`Ben-Or:1994:ASC:197917.198088`.

HoneyBadgerBFT’s design is optimized for a cryptocurrency-like deployment
scenario where network bandwidth is the scarce resource, but computation is
relatively ample. This allows us to take advantage of cryptographic building
blocks (in particular, threshold public-key encryption) that would be
considered too expensive in a classical fault-tolerant database setting where
the primary goal is to minimize response time even under contention.

In an asynchronous network, messages are eventually delivered but no other
timing assumption is made. Unlike existing weakly synchronous protocols where
parameter tuning can be finicky, HoneyBadgerBFT does not care. Regardless of
how network conditions fluctuate, HoneyBadgerBFT’s throughput always closely
tracks the network’s available bandwidth. Imprecisely speaking,
HoneyBadgerBFT eventually makes progress as long as messages eventually get
delivered; moreover, it makes progress as soon as messages are delivered.

We formally prove the security and liveness of our HoneyBadgerBFT protocol,
and show experimentally that it provides better throughput than the classical
PBFT protocol :cite:`Castro:1999:PBF:296806.296824` even in the optimistic
case.

**Implementation and large-scale experiments.**
We provide a full-fledged implementation of HoneyBadgerBFT, which we will [#t1]_
release as free open source software in the near future. [#f1]_ We demonstrate
experimental results from an Amazon AWS deployment with more than 100 nodes
distributed across 5 continents. To demonstrate its versatility and
robustness, we also deployed HoneyBadgerBFT over the Tor anonymous relay
network *without changing any parameters*, and present throughput and latency
results.


Suggested Deployment Scenarios
==============================
Among numerous conceivable applications, we highlight two likely deployment
scenarios that are sought after by banks, financial institutions, and
advocates for fully decentralized cryptocurrencies.

**Confederation cryptocurrencies.** The success of decentralized
cryptocurrencies such as Bitcoin has inspired banks and financial
institutions to inspect their transaction processing and settlement
infrastructure with a new light. "Confederation cryptocurrency" is an
oft-cited vision
:cite:`10.1007/978-3-662-53357-4_8,DBLP:journals/corr/DanezisM15,ripple:2014`,
where a conglomerate of financial institutions jointly contribute to a
Byzantine agreement protocol to allow fast and robust settlement of
transactions. Passions are running high that this approach will streamline
today’s slow and clunky infrastructure for inter-bank settlement. As a result,
several new open source projects aim to build a suitable BFT protocol for this
setting, such as IBM’s Open Blockchain and the Hyperledger project
:cite:`McMillan`.

A confederation cryptocurrency would require a BFT protocol deployed over the
wide-area network, possibly involving hundreds to thousands of consensus
nodes. In this setting, enrollment can easily be controlled, such that the set
of consensus nodes are known *a priori* - often referred to as the
"permissioned" blockchain. Clearly HoneyBadgerBFT is a natural candidate for
use in such confederation cryptocurrencies.

**Applicability to permissionless blockchains.** By contrast, decentralized
cryptocurrencies such as Bitcoin and Ethereum opt for a "permissionless"
blockchain, where enrollment is open to anyone, and nodes may join and leave
dynamically and frequently. To achieve security in this setting, known
consensus protocols rely on proofs-of-work to defeat Sybil attacks, and pay
an enormous price in terms of throughput and latency, e.g., Bitcoin commits
transactions every ~10 min, and its throughput limited by 7 tx/sec even when
the current block size is maximized.


Several recent works have suggested the promising idea of leveraging either a
slower, external blockchain such as Bitcoin or economic "proof-of-stake"
assumptions involving the underlying currency itself
:cite:`DBLP:journals/corr/Kokoris-KogiasJ16,Kwon:2014,cryptoeprint:2015:1168`

.. todo:: Original refs are: [32, 32, 35, 37] -- figure out what the duplicate
	32 is supposed to be.

to bootstrap faster BFT protocols, by selecting a random committee
to perform BFT in every different epoch. These approaches promise
to achieve the best of both worlds, security in an open enrollment,
decentralized network, and the throughput and response time matching
classical BFT protocols. Here too HoneyBadgerBFT is a natural
choice since the randomly selected committee can be geographically
heterogeneous.


.. rubric:: Footnotes

.. [#f1] https://github.com/amiller/HoneyBadgerBFT

.. rubric:: Footnotes for typos in conf. paper.

.. [#t0] "a re" --> "are"
.. [#t1] will we --> we will
