import keyring
import argparse


parser = argparse.ArgumentParser()
parser.add_argument('-r', default=False, help='read mode (debug feature)')
parser.add_argument('-s', help='service name')
parser.add_argument('-u', help='user name')
parser.add_argument('-p', help='password')
args = parser.parse_args()

if args.r:
    print(keyring.get_password(args.s, args.u))
else:
    keyring.set_password(args.s, args.u, args.p)
