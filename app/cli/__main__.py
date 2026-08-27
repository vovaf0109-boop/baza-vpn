import argparse
import asyncio
import sys
from collections.abc import Sequence

from app.cli.vpn import CliError, check_credential, export_user_provisioning, render_output
from app.config import get_settings
from app.database import create_engine, create_session_factory


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    subparsers = parser.add_subparsers(dest="area", required=True)

    vpn_parser = subparsers.add_parser("vpn", help="VPN administration utilities")
    vpn_subparsers = vpn_parser.add_subparsers(dest="command", required=True)

    export_user = vpn_subparsers.add_parser(
        "export-user",
        help="Export safe data for manually adding a user to an Xray node",
    )
    export_user.add_argument("--user-id", type=int, required=True)
    export_user.add_argument("--server-id", type=int, required=True)
    export_user.add_argument("--json", action="store_true", dest="as_json")

    check = vpn_subparsers.add_parser(
        "check-credential",
        help="Check whether a VPN credential exists for a user and node",
    )
    check.add_argument("--user-id", type=int, required=True)
    check.add_argument("--server-id", type=int, required=True)
    check.add_argument("--json", action="store_true", dest="as_json")

    return parser


async def run(args: argparse.Namespace) -> int:
    settings = get_settings()
    engine = create_engine(settings)
    factory = create_session_factory(engine)
    try:
        async with factory() as session:
            try:
                if args.area == "vpn" and args.command == "export-user":
                    data = await export_user_provisioning(
                        session,
                        user_id=args.user_id,
                        server_id=args.server_id,
                    )
                elif args.area == "vpn" and args.command == "check-credential":
                    data = await check_credential(
                        session,
                        user_id=args.user_id,
                        server_id=args.server_id,
                    )
                else:
                    raise CliError("Unsupported command")
                await session.commit()
            except Exception:
                await session.rollback()
                raise
    finally:
        await engine.dispose()

    print(render_output(data, as_json=args.as_json), end="")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return asyncio.run(run(args))
    except CliError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except Exception:
        print("error: command failed", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
