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
:math:`\mathcal{P}_{N-1}`). The nodes receive transactions as input, and their
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
  Boldyreva* :cite:`Boldyreva:2003:TSM:648120.747061` *)*. All the distributed key
  generation protocols we know of rely on timing assumptions; fortunately these
  assumptions need only to hold during setup.

DEFINITION 1. *An atomic broadcast protocol must satisfy the following
properties, all of which should hold with high probability (as a function*
:math:`1 - \mathsf{negl}(\lambda)` *of a security parameter,* :math:`\lambda`
*) in an asynchronous network and in spite of an arbitrary adversary:*

* *(Agreement)* If any correct node outputs a transaction :math:`\mathsf{tx}`,
  then every correct node outputs :math:`\mathsf{tx}`.
* *(Total Order)* If one correct node has output the sequence of transactions
  :math:`(\mathsf{tx}_0, \mathsf{tx}_1, \ldots \mathsf{tx}_j)` and another
  has output
  :math:`(\mathsf{tx}^\prime_0, \mathsf{tx}^\prime_1, \ldots \mathsf{tx}^\prime_{j^\prime})`,
  then :math:`\mathsf{tx}_i = \mathsf{tx}^\prime_i \text{ for } i \leq \min(j, j^\prime)`.
* *(Censorship Resilience)* If a transaction :math:`\mathsf{tx}` is input to
  :math:`N - f` correct nodes, then it is eventually output by every correct
  node.

.. todo:: Replace parenthesis by "kets" or whatever they are called.
.. todo:: Use nice lambda like in the paper.

The censorship resilience property is a liveness property that prevents an
adversary from blocking even a single transaction from being committed. This
property has been referred to by other names, for example "fairness" by
Cachin et al. :cite:`Cachin:2001:SEA:646766.704283`, but we prefer this more
descriptive phrase.

**Performance metrics.** We will primarily be interested in analyzing
the *efficiency* and *transaction delay* of our atomic broadcast protocol.

* *(Efficiency)* Assume that the input buffers of each honest node are
  sufficiently full :math:`\Omega(\mathsf{poly}(N, \lambda))`. Then
  *efficiency* is the expected communication cost for each node amortized
  over all committed transactions.

Since each node must output each transaction, :math:`\mathcal{O}(1)`
efficiency (which our protocol achieves) is asymptotically optimal. The above
definition of efficiency assumes the network is *under load*, reflecting our
primary goal: to sustain high throughput while fully utilizing the network’s
available bandwidth. Since we achieve good throughput by batching, our system
uses more bandwidth per committed transaction during periods of low demand
when transactions arrive infrequently. A stronger definition without this
qualification would be appropriate if our goal was to minimize costs (e.g.,
for usage-based billing).

In practice, network links have limited capacity, and if more transactions
are submitted than the network can handle, a guarantee on confirmation time
cannot hold in general. Therefore we define *transaction delay* below
relative to the number of transactions that have been input *ahead* of the
transaction in question. A finite transaction delay implies censorship
resilience.

* *(Transaction delay)* Suppose an adversary passes a transaction
  :math:`\mathsf{tx}` as input to :math:`N - f` correct nodes. Let :math:`T`
  be the "backlog", i.e. the difference between the total number of
  transactions previously input to any correct node and the number of
  transactions that have been committed. Then *transaction delay* is the
  expected number of asynchronous rounds before :math:`\mathsf{tx}` is output
  by every correct node as a function of :math:`T`.


Overview and Intuition
======================
In HoneyBadgerBFT, nodes receive transactions as input and
store them in their (unbounded) buffers. The protocol proceeds
in epochs, where after each epoch, a new batch of transactions is
appended to the committed log. At the beginning of each epoch,
nodes choose a subset of the transactions in their buffer (by a policy
we will define shortly), and provide them as input to an instance
of a randomized agreement protocol. At the end of the agreement
protocol, the final set of transactions for this epoch is chosen.

