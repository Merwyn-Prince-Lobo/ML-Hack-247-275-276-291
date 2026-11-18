"""Portable entry point; local optional libraries live in .deps."""
import sys
from pathlib import Path
local = Path(__file__).resolve().parent / '.deps'
if local.exists():
    sys.path.append(str(local))

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=['explore', 'train', 'serve', 'ui', 'report', 'verify', 'review1'])
    parser.add_argument('--trip', default='00000003', help='Training trip used by the Review 1 demonstration')
    parser.add_argument('--host', default='0.0.0.0')
    parser.add_argument('--port', type=int)
    parser.add_argument('--trials', type=int, default=10)
    args = parser.parse_args()
    if args.command == 'serve':
        import uvicorn
        uvicorn.run('pathsnap.api:app', host=args.host, port=args.port or 8000)
    elif args.command == 'ui':
        import http.server
        from functools import partial
        http.server.ThreadingHTTPServer((args.host, args.port or 8501), partial(http.server.SimpleHTTPRequestHandler, directory='ui')).serve_forever()
    elif args.command == 'review1':
        from pathsnap.review1 import main
        main(args.trip)
    elif args.command == 'train':
        from pathsnap.experiments import main
        main(args.trials)
    elif args.command == 'explore':
        from pathsnap.explore import main
        main()
    elif args.command == 'report':
        from pathsnap.report import main
        main()
    elif args.command == 'verify':
        import unittest
        result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.discover('tests'))
        sys.exit(not result.wasSuccessful())
