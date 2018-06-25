import logging
import unittest
import gevent
import random

from gevent.event import Event
from gevent.queue import Queue
from honeybadgerbft.core.commoncoin import shared_coin
from honeybadgerbft.core.binaryagreement import binaryagreement
from honeybadgerbft.crypto.threshsig.boldyreva import dealer
from collections import defaultdict

from pytest import mark, raises

logger = logging.getLogger(__name__)

def simple_broadcast_router(N, maxdelay=0.005, seed=None):
    """Builds a set of connected channels, with random delay
    @return (receives, sends)
    """
    rnd = random.Random(seed)
    #if seed is not None: print 'ROUTER SEED: %f' % (seed,)
    
    queues = [Queue() for _ in range(N)]
    _threads = []

    def makeBroadcast(i):
        def _send(j, o):
            delay = rnd.random() * maxdelay
            #print 'SEND   %8s [%2d -> %2d] %2.1f' % (o[0], i, j, delay*1000), o[1:]
            gevent.spawn_later(delay, queues[j].put, (i,o))
            #queues[j].put((i, o))
        def _bc(o):
            #print 'BCAST  %8s [%2d ->  *]' % (o[0], i), o[1]
            for j in range(N): _send(j, o)
        return _bc

    def makeRecv(j):
        def _recv():
            (i,o) = queues[j].get()
            #print 'RECV %8s [%2d -> %2d]' % (o[0], i, j)
            return (i,o)
        return _recv
        
    return ([makeBroadcast(i) for i in range(N)],
            [makeRecv(j)      for j in range(N)])


def byzantine_broadcast_router(N, maxdelay=0.005, seed=None, **byzargs):
    """Builds a set of connected channels, with random delay.

    :return: (receives, sends) endpoints.
    """
    rnd = random.Random(seed)
    queues = [Queue() for _ in range(N)]
    _threads = []

    def makeBroadcast(i):
        def _send(j, o):
            delay = rnd.random() * maxdelay
            if j == byzargs.get('byznode'):
                try:
                    byz_tag = byzargs['byz_message_type']
                except KeyError:
                    pass
                else:
                    o = list(o)
                    o[0] = byz_tag
                    o = tuple(o)

            gevent.spawn_later(delay, queues[j].put, (i, o))

            if (j == byzargs.get('byznode') and
                    o[0] == byzargs.get('redundant_msg_type')):
                gevent.spawn_later(delay, queues[j].put, (i, o))

        def _bc(o):
            for j in range(N):
                _send(j, o)

        return _bc

    def makeRecv(j):
        def _recv():
            (i,o) = queues[j].get()
            return (i,o)

        return _recv

    return ([makeBroadcast(i) for i in range(N)],
            [makeRecv(j) for j in range(N)])


def network_scheduler(events, message_queues, receivers, rounds):
    for r in rounds:
        print(f'round {r}')
        for i in range(8):
            events[r, i].wait()
            for m in message_queues[r, i]:
                gevent.spawn_later(
                    m.get('delay', 0.00000000000000000000001),
                    receivers[m['receiver']].put,
                    (m['sender'], m['msg']),
                )
            else:
                events[r, i, 'done'].set()


