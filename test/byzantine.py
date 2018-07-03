import logging
from collections import defaultdict
from distutils.util import strtobool
from os import environ

import gevent
from gevent.event import Event

from honeybadgerbft.exceptions import RedundantMessageError


logger = logging.getLogger(__name__)
CONF_PHASE = strtobool(environ.get('CONF_PHASE', '1'))


def byz_ba_issue_59(sid, pid, N, f, coin, input, decide, broadcast, receive):
    """Modified binary consensus from [MMR14], so that it exhibits a
    byzantine behavior as per issue #59
    (see https://github.com/amiller/HoneyBadgerBFT/issues/59).

    :param sid: session identifier
    :param pid: my id number
    :param N: the number of parties
    :param f: the number of byzantine parties
    :param coin: a ``common coin(r)`` is called to block until receiving a bit
    :param input: ``input()`` is called to receive an input
    :param decide: ``decide(0)`` or ``output(1)`` is eventually called
    :param broadcast: broadcast channel
    :param receive: receive channel
    :return: blocks until
    """
    # Messages received are routed to either a shared coin, the broadcast, or AUX
    est_values = defaultdict(lambda: [set(), set()])
    aux_values = defaultdict(lambda: [set(), set()])
    conf_values = defaultdict(lambda: {(0,): set(), (1,): set(), (0, 1): set()})
    est_sent = defaultdict(lambda: [False, False])
    conf_sent = defaultdict(lambda: {(0,): False, (1,): False, (0, 1): False})
    bin_values = defaultdict(set)

    # This event is triggered whenever bin_values or aux_values changes
    bv_signal = Event()

    def _recv():
        while True:  # not finished[pid]:
            (sender, msg) = receive()
            logger.debug(f'receive {msg} from node {sender}',
                          extra={'nodeid': pid, 'epoch': msg[1]})
            assert sender in range(N)
            if msg[0] == 'EST':
                # BV_Broadcast message
                _, r, v = msg
                assert v in (0, 1)
                if sender in est_values[r][v]:
                    print('Redundant EST received', msg)
                    raise RedundantMessageError(
                        'Redundant EST received {}'.format(msg))

                est_values[r][v].add(sender)
                # Relay after reaching first threshold
                if len(est_values[r][v]) >= f + 1 and not est_sent[r][v]:
                    est_sent[r][v] = True
                    for receiver in range(N):
                        logger.debug(
                            f"broadcast {('EST', r, v)} to node {receiver}",
                            extra={'nodeid': pid, 'epoch': r})
                        if receiver != 2:
                            broadcast(('EST', r, v), receiver=receiver)

                # Output after reaching second threshold
                if len(est_values[r][v]) >= 2 * f + 1:
                    logger.debug(
                        f'add v = {v} to bin_value[{r}] = {bin_values[r]}',
                        extra={'nodeid': pid, 'epoch': r},
                    )
                    bin_values[r].add(v)
                    logger.debug(f'bin_values[{r}] is now: {bin_values[r]}',
                                 extra={'nodeid': pid, 'epoch': r})
                    bv_signal.set()

            elif msg[0] == 'AUX':
                # Aux message
                _, r, v = msg
                assert v in (0, 1)
                if sender in aux_values[r][v]:
                    print('Redundant AUX received', msg)
                    raise RedundantMessageError(
                        'Redundant AUX received {}'.format(msg))

                aux_values[r][v].add(sender)
                logger.debug(
                    f'add v = {v} to aux_value[{r}] = {aux_values[r]}',
                    extra={'nodeid': pid, 'epoch': r},
                )

                bv_signal.set()

            elif msg[0] == 'CONF' and CONF_PHASE:
                # CONF message
                _, r, v = msg
                assert v in ((0,), (1,), (0, 1))
                if sender in conf_values[r][v]:
                    # FIXME: raise or continue? For now will raise just
                    # because it appeared first, but maybe the protocol simply
                    # needs to continue.
                    print(f'Redundant CONF received {msg} by {sender}')
                    raise RedundantMessageError(
                        f'Redundant CONF received {msg} by {sender}')

                conf_values[r][v].add(sender)
                logger.debug(
                    f'add v = {v} to conf_value[{r}] = {conf_values[r]}',
                    extra={'nodeid': pid, 'epoch': r},
                )

                bv_signal.set()

    # Run the receive loop in the background
    _thread_recv = gevent.spawn(_recv)

    # Block waiting for the input
    vi = input()
    assert vi in (0, 1)
    est = vi
    r = 0
    already_decided = None
    while True:  # Unbounded number of rounds
        logger.debug(f'starting round {r} with est set to {est}', 
                     extra={'nodeid': pid, 'epoch': r})
        not_est = int(not bool(est))
        if not est_sent[r][est]:
            est_sent[r][est] = True
            est_sent[r][not_est] = True
            logger.debug(
                f"broadcast {('EST', r, int(not bool(est)))} to node {0}",
                extra={'nodeid': pid, 'epoch': r},
            )
            broadcast(('EST', r, int(not bool(est))), receiver=0)
            logger.debug(
                f"broadcast {('EST', r, est)} to node {1}",
                extra={'nodeid': pid, 'epoch': r},
            )
            broadcast(('EST', r, est), receiver=1)

        while len(bin_values[r]) == 0:
            # Block until a value is output
            bv_signal.clear()
            bv_signal.wait()

        w = next(iter(bin_values[r]))  # take an element
        logger.debug(f"broadcast {('AUX', r, w)}",
                     extra={'nodeid': pid, 'epoch': r})
        for receiver in range(N):
            if receiver != 2:
                broadcast(('AUX', r, w), receiver=receiver)

        # After this all messages within A are delivered and x sends both
        # BVAL(0) and BVAL(1) to every node in A. Thus every node in A
        # broadcasts both BVAL(0) and BVAL(1) and sets bin_values={0,1}.
        logger.debug(
            'x sends both BVAL(0) and BVAL(1) to every node in A.',
            extra={'nodeid': pid, 'epoch': r},
        )
        broadcast(('EST', r, est), receiver=0)
        broadcast(('EST', r, int(not bool(est))), receiver=1)

        # XXX CONF phase
        if CONF_PHASE and not conf_sent[r][(0, 1)]:
            conf_sent[r][(0, 1)] = True
            logger.debug(f"broadcast {('CONF', r, (0, 1))}",
                         extra={'nodeid': pid, 'epoch': r})
            broadcast(('CONF', r, (0, 1)))

        logger.debug(
            f'Block until receiving the common coin value',
            extra={'nodeid': pid, 'epoch': r},
        )
        # Block until receiving the common coin value
        s = coin(r)
        logger.debug(f's = coin(r) | s = {s}, r = {r}',
                     extra={'nodeid': pid, 'epoch': r})
        not_s = int(not bool(s))

        logger.debug(f"broadcast {('EST', r, not_s)} to node 2",
                     extra={'nodeid': pid, 'epoch': r})
        broadcast(('EST', r, not_s), receiver=2)
        logger.debug(f"broadcast {('AUX', r, not_s)} to node 2",
                     extra={'nodeid': pid, 'epoch': r})
        broadcast(('AUX', r, not_s), receiver=2)
        logger.debug(f'exiting round {r}, setting est = s ({s})',
                     extra={'nodeid': pid, 'epoch': r})
        est = s
        r += 1
