.. _async-vs-wsync:

******************************************************************
THE GAP BETWEEN ASYNCHRONOUS AND WEAKLY SYNCHRONOUS NETWORK MODELS
******************************************************************

.. contents::
    :local:

Almost all modern BFT protocols rely on timing assumptions
(such as *partial* or *weak synchrony*) to guarantee liveness. Purely
asynchronous BFT protocols have received considerably less attention in
recent years. Consider the following argument, which, if it held, would
justify this narrowed focus:

	[X] *Weak synchrony assumptions are unavoidable, since in any
	network that violates these assumptions, even asynchronous
	protocols would provide unacceptable performance.*

In this section, we present [#e1]_ two counterarguments that refute the
premise above. First, we illustrate the theoretical separation between the
asynchronous and weakly synchronous network models.
Specifically we construct an adversarial network scheduler that
violates PBFT’s *weak synchrony* assumption (and indeed causes it
to fail) but under which any purely asynchronous protocol (such
as HoneyBadgerBFT) makes good progress. Second, we make a
practical observation: even when their assumptions are met, weakly
synchronous protocols are slow to recover from a network partition
once it heals, whereas asynchronous protocols make progress as
soon as messages are delivered.


Many Forms of Timing Assumptions
================================
Before proceeding we review the various standard forms of timing
assumptions. In an asynchronous network, the adversary can deliver
messages in any order and at any time, but nonetheless must *eventually*
deliver every message sent between correct nodes. Nodes in an asynchronous
network effectively have no use for "real time" clocks, and can only take
actions based on the *ordering* of messages they receive.

The well-known FLP :cite:`Fischer:1985:IDC:3149.214121` result rules out the
possibility of deterministic asynchronous protocols for atomic broadcast and
many other tasks. A deterministic protocol must therefore make some stronger
timing assumptions. A convenient (but very strong) network assumption is
*synchrony*: a :math:`\Delta`- synchronous network guarantees that every
message sent is delivered after at most a delay of :math:`\Delta` (where
:math:`\Delta` is a measure of real time).

Weaker timing assumptions come in several forms. In the
*unknown*-:math:`\Delta` model, the protocol is unable to use the delay bound
as a parameter. Alternatively, in the *eventually synchronous* model, the
message delay bound :math:`\Delta` is only guaranteed to hold after some
(unknown) instant, called the "Global Stabilization Time." Collectively, these
two models are referred to as *partial synchrony*
:cite:`Dwork:1988:CPP:42282.42283`. Yet another variation is *weak synchrony*
:cite:`Dwork:1988:CPP:42282.42283`, in which the delay bound is time varying,
but eventually does not grow faster than a polynomial function of time
:cite:`Castro:1999:PBF:296806.296824`.

In terms of feasibility, the above are equivalent -- a protocol that succeeds
in one setting can be systematically adapted for another. In terms of concrete
performance, however, adjusting for *weak synchrony* means gradually
increasing the timeout parameter over time (e.g., by an "exponential back-off"
policy). As we show later, this results in delays when recovering from
transient network partitions.

Protocols typically manifest these assumptions in the form of a timeout event.
For example, if parties detect that no progress has been made within a certain
interval, then they take a corrective action such as electing a new leader.
Asynchronous protocols do not rely on timers, and make progress whenever
messages are delivered, regardless of actual clock time.

**Counting rounds in asynchronous networks.** Although the guarantee of
eventual delivery is decoupled from notions of "real time," it is nonetheless
desirable to characterize the running time of asynchronous protocols. The
standard approach (e.g., as explained by Canetti and Rabin
:cite:`Canetti:1993:FAB:167088.167105`) is for the adversary to assign each
message a virtual round number, subject to the condition that every
:math:`(r − 1)`-message between correct nodes must be delivered before any
:math:`(r + 1)`-message is sent.


When Weak Synchrony Fails
=========================
We now proceed to describe why weakly synchronous BFT protocols can fail
(or suffer from performance degradation) when network conditions are
adversarial (or unpredictable). This motivates why such protocols are
unsuited for the cryptocurrency-oriented application scenarios described
in :ref:`Section 1 <intro>`.

**A network scheduler that thwarts PBFT.** We use Practical Byzantine
Fault Tolerance (PBFT) :cite:`Castro:1999:PBF:296806.296824`, the classic
leader-based BFT protocol, as [#e2]_ a representative example to describe how
an adversarial network scheduler can cause a class of leader-based BFT
protocols :cite:`Amir:2011:PBR:1990767.1990952,Aublin:2013:RRB:2549695.2549742,Bessani:2014:SMR:2671853.2672428,Clement:2009:MBF:1558977.1558988,Kotla:2007:ZSB:1323293.1294267,Veronese:2009:SOW:1637865.1638341` to grind to a halt.

At any given time, the designated leader is responsible for proposing the next
batch of transactions. If progress isn’t made, either because the leader is
faulty or because the network has stalled, then the nodes attempt to elect a
new leader. The PBFT protocol critically relies on a weakly synchronous
network for liveness. We construct an adversarial scheduler that violates this
assumption, and indeed prevents PBFT from making any progress at all, but for
which HoneyBadgerBFT (and, in fact, any asynchronous protocol) performs well.
It is unsurprising that a protocol based on timing assumptions fails when
those assumptions are violated; however, demonstrating an explicit attack
helps motivate our asynchronous construction.

The intuition behind our scheduler is simple. First, we assume
that a single node has crashed. Then, the network delays messages
whenever a correct node is the leader, preventing progress and
causing the next node in round-robin order to become the new
leader. When the crashed node is the next up to become the leader,
the scheduler immediately heals the network partition and delivers
messages very rapidly among the honest nodes; however, since the
leader has crashed, no progress is made here either.

This attack violates the weak synchrony assumption because it must delay
messages for longer and longer each cycle, since PBFT widens its timeout
interval after each failed leader election. On the other hand, it provides
larger and larger periods of synchrony as well. However, since these periods
of synchrony occur at inconvenient times, PBFT is unable to make use of them.
Looking ahead, HoneyBadgerBFT, and indeed any asynchronous protocol, would be
able to make progress during these opportunistic periods of synchrony.

To confirm our analysis, we implemented this malicious scheduler as a proxy
that intercepted and delayed all view change messages to the new leader, and
tested it against a 1200 line Python implementation of PBFT. The results and
message logs we observed were consistent with the above analysis; our replicas
became stuck in a loop requesting view changes that never succeeded. In the
Appendix A (:ref:`pbft-attack`) we give a complete description of PBFT and
explain how it behaves under this attack.

**Slow recovery from network partitions.** Even if the weak synchrony
assumption is eventually satisfied, protocols that rely on it may also be slow
to recover from transient network partitions. Consider the following scenario,
which is simply a finite prefix of the attack described above: one node is
crashed, and the network is temporarily partitioned for a duration of
:math:`2^D \Delta`. Our scheduler heals the network partition precisely when
it is the crashed node’s turn to become leader. Since the timeout interval at
this point is now :math:`2^{D+1} \Delta`, the protocol must wait for another
:math:`2^{D+1} \Delta` interval before beginning to elect a new leader,
despite that the network is synchronous during this interval.

**The tradeoff between robustness and responsiveness.** Such behaviors we
observe above are not specific to PBFT, but rather are fundamentally inherent
to protocols that rely on timeouts to cope with crashes. Regardless of the
protocol variant, a practitioner must tune their timeout policy according to
some tradeoff. At one extreme (eventual synchrony), the practitioner makes a
specific estimate about the network delay :math:`\Delta`. If the estimate is
too low, then the system may make no progress at all; too high, and it does
not utilize the available bandwidth. At the other extreme (weak synchrony),
the practitioner avoids specifying any absolute delay, but nonetheless must
choose a "gain" that affects how quickly the system tracks varying conditions.
An asynchronous protocol avoids the need to tune such parameters.


.. [#e1] The conference paper says: "present make". This needs to be
	corrected.

.. [#e2] The conf paper does have the "as". Should it be there?
