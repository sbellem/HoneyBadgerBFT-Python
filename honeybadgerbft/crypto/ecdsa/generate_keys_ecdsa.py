from .ecdsa_ssl import KEY
import argparse
import pickle


def generate_key_list(players):
    keylist = []
    for i in range(players):
        key = KEY()
        key.generate()
        keylist.append(key.get_secret())
    return keylist


def main():
    """ """
    parser = argparse.ArgumentParser()
    parser.add_argument('players', help='The number of players')
    args = parser.parse_args()
    players = int(args.players)
    keylist = generate_key_list(players)
    print(pickle.dumps(keylist))


if __name__ == '__main__':
    main()
