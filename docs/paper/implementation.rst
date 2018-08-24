.. _impl-and-eval:

*****************************
IMPLEMENTATION AND EVALUATION
*****************************
In this section we carry out several experiments and performance measurements
using a prototype implementation of the HoneyBadgerBFT protocol. Unless
otherwise noted, numbers reported in this section are by default for the
*optimistic* case where all nodes are behaving honestly.

First we demonstrate that HoneyBadgerBFT is indeed scalable by performing an
experiment in a wide area network, including up to 104 nodes in five
continents. Even under these conditions, HoneyBadgerBFT can reach peak
throughputs of thousands of transactions per second. Furthermore, by a
comparison with PBFT, a representative partially synchronous protocol,
HoneyBadgerBFT performs only a small constant factor worse. Finally, we
demonstrate the feasibility of running asynchronous BFT over the Tor anonymous
communication layer.

**Implementation details.** We developed a prototype implementation of
HoneyBadgerBFT in Python, using the gevent library for concurrent tasks.

For deterministic erasure coding, we use the zfec library :cite:`zooko:2008`,
which implements Reed-Solomon codes. For instantiating the common coin
primitive, we implement Boldyreva's pairing-based threshold signature scheme
:cite:`Boldyreva:2003:TSM:648120.747061`. For threshold encryption of
transactions, we use Baek and Zheng's scheme :cite:`1258486` to encrypt a
256-bit ephemeral key, followed by AES-256 in CBC mode over the actual
payload. We implement these threshold cryptography schemes using the Charm
:cite:`Akinyele2013` Python wrappers for PBC library :cite:`lynn:2007`. For
threshold signatures, we use the provided MNT224 curve, resulting in
signatures (and signature shares) of only 65 bytes, and heuristically
providing 112 bits of security. [#f6]_ Our threshold encryption scheme
requires a symmetric bilinear group: we therefore use the SS512 group, which
heuristically provides 80 bits of security :cite:`nist:2004`. [#f7]_

In our EC2 experiments, we use ordinary (unauthenticated) TCP sockets. In a
real deployment we would use TLS with both client and server authentication,
adding insignificant overhead for long- lived sessions. Similarly, in our Tor
experiment, only one endpoint of each socket is authenticated (via the "hidden
service" address).

Our theoretical model assumes nodes have unbounded buffers. In practice, more
resources could be added dynamically to a node whenever memory consumption
reaches a watermark, (e.g., whenever it is 75% full) though our prototype
implementation does not yet include this feature. Failure to provision an
adequate buffer would count against the failure budget :math:`f`.

Bandwidth Breakdown and Evaluation
==================================
We first analyze the bandwidth costs of our system. In all experiments, we
assume a constant transaction size of :math:`m_{\mathsf{T}} = 250` bytes each,
which would admit an ECDSA signature, two public keys, as well as an
application payload (i.e., approximately the size of a typical Bitcoin
transaction). Our experiments use the parameter :math:`N = 4 f`, [#f8]_ and
each party proposes a batch of :math:`B/N` transactions. To model the worst
case scenario, nodes begin with identical queues of size :math:`B`. We record
the running time as the time from the beginning of the experiment to when the
:math:`(N − f)`-th node outputs a value.

**Bandwidth and breakdown findings.** The overall bandwidth consumed by each
node consists of a fixed additive overhead as well as a transaction dependent
overhead. For all parameter values we considered, the additive overhead is
dominated by an :math:`\mathcal{O}(\lambda N^2)` term resulting from the
threshold cryptography in the :math:`\mathsf{ABA}` phases and the decryption
phase that follows. The :math:`\mathsf{ABA}` phase involves each node
transmitting :math:`4N^2` signature shares in expectation. Only the
:math:`\mathsf{RBC}` phase incurs a transaction-dependent overhead, equal to
the erasure coding expansion factor :math:`r = \frac{N}{N−2f}`. The
:math:`\mathsf{RBC}` phase also contributes :math:`N^2 \log N` hashes to the
overhead because of Merkle tree branches included in the :math:`\mathsf{ECHO}`
messages. The total communication cost (per node) is estimated as:

.. math::

	m_\mathsf{all} = r(Bm_\mathsf{T} + Nm_\mathsf{E}) + N^2((1 +
	\log N)m_\mathsf{H} + m_\mathsf{D} + 4m_\mathsf{S})

where :math:`m_\mathsf{E}` and :math:`m_\mathsf{D}` are respectively the size
of a ciphertext and decryption share in the :math:`\mathsf{TPKE}` scheme, and
:math:`m_\mathsf{S}` is the size of a :math:`\mathsf{TSIG}` signature share.

The system's effective throughput increases as we increase the proposed batch
size :math:`B`, such that the transaction-dependent portion of the cost
dominates. As Figure 5 shows, for :math:`N = 128`, for batch sizes up to 1024
transactions, the transaction-independent bandwidth still dominates to overall
cost. However, when the batch size reaches 16384, the transaction-dependent
portion begins to dominate -- largely resulting from the
:math:`\mathsf{RBC}.\mathtt{ECHO}` stage where nodes transmit erasure-coded
blocks.

Experiments on Amazon EC2
=========================
To see how practical our design is, we deployed our protocol on Amazon EC2
services and comprehensively tested its performance. We ran HoneyBagderBFT on
32, 40, 48, 56, 64, and 104 Amazon EC2 t2.*medium* instances uniformly
distributed throughout its 8 regions spanning 5 continents. In our
experiments, we varied the batch size such that each node proposed 256, 512,
1024, 2048, 4096, 8192, 16384, 32768, 65536, or 131072 transactions.

**Throughput.** Throughput is defined as the number of transactions committed
per unit of time. In our experiment, we use "confirmed transactions per
second" as our measure unit if not specified otherwise. Figure 6 shows the
relationship between throughput and total number of transactions proposed by
all :math:`N` parties. The fault tolerance parameter is set to be :math:`f =
N/4`.

*Findings.* From Figure 6 we can see for each setting, the throughput
increases as the number of proposed transactions increases. We achieve
throughput exceeding 20,000 transactions per second for medium size networks
of up to 40 nodes. For a large 104 node network, we attain more than 1,500
transactions per second. Given an infinite batch size, all network sizes would
eventually converge to a common upper bound, limited only by available
bandwidth. Although the total bandwidth consumed in the network increases
(linearly) with each additional node, the additional nodes also contribute
additional bandwidth capacity.


**Throughput, latency, and scale tradeoffs.** Latency is defined as the time
interval between the time the first node receives a client request and when
the :math:`(N − f)`-th node finishes the consensus protocol. This is
reasonable because the :math:`(N − f)`-th node finishing the protocol implies
the accomplishment of the consensus for the honest parties.

Figure 7 shows the relationship between latency and throughput for different
choices of :math:`N` and :math:`f = N/4`. The positive slopes indicate that
our experiments have not yet fully saturated the available bandwidth, and we
would attain better throughput even with larger batch sizes. Figure 7 also
shows that latency increases as the number of nodes increases, largely
stemming from the :math:`\mathsf{ABA}` phase of the protocol. In fact, at
:math:`N = 104`, for the range of batch sizes we tried, our system is CPU
bound rather than bandwidth bound because our implementation is single
threaded and must verify :math:`\mathcal{O}(N^2)` threshold signatures.
Regardless, our largest experiment with 104 nodes completes in under 6
minutes.

Although more nodes (with equal bandwidth provisioning) could be added to the
network without affecting maximum attainable throughput, the minimal bandwidth
consumed to commit one batch (and therefore the latency) increases with
:math:`\mathcal{O}(N^2 \log N)`. This constraint implies a limit on
scalability, depending on the cost of bandwidth and users' latency tolerance.


**Comparison with PBFT.** Figure 8 shows a comparison with the PBFT protocol,
a classic BFT protocol for partially synchronous networks. We use the Python
implementation from Croman et al. :cite:`10.1007/978-3-662-53357-4_8`, running
on 8, 16, 32, and 64 nodes evenly distributed among Amazon AWS regions. Batch
sizes were chosen to saturate the network's available bandwidth.

Fundamentally, while PBFT and our protocol have the same asymptotic
communication complexity *in total*, our protocol distributes this load evenly
among the network links, whereas PBFT bottlenecks on the leader's available
bandwidth. Thus PBFT's attainable throughput diminishes with the number of
nodes, while HoneyBadgerBFT's remains roughly constant.

Note that this experiment reflects only the optimistic case, with no faults or
network interruptions. Even for small networks, HoneyBadgerBFT provides
significantly better robustness under adversarial conditions as noted in
:ref:`Section 3 <async-vs-wsync>`. In particular, PBFT would achieve **zero
throughput** against an adversarial asynchronous scheduler, whereas
HoneyBadgerBFT would complete epochs at a regular rate.



Experiments over Tor
====================
To demonstrate the robustness of HoneyBadgerBFT, we run the first instance (to
our knowledge) of a fault tolerant consensus protocol carried out over Tor
(the most successful anonymous communication network). Tor adds significant
and varying latency compared to our original AWS deployment. Regardless, we
show that we can run HoneyBadgerBFT without tuning any parameters. Hiding
HoneyBadgerBFT nodes behind the shroud of Tor may offer even better
robustness. Since it helps the nodes to conceal their IP addresses, it can
help them avoid targeted network attacks and attacks involving their physical
location.

**Brief background on Tor.** The Tor network consists of approximately 6,500
relays, which are listed in a public directory service. Tor enables "hidden
services," which are servers that accept connections via Tor in order to
conceal their location. When a client establishes a connection to a hidden
service, both the client and the server construct 3-hop circuits to a common
"rendezvous point." Thus each connection to a hidden service routes data
through 5 randomly chosen relays. Tor provides a means for relay nodes to
advertise their capacity and utilization, and these self-reported metrics are
aggregated by the Tor project. According to these metrics, [#f9]_ the total
capacity of the network is ∼145Gbps, and the current utilization is ∼65Gbps.

**Tor experiment setup.** We design our experiment setup such that we could
run all :math:`N` HoneyBadgerBFT nodes on a single desktop machine running the
Tor daemon software, while being able to realistically reflect Tor relay
paths. To do this, we configured our machine to listen on :math:`N` hidden
services (one hidden service for each HoneyBadgerBFT node in our simulated
network). Since each HoneyBadgerBFT node forms a connection to each other
node, we construct a total of :math:`N^2` Tor circuits per experiment,
beginning and ending with our machine, and passing through 5 random relays.
In summary, all pairwise overlay links traverse real Tor circuits consisting
of *random* relay nodes, designed so that the performance obtained is
representative of a real HoneyBadgerBFT deployment over Tor (despite all
simulated nodes running on a single host machine).

Since Tor provides a critical public service for many users, it is important
to ensure that research experiments conducted on the live network do not
adversely impact it. We formed connections from only a single vantage point
(and thus avoid receiving), and ran experiments of short duration (several
minutes) and with small parameters (only 256 circuits formed in our largest
experiment). In total, our experiments involved the transfer of approximately
five gigabytes of data through Tor -- less than a 1E-5 fraction of its daily
utilization.

Figure 9 shows how latency changes with throughput. In contrast to our EC2
experiment where nodes have ample bandwidth, Tor circuits are limited by the
slowest link in the circuit. We attain a maximum throughput of over 800
transactions per second of Tor.

In general, messages transmitted over Tor's relay network tends to have
significant and highly variable latency. For instance, during our experiment
on 8 parties proposing 16384 transactions per party, a single message can be
delayed for 316.18 seconds and the delay variance is over 2208 while the
average delay is only 12 seconds. We stress that our protocol did not need to
be tuned for such network conditions, as would a traditional eventually-
synchronous protocol.





.. rubric:: Footnotes

.. [#f6] Earlier reports estimate 112 bits of security for the MNT224 curve
    :cite:`nist:2004`; however, recent improvements in computing discrete log
    suggest larger parameters are required [28, 29].

.. [#f7] We justify the relatively weak 80-bit security level for our
    parameters because the secrecy needs are short-lived as the plaintexts
    are revealed after each batch is committed. To defend against
    precomputation attacks, the public parameters and keys should be
    periodically regenerated.

.. [#f8] The setting :math:`N = 4 f` is not the maximum fault tolerance, but
	it is convenient when :math:`f` divides :math:`N`.

.. [#f9] https://metrics.torproject.org/bandwidth.html as of Nov 10, 2015
