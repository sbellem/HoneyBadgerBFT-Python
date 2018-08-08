.. _background-and-related-work:

***************************
BACKGROUND AND RELATED WORK
***************************

.. contents::
    :local:

Our overall goal is to build a replicated state machine, where clients
generate and submit transactions and a network of nodes receives and
processes them. Abstracting away from application specific details (such
as how to represent state and compute transitions), it suffices to build
a totally globally-consistent, totally-ordered, append-only transaction log.
Traditionally, such a primitive is called *total order* or *atomic broadcast*
:cite:`Cristian85atomicbroadcast:`; in Bitcoin parlance, we would call it a
*blockchain*.

Fault tolerant state machine replication protocols provide strong
safety and liveness guarantees, allowing a distributed system to
provide correct service in spite of network latency and the failure
of some nodes. A vast body of work has studied such protocols,
offering different performance tradeoffs, tolerating different forms
of failures and attacks, and making varying assumptions about the
underlying network. We explain below the most closely related
efforts to ours.

Robust BFT Protocols
====================
While Paxos :cite:`Lamport:1998:PP:279227.279229`, Raft
:cite:`Ongaro:2014:SUC:2643634.2643666`, and many other well-known protocols
tolerate crash faults, Byzantine fault tolerant protocols (BFT),
beginning with PBFT :cite:`Castro:1999:PBF:296806.296824`, tolerate even
arbitrary (e.g., maliciously) corrupted nodes. Many subsequent protocols offer
improved performance, often through *optimistic execution* that provides
excellent performance when there are no faults, clients do not contend much,
and the network is well-behaved, and at least some progress otherwise
:cite:`Abd-El-Malek:2005:FBF:1095809.1095817,Amir:2010:SSB:1729473.1729576,Kotla:2007:ZSB:1323293.1294267,Mao:2008:MBE:1855741.1855767,Veronese:2010:EEB:1909626.1909800`.

In general, BFT systems are evaluated in deployment scenarios where latency
and CPU are the bottleneck :cite:`Singh:2008:BPU:1387589.1387603`, thus the
most effective protocols reduce the number of rounds and minimize expensive
cryptographic operations.

Clement et al. :cite:`Clement:2009:MBF:1558977.1558988` initiated a recent
line of work :cite:`Amir:2011:PBR:1990767.1990952,Aublin:2013:RRB:2549695.2549742,Bessani:2014:SMR:2671853.2672428,Clement:2009:UCS:1629575.1629602,Clement:2009:MBF:1558977.1558988,Veronese:2009:SOW:1637865.1638341`
by advocating improvement of the *worst-case* performance,
providing service quality guarantees even when the system is under
attack -- even if this comes at the expense of performance in the
optimistic case. However, although the "Robust BFT" protocols in
this vein gracefully tolerate compromised nodes, they still rely on
timing assumptions about the underlying network. Our work takes
this approach further, guaranteeing good throughput even in a fully
asynchronous network.

Randomized Agreement
====================
Deterministic asynchronous protocols are impossible for most tasks
:cite:`Fischer:1985:IDC:3149.214121`. While the vast majority of practical BFT
protocols steer clear of this impossibility result by making timing
assumptions, randomness (and, in particular, cryptography) provides an
alternative route. Indeed we know of asynchronous BFT protocols for a variety
of tasks such as binary agreement (ABA), reliable broadcast (RBC), and more
:cite:`Bracha:1987:ABA:36888.36891,Cachin:2001:SEA:646766.704283,Cachin:2000:ROC:343477.343531`

Our work is most closely related to SINTRA
:cite:`Cachin:2002:SIR:647883.738262`, a system implementation based on the
asynchronous atomic broadcast protocol from Cachin et al. (CKPS01)
:cite:`Cachin:2001:SEA:646766.704283`. This protocol consists of a reduction
from atomic broadcast (ABC) to common subset agreement (ACS), as well as a
reduction from ACS to multi-value validated agreement (MVBA).

The key invention we contribute is a novel reduction from ABC to ACS that
provides better efficiency (by an :math:`\mathcal{O}(N)` factor) through
batching, while using threshold encryption to preserve censorship resilience
(see Section 4.4 :ref:`inst-acs-eff`). We also obtain better efficiency by
cherry-picking from the literature improved instantiations of subcomponents.
In particular, we sidestep the expensive MVBA primitive by using an
alternative ACS :cite:`Ben-Or:1994:ASC:197917.198088` along with an efficient
RBC :cite:`1541196` as explained in Section 4.4 :ref:`inst-acs-eff`.

Table 1 summarizes the asymptotic performance of HoneyBadgerBFT with several other
atomic broadcast protocols. Here "Comm. compl." denotes the expected communication
complexity (i.e., total bytes transferred) per committed transaction. Since PBFT relies
on weak synchrony assumptions, it may therefore fail to make progress at all in an
asynchronous network. Protocols KS02 :cite:`Kursawe:2005:OAA:2104063.2104085` and RC05
:cite:`Ramasamy:2005:PAB:2164210.2164223` are optimistic, falling back to an expensive
recovery mode based on MVBA. As mentioned the protocol of Cachin et al. (CKPS01)
:cite:`Cachin:2001:SEA:646766.704283` can be improved using a more efficient ACS
construction :cite:`Ben-Or:1994:ASC:197917.198088,1541196`. We also obtain another
:math:`\mathcal{O}(N)` improvement through our novel reduction.

Finally, King and Saia
:cite:`King:2009:AEE:1813164.1813223,King:2011:BON:1989727.1989732` have recently
developed agreement protocols with less-than-quadratic number of messages by routing
communications over a sparse graph. However, extending these results to the asynchronous
setting remains an open problem.
