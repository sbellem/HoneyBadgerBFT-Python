***************************
THE HoneyBadgerBFT PROTOCOL
***************************
In this section we present HoneyBadgerBFT, the first asynchronous
atomic broadcast protocol to achieve optimal asymptotic efficiency.

.. contents::
	:local:

Problem Definition: Atomic Broadcast
====================================
We first define our network model and the atomic broadcast problem. Our
setting involves a network of :math:`N` designated nodes, with distinct
well-known identities (:math:`\mathcal{P}_0` through
:math:`\mathcal{P}_{N−1}`). The nodes receive transactions as input, and their
goal is to reach common agreement on an ordering of these transactions. Our
model particularly matches the deployment scenario of a
"permissioned blockchain" where transactions can be submitted by arbitrary
clients, but the nodes responsible for carrying out the protocol are fixed.

The atomic broadcast primitive allows us to abstract away any
application-specific details, such as how transactions are to be interpreted
(to prevent replay attacks, for example, an application might define a
transaction to include signatures and sequence numbers). For our purposes,
transactions are simply unique strings. In practice, clients would generate
transactions and send them to all of the nodes, and consider them committed
after collecting signatures from a majority of nodes. To simplify our
presentation, we do not explicitly model clients, but rather assume that
transactions are chosen by the adversary and provided as input to the nodes.
Likewise, a transaction is considered committed once it is output by a node.

Our system model makes the following assumptions:

* *(Purely asynchronous network)* We assume each pair of nodes is connected by
  a reliable authenticated point-to-point channel that does not drop
  messages. [#f2]_ The delivery schedule is entirely determined by the
  adversary, but every message sent between correct nodes must eventually be
  delivered. We will be interested in characterizing the running time of
  protocols based on the number of asynchronous rounds (as described in
  :ref:`Section 2 <background-and-related-work>`). As the network may queue
  messages with arbitrary delay, we also assume nodes have unbounded buffers
  and are able to process all the messages they receive.
* *(Static Byzantine faults)* The adversary is given complete control of up to
  :math:`f` faulty nodes, where :math:`f` is a protocol parameter. Note that
  :math:`3f + 1 \leq N` (which our protocol achieves) is the lower bound for
  broadcast protocols in this setting.
* *(Trusted setup)* For ease of presentation, we assume that nodes may
  interact with a trusted dealer during an initial protocol-specific setup
  phase, which we will use to establish public keys and secret shares. *Note
  that in a real deployment, if an actual trusted party is unavailable, then
  a distributed key generation protocol could be used instead (c.f.,
  Boldyreva* [Bol02]_ *)*. All the distributed key generation protocols we
  know of rely on timing assumptions; fortunately these assumptions need only
  to hold during setup.

DEFINITION 1. *An atomic broadcast protocol must satisfy the following
properties, all of which should hold with high probability (as a function*
:math:`1 − \mathsf{negl}(λ)` *of a security parameter,* :math:`λ` *) in an
asynchronous network and in spite of an arbitrary adversary:*

Overview and Intuition
======================

Constructing HoneyBadgerBFT from Asynchronous Common Subset
===========================================================

Instantiating ACS Efficiently
=============================
Cachin et al. present a protocol we call CKPS01 that (implicitly) reduces ACS
to multi-valued validated Byzantine agreement (MVBA) [CKPS01]_. Roughly speaking,
MVBA allows nodes to propose values satisfying a predicate, one of which is
ultimately chosen. The reduction is simple: the validation predicate says that
the output must be a vector of signed inputs from at least :math:`N − f`
parties. Unfortunately, the MVBA primitive agreement becomes a bottleneck,
because the only construction we know of incurs an overhead of
:math:`\mathcal{O}(N^3 |v|)`.

We avoid this bottleneck by using an alternative instantiation of ACS that
sidesteps MVBA entirely. The instantiation we use is due to Ben-Or et al.
[BKR94]_ and has, in our view, been somewhat overlooked. In fact, it predates
CKPS01 [CKPS01]_, and was initially developed for a mostly unrelated purpose
(as a tool for achieving efficient asynchronous multi-party computation
[BKR94]_). This protocol is a reduction from ACS to reliable broadcast (RBC)
and asynchronous binary Byzantine agreement (ABA). Only recently do we know of
efficient constructions for these subcomponents, which we explain shortly.

At a high level, the ACS protocol proceeds in two main phases. In the first
phase, each node P i uses RBC to disseminate its proposed value to the other
nodes, followed by ABA to decide on a bit vector that indicates which RBCs
have successfully completed. We now briefly explain the RBC and ABA
constructions before explaing the Ben-Or protocol in more detail.

We now briefly explain the RBC and ABA constructions before explaing the
Ben-Or protocol in more detail.

**Communication-optimal reliable roadcast.** An asynchronous reliable
broadcast channel satisfies the following properties:

* (*Agreement*) If any two correct nodes deliver :math:`v` and :math:`v_0`,
  then :math:`v = v_0`.
* (*Totality*) If any correct node delivers :math:`v`, then all correct nodes
  deliver :math:`v`
* (*Validity*) If the sender is correct and inputs :math:`v`, then all correct
  nodes deliver :math:`v`

While Bracha’s [Bra87]_ classic reliable broadcast protocol requires
:math:`\mathcal{O}(N^2 |v|)` bits of total communication in order to broadcast
a message of size :math:`|v|`, Cachin and Tessaro [CT01]_ observed that
erasure coding can reduce this cost to merely
:math:`\mathcal{O}(N|v| + λ N^2 \log N)`, even in the worst case. This is a
significant improvement for large messages (i.e., when
:math:`|v| \gg λ N \log N`), which, (looking back to Section 4.3) guides
our choice of batch size. The use of erasure coding here induces at :math:`N`
most a small constant factor of overhead, equal to :math:`\frac{N}{N−2f} \lt 3`.

If the sender is correct, the total running time is three (asynchronous)
rounds; and in any case, at most two rounds elapse between when the first
correct node outputs a value and the last outputs a value. The reliable
broadcast algorithm shown in Figure 2.

**Binary Agreement**. Binary agreement is a standard primitive that allows
nodes to agree on the value of a single bit. More formally, binary agreement
guarantees three properties:

* (*Agreement*) If any correct node outputs the bit :math:`b`, then every
  correct node outputs :math:`b`.
* (*Termination*) If all correct nodes receive input, then every correct
  node outputs a bit.
* (*Validity*) If any correct node outputs :math:`b`, then at least one
  correct node received :math:`b` as input.

The validity property implies *unanimity*: if all of the correct nodes receive
the same input value :math:`b`, then :math:`b` must be the decided value. On
the other hand, if at any point two nodes receive different inputs, then the
adversary may force the decision to either value even before the remaining
nodes receive input.

We instantiate this primitive with a protocol from Moustefaoui et al.
[MMR14]_, which is based on a cryptographic common coin. We defer explanation
of this instantiation to the :ref:`Appendix <appendix>`. Its expected running time is
:math:`\mathcal{O}(1)`, and in fact completes within :math:`\mathcal{O}(k)`
rounds with probability :math:`1 − 2^{-k}`. The communication complexity per
node is :math:`\mathcal{O}(Nλ)`, which is due primarily to threshold
cryptography used in the common coin.


**Agreeing on a subset of proposed values.** Putting the above pieces
together, we use a protocol from Ben-Or et al. [BKR94]_ to agree on a set of
values containing the entire proposals of at least :math:`N − f` nodes. At a
high level, this protocol proceeds in two main phases. In the first phase,
each node :math:`\mathcal{P}_i` uses Reliable Broadcast to disseminate its
proposed value to the other nodes. In the second stage, :math:`N` concurrent
instances of binary Byzantine agreement are used to agree on a bit
vector :math:`\{b_j\}_{j \in [1..N]}`, where :math:`b_j = 1` indicates that
:math:`\mathcal{P}_j`’s proposed value is included in the final set.

Actually the simple description above conceals a subtle challenge, for which
Ben-Or provide a clever solution.
`
A naïve attempt at an implementation of the above sketch would have each node
to wait for the first :math:`(N − f)` broadcasts to complete, and then propose
:math:`1` for the binary agreement instances corresponding to those and
:math:`0` for all the others. However, correct nodes might observe the
broadcasts complete in a different order. Since binary agreement only
guarantees that the output is :math:`1` if all the correct nodes unaninimously
propose :math:`1`, it is possible that the resulting bit vector could be
empty.

To avoid this problem, nodes abstain from proposing :math:`0` until they are
certain that the final vector will have at least :math:`N − f` bits set. To
provide some intuition for the flow of this protocol, we narrate several
possible scenarios in Figure 3. The algorithm from Ben-Or et al. [BKR94]_ is
given in Figure 4. The running time is :math:`\mathcal{O}(\log N)` in
expectation, since it must wait for all binary agreement instances to
finish. [#f4]_ When instantiated with the reliable broadcast and binary
agreement constructions described above, the total communication
complexity is :math:`\mathcal{O}(N^2 |v| + λ N^3 \log N)` assuming :math:`|v|`
is the largest size of any node’s input.




+-------------+---------------+-+---------------+-+---------------+
|             | ``RBC_j``     | |  ``BA_j`` in  | |  ``BA_j`` out | 
+=============+===+===+===+===+=+===+===+===+===+=+===+===+===+===+
| ``pid \ j`` | 0 | 1 | 2 | 3 | | 0 | 1 | 2 | 3 | | 0 | 1 | 2 | 3 |
+-------------+---+---+---+---+-+---+---+---+---+-+---+---+---+---+
| 0           | v | - | v | v | | 1 | 0 | 1 | 1 | | 0 | 0 | 1 | 1 |
+-------------+---+---+---+---+-+---+---+---+---+-+---+---+---+---+
| 1           | - | v | v | v | | 0 | 1 | 1 | 1 | | 0 |   |   |   |
+-------------+---+---+---+---+-+---+---+---+---+-+---+---+---+---+
| 2           | - | v | v | v | | 0 | 1 | 1 | 1 | |   |   |   |   |
+-------------+---+---+---+---+-+---+---+---+---+-+---+---+---+---+
| 3           | v | - | v | v | | 1 | 0 | 1 | 1 | |   |   |   |   |
+-------------+---+---+---+---+-+---+---+---+---+-+---+---+---+---+


Analysis
========







.. rubric:: Footnotes

.. [#f2] Reliable channels can be emulated on top of unreliable channels by
	resending transmissions, at the expense of some efficiency.

.. [#f4] The expected running time can be reduced to :math:`\mathcal{O}(1)`
 	(c.f. [BE03]_) by running several instances in parallel, though this comes
	at the expense of throughput
