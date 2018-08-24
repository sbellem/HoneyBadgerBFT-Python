.. _appendix:

********
APPENDIX
********

.. contents::
    :local:

.. _pbft-attack:

ATTACKING PBFT
==============
**PBFT.**

**An intermittently synchronous network that thwarts PBFT.**

**How PBFT behaves under attack.**

**Intermittently synchronous networks.**




.. _deferred-proofs:

DEFERRED PROOFS
===============
We now restate and prove the theorems originally stated in :ref:`Section 4.5
<analysis>`.

**THEOREM 3.** (Efficiency). *Assuming each correct node’s queue contains at
least* :math:`B` *distinct transactions, then the expected number of
transactions committed in an epoch is at least* :math:`\frac{B}{4}`
*, resulting in constant efficiency.*

**PROOF.** First, we consider an experiment where the threshold-encrypted
ciphertexts are replaced with encryptions of random plaintexts. In this case,
the adversary does not learn any information about the proposed batch for each
honest party. We will first show that in this experiment, the expected number
of transactions committed in an epoch is at least :math:`frac{1}{4}B`.

**Experiment 1.**


**Experiment 2.**

**THEOREM 4.** (Censorship Resilience)

**LEMMA 1.**



.. _aba:

ASYNCHRONOUS BINARY BYZANTINE AGREEMENT
=======================================

**Realizing binary agreement from a common coin.** Binary agreement allows
nodes to agree on the value of a single bit. More formally, binary agreement
guarantees three properties:

* *(Agreement)* If any correct node outputs the bit :math:`b`, then every
  correct node outputs :math:`b`.
* *(Termination)* If all correct nodes receive input, then every correct
  node outputs a bit.
* *(Validity)* If any correct node outputs :math:`b`, then at least one
  correct node received :math:`b` as input.

The validity property implies *unanimity*: if all of the correct nodes receive
the same input value :math:`b`, then :math:`b` must be the decided value. On
the other hand, if at any point two nodes receive different inputs, then the
adversary may force the decision to either value even before the remaining
nodes receive input.

We instantiate this primitive with a protocol based on cryptographic common
coin, which essentially act as synchronizing gadgets. The adversary only
learns the value of the next coin after a majority of correct nodes have
committed to a vote -- if the coin matches the majority vote, then that is the
decided value. The adversary can influence the majority vote each round, but
only until the coin is revealed.

The Byzantine agreement algorithm from Moustefaoui et al.
:cite:`Mostefaoui:2014:SAB:2611462.2611468` is shown in Figure 11. Its
expected running time is :math:`\mathcal{O}(1)`, and in fact completes within
:math:`\mathcal{O}(k)` rounds with probability :math:`1 − 2^{−k}`. When
instantiated with the common coin defined below, the total communication
complexity is :math:`\mathcal{O}(\lambda N^2)`, since it uses a constant
number of common coins.


**Realizing a common coin from a threshold signature scheme.**