def byzantine_router_issue_59(N):
    events = defaultdict(Event)
    message_queues = defaultdict(Queue)
    held_messages = defaultdict(set)
    receivers = [Queue() for _ in range(N)]
    counters = defaultdict(int)

    coins = defaultdict(Queue)

    r = 0
    rounds = Queue()
    rounds.put(r)
    votes = {0: 0}

    gevent.spawn(
        network_scheduler,
        events,
        message_queues,
        receivers,
        rounds,
    )

    def makeBroadcast(i):
        def _queue_messages(*, epoch, message_group,
                            held_messages, message_queues):
            phase = message_group['phase']
            messages = message_group['messages']
            counter = message_group['counter']
            for m in messages:
                if counters[epoch, phase] >= counter:
                    break
                try:
                    held_messages[epoch].remove(m)
                except KeyError:
                    pass
                else:
                    message_queues[epoch, phase].put(
                        {'sender': m[0], 'receiver': m[1], 'msg': m[2]}
                    )
                    counters[epoch, phase] += 1
                    if phase == 4:
                        coins[epoch].put(int(not bool(m[2][2])))
                        votes[epoch + 1] = int(not bool(m[2][2]))
                        break
            if counters[epoch, phase] == counter:
                message_queues[epoch, phase].put(StopIteration)

        def _set_event(*, events, epoch, phase):
            ready = not events[epoch, phase].ready()
            if phase == 0 and epoch > 0:
                ready = ready and events[epoch-1, 7, 'done'].ready()
            elif phase > 0:
                ready = ready and events[epoch, phase-1].ready()
            if phase == 6:
                ready = (ready and
                    StopIteration in message_queues[epoch, phase].queue)
            if ready:
                print(f'event {phase}, round {epoch}')
                events[epoch, phase].set()

        def _send(j, o):
            nonlocal r
            v = votes[r]
            not_v = int(not bool(v))

            M0 = [
                (3, 0, ('EST', r, not_v)),
                (3, 1, ('EST', r, v)),
                (2, 0, ('EST', r, not_v)),
                (2, 1, ('EST', r, not_v)),
                (0, 0, ('EST', r, v)),
                (0, 0, ('EST', r, not_v)),
            ]
            M1 = [
                (0, 1, ('EST', r, v)),
                (1, 1, ('EST', r, v)),
            ]
            M2 = [
                (1, 0, ('EST', r, v)),
                (0, 1, ('EST', r, not_v)),
                (0, 0, ('AUX', r, not_v)),
                (0, 1, ('AUX', r, not_v)),
                (1, 0, ('AUX', r, v)),
                (1, 1, ('AUX', r, v)),
            ]
            M3 = [
                (3, 0, ('EST', r, v)),
                (3, 1, ('EST', r, not_v)),
                (3, 0, ('AUX', r, not_v)),
                (3, 1, ('AUX', r, not_v)),
            ]
            M4 = [
                (3, 2, ('EST', r, 0)),
                (3, 2, ('EST', r, 1)),
            ]
            G1 = (
                {'phase': 0, 'messages': M0, 'counter': 6},
                {'phase': 1, 'messages': M1, 'counter': 2},
                {'phase': 2, 'messages': M2, 'counter': 6},
                {'phase': 3, 'messages': M3, 'counter': 4},
                {'phase': 4, 'messages': M4, 'counter': 1},
            )

            if i in (0, 1, 2, 3) and j == 3:
                if r == 0 or events[r-1, 6].ready() and o[1] == r:
                    gevent.spawn_later(
                        0.00000000000000001, receivers[j].put, (i, o))
            else:
                held_messages[o[1]].add((i, j, o))

            for message_group in G1:
                _queue_messages(
                    epoch=r,
                    message_group=message_group,
                    held_messages=held_messages,
                    message_queues=message_queues,
                )
                _set_event(
                    epoch=r, phase=message_group['phase'], events=events)

            # PHASES 5 & 6
            if not coins[r].empty():
                not_coin = int(not bool(coins[r].peek()))
                M5 = [
                    (0, 2, ('EST', r, not_coin)),
                    (1, 2, ('EST', r, not_coin)),
                ]
                M6 = [
                    (0, 2, ('AUX', r, not_coin)),
                    (1, 2, ('AUX', r, not_coin)),
                    (2, 2, ('AUX', r, not_coin)),
                    (3, 2, ('AUX', r, not_coin)),
                ]
                G2 = (
                    {'phase': 5, 'messages': M5, 'counter': 2},
                    {'phase': 6, 'messages': M6, 'counter': 3},
                )
                for message_group in G2:
                    _queue_messages(
                        epoch=r,
                        message_group=message_group,
                        held_messages=held_messages,
                        message_queues=message_queues,
                    )
                    _set_event(
                        epoch=r, phase=message_group['phase'], events=events)

            if events[r, 6].ready():
                for m in set(held_messages[r]):
                    message_queues[r, 7].put(
                        {'sender': m[0], 'receiver': m[1], 'msg': m[2]})
                    held_messages[r].remove(m)
                else:
                    message_queues[r, 7].put(StopIteration)
                    events[r, 7].set()

            if events[r, 7].ready():
                votes[r] = coins[r].peek()
                r += 1
                rounds.put(r)

        def _bc(o, receiver=None):
            if receiver is not None:
                _send(receiver, o)
            else:
                for j in range(N):
                    _send(j, o)

        return _bc

    def makeRecv(j):
        def _recv():
            (i,o) = receivers[j].get()
            return (i,o)

        return _recv

    return ([makeBroadcast(i) for i in range(N)],
            [makeRecv(j) for j in range(N)])


def dummy_coin(sid, N, f):
    counter = defaultdict(int)
    events = defaultdict(Event)
    def getCoin(round):
        # Return a pseudorandom number depending on the round, without blocking
        counter[round] += 1
        if counter[round] == f+1: events[round].set()
        events[round].wait()
        return hash((sid,round)) % 2
    return getCoin


