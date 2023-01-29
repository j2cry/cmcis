#!/home/bot/venv/bin/python3
import keyring
import argparse


parser = argparse.ArgumentParser()
parser.add_argument('-r', default=False, help='read mode (debug feature)')
parser.add_argument('-s', help='service name')
parser.add_argument('-u', help='user name')
parser.add_argument('-p', help='password')
args = parser.parse_args()

if args.r:
    print(f'GET PWD FROM SERVICE `{args.s}` ON USER `{args.u}`')
    print(f'`{keyring.get_password(args.s, args.u)}`')
else:
    print(f'SET PWD: `{args.p}` TO SERVICE `{args.s}` ON USER `{args.u}`')
    keyring.set_password(args.s, args.u, args.p)
