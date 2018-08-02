************
INTRODUCTION
************

**Robustness is a first-class citizen.**

**Favor throughput over latency.**

Our Contributions
=================

**Timing assumptions considered harmful.**

**Practical asynchronous BFT.** We propose HoneyBadgerBFT, the first BFT
*atomic broadcast* protocol to provide *optimal asymptotic efficiency* in
the asynchronous setting. We therefore directly refute the prevailing wisdom
that such protocols a re necessarily impractical.

**Implementation and large-scale experiments.**
* Python implementation
* Experimental results from an Amazon AWS deployment with more than
  100 nodes distributed across 5 continents
* Deployed HoneyBadgerBFT over the Tor anonymous relay network
  without changing any parameters

Suggested Deployment Scenarios
==============================

**Confederation cryptocurrencies.**

**Applicability to permissionless blockchains.**
Several recent works
have suggested the promising idea of leveraging either a slower,
external blockchain such as Bitcoin or economic “proof-of-stake”
assumptions involving the underlying currency itself [32, 32, 35, 37]
to bootstrap faster BFT protocols, by selecting a random committee
to perform BFT in every different epoch. These approaches promise
to achieve the best of both worlds, security in an open enrollment,
decentralized network, and the throughput and response time match-
ing classical BFT protocols. Here too HoneyBadgerBFT is a natural
choice since the randomly selected committee can be geographically
heterogeneous.