### Test binary agreement with a dummy coin
def _test_binaryagreement_dummy(N=4, f=1, seed=None):
    # Generate keys
    sid = 'sidA'    
    # Test everything when runs are OK
    #if seed is not None: print 'SEED:', seed
    rnd = random.Random(seed)
    router_seed = rnd.random()
    sends, recvs = simple_broadcast_router(N, seed=seed)

    threads = []
    inputs = []
    outputs = []
    coin = dummy_coin(sid, N, f)  # One dummy coin function for all nodes

    for i in range(N):
        inputs.append(Queue())
        outputs.append(Queue())
        
        t = gevent.spawn(binaryagreement, sid, i, N, f, coin,
                         inputs[i].get, outputs[i].put_nowait, sends[i], recvs[i])
        threads.append(t)

    for i in range(N):
        inputs[i].put(random.randint(0,1))
    #gevent.killall(threads[N-f:])
    #gevent.sleep(3)
    #for i in range(N-f, N):
    #    inputs[i].put(0)
    try:
        outs = [outputs[i].get() for i in range(N)]
        assert len(set(outs)) == 1
        try: gevent.joinall(threads)
        except gevent.hub.LoopExit: pass
    except KeyboardInterrupt:
        gevent.killall(threads)
        raise


def test_binaryagreement_dummy():
    _test_binaryagreement_dummy()


@mark.parametrize('msg_type', ('EST', 'AUX'))
@mark.parametrize('byznode', (1, 2, 3))
def test_binaryagreement_dummy_with_redundant_messages(byznode, msg_type):
    N = 4
    f = 1
    seed = None
    sid = 'sidA'
    rnd = random.Random(seed)
    router_seed = rnd.random()
    sends, recvs = byzantine_broadcast_router(
        N, seed=seed, byznode=byznode, redundant_msg_type=msg_type)
    threads = []
    inputs = []
    outputs = []
    coin = dummy_coin(sid, N, f)  # One dummy coin function for all nodes

    for i in range(N):
        inputs.append(Queue())
        outputs.append(Queue())
        t = gevent.spawn(binaryagreement, sid, i, N, f, coin,
                         inputs[i].get, outputs[i].put_nowait, sends[i], recvs[i])
        threads.append(t)

    for i in range(N):
        inputs[i].put(random.randint(0,1))

    with raises(gevent.hub.LoopExit) as err:
        outs = [outputs[i].get() for i in range(N)]

    try:
        gevent.joinall(threads)
    except gevent.hub.LoopExit:
        pass


@mark.parametrize('byznode', (1, 2, 3))
def test_binaryagreement_dummy_with_byz_message_type(byznode):
    N = 4
    f = 1
    seed = None
    sid = 'sidA'
    rnd = random.Random(seed)
    router_seed = rnd.random()
    sends, recvs = byzantine_broadcast_router(
        N, seed=seed, byznode=byznode, byz_message_type='BUG')
    threads = []
    inputs = []
    outputs = []
    coin = dummy_coin(sid, N, f)  # One dummy coin function for all nodes

    for i in range(N):
        inputs.append(Queue())
        outputs.append(Queue())
        t = gevent.spawn(binaryagreement, sid, i, N, f, coin,
                         inputs[i].get, outputs[i].put_nowait, sends[i], recvs[i])
        threads.append(t)

    for i in range(N):
        inputs[i].put(random.randint(0,1))

    with raises(gevent.hub.LoopExit) as err:
        outs = [outputs[i].get() for i in range(N)]
    try:
        gevent.joinall(threads)
    except gevent.hub.LoopExit:
        pass


### Test binary agreement with boldyreva coin
def _make_coins(sid, N, f, seed):
    # Generate keys
    PK, SKs = dealer(N, f+1)
    rnd = random.Random(seed)
    router_seed = rnd.random()
    sends, recvs = simple_broadcast_router(N, seed=seed)
    coins = [shared_coin(sid, i, N, f, PK, SKs[i], sends[i], recvs[i]) for i in range(N)]
    return coins

def _test_binaryagreement(N=4, f=1, seed=None):
    # Generate keys
    sid = 'sidA'
    # Test everything when runs are OK
    #if seed is not None: print 'SEED:', seed
    rnd = random.Random(seed)

    # Instantiate the common coin
    coins_seed = rnd.random()
    coins = _make_coins(sid+'COIN', N, f, coins_seed)

    # Router
    router_seed = rnd.random()
    sends, recvs = simple_broadcast_router(N, seed=seed)

    threads = []
    inputs = []
    outputs = []

    for i in range(N):
        inputs.append(Queue())
        outputs.append(Queue())
        
        t = gevent.spawn(binaryagreement, sid, i, N, f, coins[i],
                         inputs[i].get, outputs[i].put_nowait, sends[i], recvs[i])
        threads.append(t)

    for i in range(N):
        inputs[i].put(random.randint(0,1))
    #gevent.killall(threads[N-f:])
    #gevent.sleep(3)
    #for i in range(N-f, N):
    #    inputs[i].put(0)
    try:
        outs = [outputs[i].get() for i in range(N)]
        assert len(set(outs)) == 1
        try: gevent.joinall(threads)
        except gevent.hub.LoopExit: pass
    except KeyboardInterrupt:
        gevent.killall(threads)
        raise

