import argparse
import base64
import pickle

from coincurve import PrivateKey


def generate_key_list(players):
    return [PrivateKey().secret for _ in range(players)]


def main():
    """ """
    parser = argparse.ArgumentParser()
    parser.add_argument('players', help='The number of players')
    parser.add_argument('output_file', help='File to write the keys')
    args = parser.parse_args()
    players = int(args.players)
    keylist = generate_key_list(players)
    print(base64.encodebytes(pickle.dumps(keylist)).decode())


if __name__ == '__main__':
    main()
