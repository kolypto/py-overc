import os, argparse
from overc import OvercApplication

# Arguments
parser = argparse.ArgumentParser(description='WSGI application launcher')
parser.add_argument('instance_path', help="Application instance path (configs & runtime data)")
args = parser.parse_args()

# Application
app = OvercApplication(
    __name__,
    os.path.realpath(args.instance_path)
)

if __name__ == '__main__':
    app.run()