def test_binaryagreement():
    for i in range(5): _test_binaryagreement(seed=i)


@mark.parametrize('values,s,already_decided,expected_est,'
                  'expected_already_decided,expected_output', (
    ({0}, 0, None, 0, 0, 0),
    ({1}, 1, None, 1, 1, 1),
))
def test_set_next_round_estimate_with_decision(values, s, already_decided,
                    expected_est, expected_already_decided, expected_output):
    from honeybadgerbft.core.binaryagreement import set_new_estimate
    decide = Queue()
    updated_est, updated_already_decided = set_new_estimate(
        values=values,
        s=s,
        already_decided=already_decided,
        decide=decide.put,
    )
    assert updated_est == expected_est
    assert updated_already_decided == expected_already_decided
    assert decide.get() == expected_output


@mark.parametrize('values,s,already_decided,'
                  'expected_est,expected_already_decided', (
    ({0}, 0, 1, 0, 1),
    ({0}, 1, None, 0, None),
    ({0}, 1, 0, 0, 0),
    ({0}, 1, 1, 0, 1),
    ({1}, 0, None, 1, None),
    ({1}, 0, 0, 1, 0),
    ({1}, 0, 1, 1, 1),
    ({1}, 1, 0, 1, 0),
    ({0, 1}, 0, None, 0, None),
    ({0, 1}, 0, 0, 0, 0),
    ({0, 1}, 0, 1, 0, 1),
    ({0, 1}, 1, None, 1, None),
    ({0, 1}, 1, 0, 1, 0),
    ({0, 1}, 1, 1, 1, 1),
))
def test_set_next_round_estimate(values, s, already_decided,
                                 expected_est, expected_already_decided):
    from honeybadgerbft.core.binaryagreement import set_new_estimate
    decide = Queue()
    updated_est, updated_already_decided = set_new_estimate(
        values=values,
        s=s,
        already_decided=already_decided,
        decide=decide.put,
    )
    assert updated_est == expected_est
    assert updated_already_decided == expected_already_decided
    assert decide.empty()


@mark.parametrize('values,s,already_decided', (
    ({0}, 0, 0),
    ({1}, 1, 1),
))
def test_set_next_round_estimate_raises(values, s, already_decided):
    from honeybadgerbft.core.binaryagreement import set_new_estimate
    from honeybadgerbft.exceptions import AbandonedNodeError
    with raises(AbandonedNodeError):
        updated_est, updated_already_decided = set_new_estimate(
            values=values,
            s=s,
            already_decided=already_decided,
            decide=None,
        )

        
@mark.skip(
    reason=('Will loop indefinitely as fix is not implemented yet.'
            'See https://github.com/amiller/HoneyBadgerBFT/issues/59')
)
def test_issue59_attack():
    from .byzantine import byz_ba_issue_59
    N = 4
    f = 1
    seed = None
    sid = 'sidA'
    rnd = random.Random(seed)
    sends, recvs = byzantine_router_issue_59(N)
    threads = []
    inputs = []
    outputs = []

    # Instantiate the common coin
    coins_seed = rnd.random()
    coins = _make_coins(sid+'COIN', N, f, coins_seed)

    for i in range(4):
        inputs.append(Queue())
        outputs.append(Queue())

    t = gevent.spawn(byz_ba_issue_59, sid, 3, N, f, coins[3],
                     inputs[3].get, outputs[3].put_nowait, sends[3], recvs[3])
    threads.append(t)

    for i in (2, 0, 1):
        t = gevent.spawn(binaryagreement, sid, i, N, f, coins[i],
                         inputs[i].get, outputs[i].put_nowait, sends[i], recvs[i])
        threads.append(t)

    inputs[0].put(0)    # A_0
    inputs[1].put(0)    # A_1
    inputs[2].put(1)    # B
    inputs[3].put(0)    # F (x)

    #with raises(gevent.hub.LoopExit) as err:
    #outs = [outputs[i].get() for i in range(N)]
    failing = True
    while failing:
        try:
            outs = [outputs[i].get() for i in range(N)]
        except gevent.hub.LoopExit:
            pass
        else:
            failing = False
    try:
        gevent.joinall(threads)
    except gevent.hub.LoopExit:
        pass