At this high level, our approach is similar to existing asynchronous atomic
broadcast protocols, and in particular to Cachin et al.
:cite:`Cachin:2001:SEA:646766.704283`, the basis for a large scale transaction
processing system (SINTRA). Like ours, Cachin’s protocol is centered around an
instance of the Asynchronous Common Subset (ACS) primitive. Roughly speaking, the ACS
primitive allows each node to propose a value, and guarantees that every node outputs a
common vector containing the input values of at least :math:`N - 2f` correct nodes. It
is trivial to build atomic broadcast from this primitive - each node simply
proposes a subset of transactions from the front of [#t1]_ its queue,
and outputs the union of the elements in the agreed-upon vector.
However, there are two important challenges.

**Challenge 1: Achieving censorship resilience.** The cost of ACS depends
directly on size of the transaction sets proposed by each node. Since the
output vector contains at least :math:`N - f` such sets, we can therefore
improve the overall efficiency by ensuring that nodes propose *mostly
disjoint* sets of transactions, thus committing more distinct transactions
in one batch for the same cost. Therefore instead of simply choosing the
first element(s) from its buffer (as in :cite:`Cachin:2001:SEA:646766.704283`), each
node in our protocol proposes a randomly chosen sample, such that each transaction is,
on average, proposed by only one node.

However, implemented naïvely, this optimization would compromise censorship
resilience, since the ACS primitive allows the adversary to choose *which*
nodes' proposals are ultimately included. The adversary could selectively
censor a transaction excluding whichever node(s) propose it. We avoid this
pitfall by using threshold encryption, which prevents the adversary from
learning which transactions are proposed by which nodes, until after
agreement is already reached. The full protocol will be described in
:ref:`Section 4.3 <constructing-hbbft-from-acs>`.

**Challenge 2: Practical throughput.** Although the theoretical feasibility
of asynchronous ACS and atomic broadcast have been known
:cite:`Ben-Or:1994:ASC:197917.198088,Cachin:2001:SEA:646766.704283,Cachin:2002:SIR:647883.738262`,
their practical performance is not. To the best of our knowledge, the only other work
that implemented ACS was by Cachin and Portiz :cite:`Cachin:2002:SIR:647883.738262`,
who showed that they could attain a throughput of 0.4
tx/sec over a wide area network. Therefore, an interesting question is
whether such protocols can attain high throughput in practice.

In this paper, we show that by stitching together a carefully chosen array of
sub-components, we can efficiently instantiate ACS and attain much greater
throughput both asymptotically and in practice. Notably, we improve the
asymptotic cost (per node) of ACS from :math:`\mathcal{O}(N^2)` (as in
Cachin et al. :cite:`Cachin:2001:SEA:646766.704283,Cachin:2002:SIR:647883.738262` to
:math:`\mathcal{O}(1)`. Since the
components we cherry-pick have not been presented together before (to our
knowledge), we provide a self-contained description of the whole construction
in :ref:`Section 4.4 <inst-acs-eff>`.

**Modular protocol composition.** We are now ready to present our
constructions formally. Before doing so, we make a remark about the style
of our presentation. We define our protocols in a modular style, where each
protocol may run several instances of other (sub)protocols. The outer
protocol can provide input to and receive output from the subprotocol. A node
may begin executing a (sub)protocol even before providing it input (e.g., if
it receives messages from other nodes).

It is essential to isolate such (sub)protocol instances to ensure that
messages pertaining to one instance cannot be replayed in another. This is
achieved in practice by associating to each (sub)protocol instance a unique
string (a session identifier), tagging any messages sent or received in this
(sub)protocol with this identifier, and routing messages accordingly. We
suppress these message tags in our protocol descriptions for ease of reading.
We use brackets to distinguish between tagged instances of a subprotocol. For
example, :math:`\mathsf{RBC}[i]` denotes an :math:`i^{th}` instance of the
:math:`\mathsf{RBC}` subprotocol.
We implicitly assume that asynchronous communications between parties are over
authenticated asynchronous channels. In reality, such channels could be
instantiated using TLS sockets, for example, as we discuss in
:ref:`Section 5 <impl-and-eval>`.

To distinguish different message types sent between parties within a protocol,
we use a label in :math:`\texttt{typewriter}` font (e.g.,
:math:`\tt{VAL}(m)` indicates a message :math:`m` of type :math:`\tt{VAL}`).


.. _constructing-hbbft-from-acs:

Constructing HoneyBadgerBFT from Asynchronous Common Subset
===========================================================

**Building block: ACS.** Our main building block is a primitive called
asynchronous common subset (ACS). The theoretical feasibility of constructing
ACS has been demonstrated in several works
:cite:`Ben-Or:1994:ASC:197917.198088,Cachin:2001:SEA:646766.704283`. In this
section, we will present the formal definition of ACS and use it as a blackbox
to construct HoneyBadgerBFT. Later in :ref:`Section 4.4 <inst-acs-eff>`, we
will show that by combining several constructions that were somewhat
overlooked in the past, we can instantiate ACS efficiently!

More formally, an ACS protocol satisfies the following properties:

* *(Validity)* If a correct node outputs a set :math:`\mathbf{v}`, then
  :math:`|\mathbf{v}| \geq N - f` and :math:`\mathbf{v}` contains the inputs
  of at least :math:`N - 2 f` correct nodes.
* *(Agreement)* If a correct node outputs :math:`\mathbf{v}`, then every node
  outputs :math:`\mathbf{v}`.
* *(Totality)* If :math:`N - f` correct nodes receive an input, then all
  correct nodes produce an output.

**Building block: threshold encryption.** A *threshold encryption* scheme
:math:`\mathsf{TPKE}` is a cryptographic primitive that allows any party to
encrypt a message to a master public key, such that the network nodes must
work together to decrypt it. Once :math:`f + 1` correct nodes compute and
reveal *decryption shares* for a ciphertext, the plain-text can be recovered;
until at least one correct node reveals its decryption share, the attacker
learns nothing about the plaintext. A threshold scheme provides the following
interface:

**Atomic broadcast from ACS.**


.. _inst-acs-eff:

Instantiating ACS Efficiently
=============================
Cachin et al. present a protocol we call CKPS01 that (implicitly) reduces ACS
to multi-valued validated Byzantine agreement (MVBA) :cite:`Cachin:2001:SEA:646766.704283`. Roughly speaking,
MVBA allows nodes to propose values satisfying a predicate, one of which is
ultimately chosen. The reduction is simple: the validation predicate says that
the output must be a vector of signed inputs from at least :math:`N - f`
parties. Unfortunately, the MVBA primitive agreement becomes a bottleneck,
because the only construction we know of incurs an overhead of
:math:`\mathcal{O}(N^3 |v|)`.

We avoid this bottleneck by using an alternative instantiation of ACS that
sidesteps MVBA entirely. The instantiation we use is due to Ben-Or et al.
:cite:`Ben-Or:1994:ASC:197917.198088` and has, in our view, been somewhat overlooked.
In fact, it predates CKPS01 :cite:`Cachin:2001:SEA:646766.704283`, and was initially developed for a mostly unrelated purpose
(as a tool for achieving efficient asynchronous multi-party computation
:cite:`Ben-Or:1994:ASC:197917.198088`). This protocol is a reduction from ACS to reliable broadcast (RBC)
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

While Bracha’s :cite:`Bracha:1987:ABA:36888.36891` classic reliable broadcast protocol
requires :math:`\mathcal{O}(N^2 |v|)` bits of total communication in order to broadcast
a message of size :math:`|v|`, Cachin and Tessaro :cite:`1541196` observed that
erasure coding can reduce this cost to merely
:math:`\mathcal{O}(N|v| + \lambda N^2 \log N)`, even in the worst case. This
is a significant improvement for large messages (i.e., when
:math:`|v| \gg \lambda N \log N`), which, (looking back to Section 4.3) guides
our choice of batch size. The use of erasure coding here induces at :math:`N`
most a small constant factor of overhead, equal to :math:`\frac{N}{N-2f} \lt 3`.

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
:cite:`Mostefaoui:2014:SAB:2611462.2611468`, which is based on a cryptographic common
coin. We defer explanation of this instantiation to the :ref:`Appendix <appendix>`. Its
expected running time is :math:`\mathcal{O}(1)`, and in fact completes within
:math:`\mathcal{O}(k)` rounds with probability :math:`1 - 2^{-k}`. The communication
complexity per node is :math:`\mathcal{O}(N\lambda)`, which is due primarily to
threshold cryptography used in the common coin.

**Agreeing on a subset of proposed values.** Putting the above pieces
together, we use a protocol from Ben-Or et al. :cite:`Ben-Or:1994:ASC:197917.198088` to
agree on a set of values containing the entire proposals of at least :math:`N - f`
nodes. At a high level, this protocol proceeds in two main phases. In the first phase,
each node :math:`\mathcal{P}_i` uses Reliable Broadcast to disseminate its
proposed value to the other nodes. In the second stage, :math:`N` concurrent
instances of binary Byzantine agreement are used to agree on a bit
vector :math:`\{b_j\}_{j \in [1..N]}`, where :math:`b_j = 1` indicates that
:math:`\mathcal{P}_j`’s proposed value is included in the final set.

Actually the simple description above conceals a subtle challenge, for which
Ben-Or provide a clever solution.
`
A naïve attempt at an implementation of the above sketch would have each node
to wait for the first :math:`(N - f)` broadcasts to complete, and then propose
:math:`1` for the binary agreement instances corresponding to those and
:math:`0` for all the others. However, correct nodes might observe the
broadcasts complete in a different order. Since binary agreement only
guarantees that the output is :math:`1` if all the correct nodes unaninimously
propose :math:`1`, it is possible that the resulting bit vector could be
empty.

To avoid this problem, nodes abstain from proposing :math:`0` until they are
certain that the final vector will have at least :math:`N - f` bits set. To
provide some intuition for the flow of this protocol, we narrate several
possible scenarios in Figure 3. The algorithm from Ben-Or et al.
:cite:`Ben-Or:1994:ASC:197917.198088` is given in Figure 4. The running time is
:math:`\mathcal{O}(\log N)` in expectation, since it must wait for all binary agreement
instances to finish. [#f4]_ When instantiated with the reliable broadcast and binary
agreement constructions described above, the total communication
complexity is :math:`\mathcal{O}(N^2 |v| + \lambda N^3 \log N)` assuming
:math:`|v|` is the largest size of any node’s input.




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

.. [#t1] Typo fix: missing "of" - must correct in paper.

.. [#f2] Reliable channels can be emulated on top of unreliable channels by
	resending transmissions, at the expense of some efficiency.

.. [#f4] The expected running time can be reduced to :math:`\mathcal{O}(1)`
    (c.f. :cite:`Ben-Or:2003:RIC:1061993.1061994`) by running several instances in
    parallel, though this comes at the expense of throughput.
